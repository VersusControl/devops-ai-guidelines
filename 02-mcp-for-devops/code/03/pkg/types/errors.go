package types

import (
	"fmt"
)

// MCPError represents structured errors for MCP responses
type MCPError struct {
	Code        int               `json:"code"`
	Message     string            `json:"message"`
	Data        map[string]string `json:"data,omitempty"`
	Suggestions []string          `json:"suggestions,omitempty"`
}

func (e *MCPError) Error() string {
	return fmt.Sprintf("MCP Error %d: %s", e.Code, e.Message)
}

// Common error codes
const (
	ErrorCodeInvalidRequest     = -32600
	ErrorCodeMethodNotFound     = -32601
	ErrorCodeInvalidParams      = -32602
	ErrorCodeInternalError      = -32603
	ErrorCodeResourceNotFound   = -32000
	ErrorCodeUnauthorized       = -32001
	ErrorCodeForbidden          = -32002
	ErrorCodeTimeout            = -32003
	ErrorCodeClusterUnavailable = -32004
)

// Error constructors
func NewResourceNotFoundError(resourceType, namespace, name string) *MCPError {
	message := fmt.Sprintf("Resource not found: %s", name)
	if namespace != "" {
		message = fmt.Sprintf("Resource not found: %s/%s", namespace, name)
	}

	return &MCPError{
		Code:    ErrorCodeResourceNotFound,
		Message: message,
		Data: map[string]string{
			"resource_type": string(resourceType),
			"namespace":     namespace,
			"name":          name,
		},
		Suggestions: []string{
			"Check if the resource name is correct",
			"Verify the namespace exists and you have access",
			fmt.Sprintf("List available %ss to confirm the resource exists", resourceType),
		},
	}
}

func NewClusterUnavailableError(err error) *MCPError {
	return &MCPError{
		Code:    ErrorCodeClusterUnavailable,
		Message: "Kubernetes cluster is not available",
		Data: map[string]string{
			"underlying_error": err.Error(),
		},
		Suggestions: []string{
			"Check if kubectl can connect to the cluster",
			"Verify your kubeconfig is correct",
			"Ensure the cluster is running and accessible",
		},
	}
}

func NewInternalError(component string, err error) *MCPError {
	return &MCPError{
		Code:    ErrorCodeInternalError,
		Message: fmt.Sprintf("Internal error in %s", component),
		Data: map[string]string{
			"component": component,
			"error":     err.Error(),
		},
		Suggestions: []string{
			"Check the MCP server logs for more details",
			"Retry the operation",
			"Contact the administrator if the problem persists",
		},
	}
}
