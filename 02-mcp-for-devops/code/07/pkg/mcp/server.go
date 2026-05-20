// Package mcp wires the advanced building blocks (cache, watch,
// multi-cluster, CRD, helm) behind a single MCP server. It exposes:
//
//   - `mc_list_pods`   — multi-cluster pod listing with cache
//   - `mc_watch`       — subscribe to live events from a cluster
//   - `crd_list`       — list arbitrary CR instances
//   - `helm_list`      — enumerate Helm releases
//   - `helm_install`   — install or upgrade a chart
package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	"k8s-mcp-advanced/pkg/cache"
	"k8s-mcp-advanced/pkg/crd"
	"k8s-mcp-advanced/pkg/helm"
	"k8s-mcp-advanced/pkg/multicluster"
	"k8s-mcp-advanced/pkg/watch"
)

// Server is the assembled advanced MCP server.
type Server struct {
	clusters *multicluster.Manager
	cache    *cache.Store
	helm     *helm.Client
	watchers map[string]*watch.Watcher
	mcp      *server.MCPServer
}

// NewServer wires everything but does not start any background goroutines.
func NewServer(clusters *multicluster.Manager) *Server {
	s := &Server{
		clusters: clusters,
		cache:    cache.New(2048, 30*time.Second),
		helm:     helm.New(),
		watchers: make(map[string]*watch.Watcher),
		mcp: server.NewMCPServer(
			"k8s-mcp-advanced",
			"1.0.0",
			server.WithResourceCapabilities(true, true),
			server.WithToolCapabilities(true),
		),
	}
	s.registerTools()
	return s
}

// Serve runs stdio transport until ctx is cancelled.
func (s *Server) Serve(ctx context.Context) error {
	_ = ctx
	return server.ServeStdio(s.mcp)
}

func (s *Server) registerTools() {
	s.mcp.AddTool(mcp.NewTool(
		"mc_list_pods",
		mcp.WithDescription("List pods across one or more clusters with cache."),
		mcp.WithString("cluster", mcp.Description("Logical cluster name. Use '*' to fan out.")),
		mcp.WithString("namespace", mcp.DefaultString("default")),
	), s.handleListPods)

	s.mcp.AddTool(mcp.NewTool(
		"mc_clusters",
		mcp.WithDescription("List registered clusters and their reachability."),
	), s.handleClusters)

	s.mcp.AddTool(mcp.NewTool(
		"crd_list",
		mcp.WithDescription("List instances of a custom resource."),
		mcp.WithString("cluster"),
		mcp.WithString("group", mcp.Required(), mcp.Description("API group, e.g. cert-manager.io")),
		mcp.WithString("kind", mcp.Required(), mcp.Description("Kind, e.g. Certificate")),
		mcp.WithString("namespace"),
	), s.handleCRDList)

	s.mcp.AddTool(mcp.NewTool(
		"helm_list",
		mcp.WithDescription("List Helm releases."),
		mcp.WithString("namespace"),
	), s.handleHelmList)

	s.mcp.AddTool(mcp.NewTool(
		"helm_install",
		mcp.WithDescription("Install or upgrade a Helm chart."),
		mcp.WithString("release", mcp.Required()),
		mcp.WithString("chart", mcp.Required()),
		mcp.WithString("namespace"),
		mcp.WithString("version"),
		mcp.WithBoolean("upgrade", mcp.DefaultBool(true)),
		mcp.WithBoolean("dryRun", mcp.DefaultBool(false)),
	), s.handleHelmInstall)
}

// --- handlers ---------------------------------------------------------------

func (s *Server) handleListPods(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	clusterArg := req.GetString("cluster", "")
	namespace := req.GetString("namespace", "default")

	targets := []string{clusterArg}
	if clusterArg == "" {
		targets = []string{s.clusters.Default()}
	} else if clusterArg == "*" {
		targets = s.clusters.Names()
	}

	var out strings.Builder
	for _, name := range targets {
		key := fmt.Sprintf("pods:%s:%s", name, namespace)
		if cached, ok := s.cache.Get(key); ok {
			fmt.Fprintf(&out, "[%s] (cached)\n%s\n", name, cached.(string))
			continue
		}
		c, err := s.clusters.Get(name)
		if err != nil {
			fmt.Fprintf(&out, "[%s] error: %v\n", name, err)
			continue
		}
		pods, err := c.Clientset.CoreV1().Pods(namespace).List(ctx, metav1.ListOptions{})
		if err != nil {
			fmt.Fprintf(&out, "[%s] error: %v\n", name, err)
			continue
		}
		lines := make([]string, 0, len(pods.Items))
		for _, p := range pods.Items {
			lines = append(lines, fmt.Sprintf("  %s/%s  %s", p.Namespace, p.Name, p.Status.Phase))
		}
		body := strings.Join(lines, "\n")
		s.cache.Set(key, body)
		fmt.Fprintf(&out, "[%s]\n%s\n", name, body)
	}
	return mcp.NewToolResultText(out.String()), nil
}

func (s *Server) handleClusters(ctx context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	status := s.clusters.Ping(ctx)
	var out strings.Builder
	for name, err := range status {
		state := "ok"
		if err != nil {
			state = "error: " + err.Error()
		}
		fmt.Fprintf(&out, "%s  %s\n", name, state)
	}
	return mcp.NewToolResultText(out.String()), nil
}

func (s *Server) handleCRDList(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	clusterArg := req.GetString("cluster", "")
	group := req.GetString("group", "")
	kind := req.GetString("kind", "")
	namespace := req.GetString("namespace", "")

	if group == "" || kind == "" {
		return mcp.NewToolResultError("group and kind are required"), nil
	}
	c, err := s.clusters.Get(clusterArg)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}
	cfg, err := restConfigFor(c)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}
	cl, err := crd.New(cfg)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}
	items, err := cl.List(ctx, group, kind, namespace)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}
	rows := make([]map[string]string, 0, len(items))
	for _, it := range items {
		rows = append(rows, map[string]string{
			"namespace": it.GetNamespace(),
			"name":      it.GetName(),
			"created":   it.GetCreationTimestamp().Format(time.RFC3339),
		})
	}
	b, _ := json.MarshalIndent(rows, "", "  ")
	return mcp.NewToolResultText(string(b)), nil
}

func (s *Server) handleHelmList(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	releases, err := s.helm.List(ctx, req.GetString("namespace", ""))
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}
	b, _ := json.MarshalIndent(releases, "", "  ")
	return mcp.NewToolResultText(string(b)), nil
}

func (s *Server) handleHelmInstall(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	out, err := s.helm.Install(ctx, helm.InstallOptions{
		Release:   req.GetString("release", ""),
		Chart:     req.GetString("chart", ""),
		Version:   req.GetString("version", ""),
		Namespace: req.GetString("namespace", ""),
		Upgrade:   req.GetBool("upgrade", true),
		DryRun:    req.GetBool("dryRun", false),
	})
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}
	return mcp.NewToolResultText(out), nil
}
