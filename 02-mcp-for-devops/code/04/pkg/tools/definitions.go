package tools

import "github.com/mark3labs/mcp-go/mcp"

func GetToolDefinitions() []mcp.Tool {
	return []mcp.Tool{
		{
			Name:        "k8s_scale_deployment",
			Description: "Scale a Kubernetes deployment to the specified number of replicas",
			InputSchema: mcp.ToolInputSchema{
				Type: "object",
				Properties: map[string]interface{}{
					"namespace": map[string]interface{}{
						"type":        "string",
						"description": "Kubernetes namespace containing the deployment",
						"pattern":     "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
					},
					"name": map[string]interface{}{
						"type":        "string",
						"description": "Name of the deployment to scale",
						"pattern":     "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
					},
					"replicas": map[string]interface{}{
						"type":        "integer",
						"description": "Target number of replicas (0-100)",
						"minimum":     0,
						"maximum":     100,
					},
					"confirm": map[string]interface{}{
						"type":        "boolean",
						"description": "Confirmation that you want to perform this scaling operation",
						"const":       true,
					},
				},
				Required: []string{"namespace", "name", "replicas", "confirm"},
			},
		},
		{
			Name:        "k8s_restart_deployment",
			Description: "Restart a Kubernetes deployment by updating its restart annotation",
			InputSchema: mcp.ToolInputSchema{
				Type: "object",
				Properties: map[string]interface{}{
					"namespace": map[string]interface{}{
						"type":        "string",
						"description": "Kubernetes namespace containing the deployment",
						"pattern":     "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
					},
					"name": map[string]interface{}{
						"type":        "string",
						"description": "Name of the deployment to restart",
						"pattern":     "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
					},
					"confirm": map[string]interface{}{
						"type":        "boolean",
						"description": "Confirmation that you want to restart this deployment",
						"const":       true,
					},
				},
				Required: []string{"namespace", "name", "confirm"},
			},
		},
		{
			Name:        "k8s_get_pod_logs",
			Description: "Retrieve logs from a Kubernetes pod with filtering options",
			InputSchema: mcp.ToolInputSchema{
				Type: "object",
				Properties: map[string]interface{}{
					"namespace": map[string]interface{}{
						"type":        "string",
						"description": "Kubernetes namespace containing the pod",
						"pattern":     "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
					},
					"name": map[string]interface{}{
						"type":        "string",
						"description": "Name of the pod to get logs from",
						"pattern":     "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
					},
					"container": map[string]interface{}{
						"type":        "string",
						"description": "Container name (optional, defaults to first container)",
						"pattern":     "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
					},
					"tailLines": map[string]interface{}{
						"type":        "integer",
						"description": "Number of lines to tail (optional, defaults to 100)",
						"minimum":     1,
						"maximum":     10000,
						"default":     100,
					},
					"sinceSeconds": map[string]interface{}{
						"type":        "integer",
						"description": "Show logs from this many seconds ago (optional)",
						"minimum":     1,
						"maximum":     86400, // 24 hours max
					},
				},
				Required: []string{"namespace", "name"},
			},
		},
		{
			Name:        "k8s_create_configmap",
			Description: "Create or update a Kubernetes ConfigMap with the specified data",
			InputSchema: mcp.ToolInputSchema{
				Type: "object",
				Properties: map[string]interface{}{
					"namespace": map[string]interface{}{
						"type":        "string",
						"description": "Kubernetes namespace for the ConfigMap",
						"pattern":     "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
					},
					"name": map[string]interface{}{
						"type":        "string",
						"description": "Name of the ConfigMap",
						"pattern":     "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
					},
					"data": map[string]interface{}{
						"type":        "object",
						"description": "Key-value pairs for the ConfigMap data",
						"additionalProperties": map[string]interface{}{
							"type": "string",
						},
					},
					"labels": map[string]interface{}{
						"type":        "object",
						"description": "Labels to apply to the ConfigMap (optional)",
						"additionalProperties": map[string]interface{}{
							"type": "string",
						},
					},
				},
				Required: []string{"namespace", "name", "data"},
			},
		},
		{
			Name:        "k8s_delete_pod",
			Description: "Delete a specific Kubernetes pod (use with caution)",
			InputSchema: mcp.ToolInputSchema{
				Type: "object",
				Properties: map[string]interface{}{
					"namespace": map[string]interface{}{
						"type":        "string",
						"description": "Kubernetes namespace containing the pod",
						"pattern":     "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
					},
					"name": map[string]interface{}{
						"type":        "string",
						"description": "Name of the pod to delete",
						"pattern":     "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
					},
					"force": map[string]interface{}{
						"type":        "boolean",
						"description": "Force delete the pod immediately (optional)",
						"default":     false,
					},
					"confirm": map[string]interface{}{
						"type":        "boolean",
						"description": "Confirmation that you want to delete this pod",
						"const":       true,
					},
				},
				Required: []string{"namespace", "name", "confirm"},
			},
		},
	}
}
