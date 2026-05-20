// Package multicluster manages a fleet of Kubernetes clients keyed by a
// logical cluster name. MCP tools accept a `cluster` argument that the
// Manager resolves into the right *kubernetes.Clientset.
package multicluster

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sync"

	"gopkg.in/yaml.v3"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
)

// ClusterSpec declares one entry in the registry file.
type ClusterSpec struct {
	Name       string `yaml:"name"`
	Kubeconfig string `yaml:"kubeconfig,omitempty"`
	Context    string `yaml:"context,omitempty"`
	ReadOnly   bool   `yaml:"readOnly,omitempty"`
}

type registry struct {
	Clusters []ClusterSpec `yaml:"clusters"`
}

// Cluster bundles a clientset with its declared metadata.
type Cluster struct {
	Spec      ClusterSpec
	Clientset kubernetes.Interface
}

// Manager holds and lazily initialises per-cluster clients.
type Manager struct {
	mu       sync.RWMutex
	specs    map[string]ClusterSpec
	clients  map[string]kubernetes.Interface
	defaults string
}

// LoadFromFile parses a YAML registry file and returns a populated Manager.
// Clients are constructed eagerly so configuration errors surface at boot.
func LoadFromFile(path string) (*Manager, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read %s: %w", path, err)
	}
	var r registry
	if err := yaml.Unmarshal(data, &r); err != nil {
		return nil, fmt.Errorf("parse %s: %w", path, err)
	}
	if len(r.Clusters) == 0 {
		return nil, fmt.Errorf("no clusters declared in %s", path)
	}

	m := &Manager{
		specs:    make(map[string]ClusterSpec, len(r.Clusters)),
		clients:  make(map[string]kubernetes.Interface, len(r.Clusters)),
		defaults: r.Clusters[0].Name,
	}
	for _, spec := range r.Clusters {
		client, err := buildClient(spec)
		if err != nil {
			return nil, fmt.Errorf("cluster %q: %w", spec.Name, err)
		}
		m.specs[spec.Name] = spec
		m.clients[spec.Name] = client
	}
	return m, nil
}

// Names returns the registered cluster names in registry order.
func (m *Manager) Names() []string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	out := make([]string, 0, len(m.specs))
	for name := range m.specs {
		out = append(out, name)
	}
	return out
}

// Default returns the first cluster declared in the registry.
func (m *Manager) Default() string {
	return m.defaults
}

// Get resolves a logical cluster name to a Cluster handle.
func (m *Manager) Get(name string) (*Cluster, error) {
	if name == "" {
		name = m.defaults
	}
	m.mu.RLock()
	defer m.mu.RUnlock()
	client, ok := m.clients[name]
	if !ok {
		return nil, fmt.Errorf("unknown cluster %q", name)
	}
	return &Cluster{Spec: m.specs[name], Clientset: client}, nil
}

// Ping verifies the API server of every cluster is reachable.
func (m *Manager) Ping(ctx context.Context) map[string]error {
	m.mu.RLock()
	defer m.mu.RUnlock()
	result := make(map[string]error, len(m.clients))
	for name, c := range m.clients {
		_, err := c.Discovery().ServerVersion()
		result[name] = err
	}
	_ = ctx
	return result
}

func buildClient(spec ClusterSpec) (kubernetes.Interface, error) {
	kubeconfig := expandHome(spec.Kubeconfig)
	if kubeconfig == "" {
		kubeconfig = expandHome(os.Getenv("KUBECONFIG"))
	}
	if kubeconfig == "" {
		kubeconfig = expandHome("~/.kube/config")
	}

	loader := &clientcmd.ClientConfigLoadingRules{ExplicitPath: kubeconfig}
	overrides := &clientcmd.ConfigOverrides{}
	if spec.Context != "" {
		overrides.CurrentContext = spec.Context
	}
	cc := clientcmd.NewNonInteractiveDeferredLoadingClientConfig(loader, overrides)
	restCfg, err := cc.ClientConfig()
	if err != nil {
		return nil, err
	}
	return kubernetes.NewForConfig(restCfg)
}

func expandHome(p string) string {
	if p == "" || p[0] != '~' {
		return p
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return p
	}
	return filepath.Join(home, p[1:])
}
