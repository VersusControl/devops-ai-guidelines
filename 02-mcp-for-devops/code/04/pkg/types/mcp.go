package types

import (
	"encoding/json"
)

// Resource represents a Kubernetes resource exposed through MCP
type Resource struct {
	URI         string            `json:"uri"`
	Name        string            `json:"name"`
	Description string            `json:"description"`
	MimeType    string            `json:"mimeType"`
	Metadata    map[string]string `json:"metadata,omitempty"`
}

// ResourceContent holds the actual resource data
type ResourceContent struct {
	URI      string          `json:"uri"`
	MimeType string          `json:"mimeType"`
	Text     string          `json:"text,omitempty"`
	Blob     []byte          `json:"blob,omitempty"`
	Metadata json.RawMessage `json:"metadata,omitempty"`
}

// K8sResourceType represents different Kubernetes resource types
type K8sResourceType string

const (
	ResourceTypePod        K8sResourceType = "pod"
	ResourceTypeService    K8sResourceType = "service"
	ResourceTypeDeployment K8sResourceType = "deployment"
	ResourceTypeConfigMap  K8sResourceType = "configmap"
	ResourceTypeSecret     K8sResourceType = "secret"
	ResourceTypeNamespace  K8sResourceType = "namespace"
)

// ResourceIdentifier uniquely identifies a Kubernetes resource
type ResourceIdentifier struct {
	Type      K8sResourceType `json:"type"`
	Namespace string          `json:"namespace"`
	Name      string          `json:"name"`
}

func (r ResourceIdentifier) ToURI() string {
	if r.Namespace == "" {
		return "k8s://" + string(r.Type) + "/" + r.Name
	}
	return string("k8s://" + string(r.Type) + "/" + r.Namespace + "/" + r.Name)
}
