// Package helm is a thin process-level wrapper around the `helm` CLI.
//
// We deliberately avoid linking against the Helm v3 Go SDK to keep this
// module's dependency graph small. The CLI is shipped on every operator's
// laptop and CI image, so shelling out is pragmatic and easy to audit.
package helm

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"
)

// Release is a subset of the JSON output produced by `helm list -o json`.
type Release struct {
	Name       string `json:"name"`
	Namespace  string `json:"namespace"`
	Revision   string `json:"revision"`
	Status     string `json:"status"`
	Chart      string `json:"chart"`
	AppVersion string `json:"app_version"`
	Updated    string `json:"updated"`
}

// Client owns shared invocation knobs (kubeconfig, context).
type Client struct {
	Bin        string
	Kubeconfig string
	Context    string
}

// New returns a Client using the `helm` binary on PATH.
func New() *Client {
	return &Client{Bin: "helm"}
}

// List returns Helm releases visible in the given namespace ("" = all).
func (c *Client) List(ctx context.Context, namespace string) ([]Release, error) {
	args := []string{"list", "-o", "json"}
	if namespace == "" {
		args = append(args, "-A")
	} else {
		args = append(args, "-n", namespace)
	}
	out, err := c.run(ctx, args...)
	if err != nil {
		return nil, err
	}
	var releases []Release
	if err := json.Unmarshal(out, &releases); err != nil {
		return nil, fmt.Errorf("decode helm list output: %w", err)
	}
	return releases, nil
}

// InstallOptions captures the inputs to a Helm install or upgrade.
type InstallOptions struct {
	Release   string
	Chart     string
	Version   string
	Namespace string
	Values    map[string]string
	Upgrade   bool
	DryRun    bool
}

// Install runs `helm install` (or `upgrade --install` when Upgrade is true).
func (c *Client) Install(ctx context.Context, opts InstallOptions) (string, error) {
	if opts.Release == "" || opts.Chart == "" {
		return "", fmt.Errorf("release name and chart are required")
	}
	args := []string{}
	if opts.Upgrade {
		args = append(args, "upgrade", "--install")
	} else {
		args = append(args, "install")
	}
	args = append(args, opts.Release, opts.Chart)
	if opts.Version != "" {
		args = append(args, "--version", opts.Version)
	}
	if opts.Namespace != "" {
		args = append(args, "--namespace", opts.Namespace, "--create-namespace")
	}
	for k, v := range opts.Values {
		args = append(args, "--set", fmt.Sprintf("%s=%s", k, v))
	}
	if opts.DryRun {
		args = append(args, "--dry-run")
	}
	args = append(args, "-o", "json")

	out, err := c.run(ctx, args...)
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(out)), nil
}

// Uninstall removes a release.
func (c *Client) Uninstall(ctx context.Context, release, namespace string) error {
	args := []string{"uninstall", release}
	if namespace != "" {
		args = append(args, "-n", namespace)
	}
	_, err := c.run(ctx, args...)
	return err
}

func (c *Client) run(ctx context.Context, args ...string) ([]byte, error) {
	if c.Kubeconfig != "" {
		args = append([]string{"--kubeconfig", c.Kubeconfig}, args...)
	}
	if c.Context != "" {
		args = append([]string{"--kube-context", c.Context}, args...)
	}
	bin := c.Bin
	if bin == "" {
		bin = "helm"
	}
	cmd := exec.CommandContext(ctx, bin, args...)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("helm %s: %w: %s", strings.Join(args, " "), err, stderr.String())
	}
	return stdout.Bytes(), nil
}
