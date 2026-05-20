package mcp

import (
	"fmt"
	"os"
	"path/filepath"

	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"

	"k8s-mcp-advanced/pkg/multicluster"
)

// restConfigFor reconstructs a *rest.Config from a multicluster.Cluster. The
// clientset alone does not retain the original config, so we rebuild from
// the underlying kubeconfig + context.
func restConfigFor(c *multicluster.Cluster) (*rest.Config, error) {
	kc := expandHome(c.Spec.Kubeconfig)
	if kc == "" {
		kc = expandHome(os.Getenv("KUBECONFIG"))
	}
	if kc == "" {
		kc = expandHome("~/.kube/config")
	}
	loader := &clientcmd.ClientConfigLoadingRules{ExplicitPath: kc}
	overrides := &clientcmd.ConfigOverrides{}
	if c.Spec.Context != "" {
		overrides.CurrentContext = c.Spec.Context
	}
	cfg, err := clientcmd.NewNonInteractiveDeferredLoadingClientConfig(loader, overrides).ClientConfig()
	if err != nil {
		return nil, fmt.Errorf("rebuild rest.Config: %w", err)
	}
	return cfg, nil
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
