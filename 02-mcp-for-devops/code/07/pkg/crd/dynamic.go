// Package crd interacts with arbitrary Custom Resources via the
// dynamic client and discovery RESTMapper. It lets the MCP server inspect
// resources (Cert-Manager Certificates, ArgoCD Applications, etc.) without
// hard-coding their schemas.
package crd

import (
	"context"
	"fmt"

	"k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/client-go/discovery"
	memory "k8s.io/client-go/discovery/cached/memory"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/restmapper"
)

// Client wraps the dynamic + discovery clients required for CRD work.
type Client struct {
	dyn    dynamic.Interface
	mapper meta.RESTMapper
}

// New constructs a Client from a rest.Config.
func New(cfg *rest.Config) (*Client, error) {
	dyn, err := dynamic.NewForConfig(cfg)
	if err != nil {
		return nil, fmt.Errorf("dynamic client: %w", err)
	}
	disc, err := discovery.NewDiscoveryClientForConfig(cfg)
	if err != nil {
		return nil, fmt.Errorf("discovery client: %w", err)
	}
	mapper := restmapper.NewDeferredDiscoveryRESTMapper(memory.NewMemCacheClient(disc))
	return &Client{dyn: dyn, mapper: mapper}, nil
}

// List returns the items of a Kind+Group, optionally scoped to a namespace.
func (c *Client) List(ctx context.Context, group, kind, namespace string) ([]unstructured.Unstructured, error) {
	gvr, namespaced, err := c.resolve(group, kind)
	if err != nil {
		return nil, err
	}

	var ri dynamic.ResourceInterface = c.dyn.Resource(gvr)
	if namespaced {
		ri = c.dyn.Resource(gvr).Namespace(namespace)
	}

	list, err := ri.List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("list %s/%s: %w", group, kind, err)
	}
	return list.Items, nil
}

// Get fetches a single resource by name.
func (c *Client) Get(ctx context.Context, group, kind, namespace, name string) (*unstructured.Unstructured, error) {
	gvr, namespaced, err := c.resolve(group, kind)
	if err != nil {
		return nil, err
	}
	var ri dynamic.ResourceInterface = c.dyn.Resource(gvr)
	if namespaced {
		ri = c.dyn.Resource(gvr).Namespace(namespace)
	}
	return ri.Get(ctx, name, metav1.GetOptions{})
}

// Resolve returns the GroupVersionResource for a Kind + Group pair. Useful
// for MCP tool argument validation.
func (c *Client) Resolve(group, kind string) (schema.GroupVersionResource, bool, error) {
	return c.resolve(group, kind)
}

func (c *Client) resolve(group, kind string) (schema.GroupVersionResource, bool, error) {
	gk := schema.GroupKind{Group: group, Kind: kind}
	mapping, err := c.mapper.RESTMapping(gk)
	if err != nil {
		return schema.GroupVersionResource{}, false, fmt.Errorf("resolve %s/%s: %w", group, kind, err)
	}
	return mapping.Resource, mapping.Scope.Name() == meta.RESTScopeNameNamespace, nil
}
