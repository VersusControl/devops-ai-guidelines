package tools

import (
	"context"
	"fmt"
	"kubernetes-mcp-server/internal/logging"
	"kubernetes-mcp-server/pkg/k8s"
	"time"
)

type ToolExecutor struct {
	k8sClient *k8s.Client
	validator *Validator
	logger    *logging.Logger
}

func NewToolExecutor(k8sClient *k8s.Client, logger *logging.Logger) *ToolExecutor {
	return &ToolExecutor{
		k8sClient: k8sClient,
		validator: NewValidator(),
		logger:    logger,
	}
}

// ExecuteResult represents the result of tool execution
type ExecuteResult struct {
	Success   bool                   `json:"success"`
	Message   string                 `json:"message"`
	Data      map[string]interface{} `json:"data,omitempty"`
	Error     string                 `json:"error,omitempty"`
	Timestamp time.Time              `json:"timestamp"`
}

// ExecuteTool executes the specified tool with the provided input
func (e *ToolExecutor) ExecuteTool(ctx context.Context, toolName string, inputs map[string]interface{}) *ExecuteResult {
	start := time.Now()

	e.logger.LogMCPRequest("tool_call", toolName, inputs)

	// Validate input schema
	validation := e.validator.ValidateToolInput(toolName, inputs)
	if !validation.Valid {
		result := &ExecuteResult{
			Success:   false,
			Message:   "Input validation failed",
			Error:     fmt.Sprintf("Validation errors: %v", validation.Errors),
			Timestamp: start,
		}
		e.logger.LogMCPResponse("tool_call", time.Since(start), fmt.Errorf("validation failed"))

		return result
	}

	// Execute the tool based on its name
	var result *ExecuteResult
	switch toolName {
	case "k8s_scale_deployment":
		result = e.executeScaleDeployment(ctx, inputs)
	case "k8s_restart_deployment":
		result = e.executeRestartDeployment(ctx, inputs)
	case "k8s_get_pod_logs":
		result = e.executeGetPodLogs(ctx, inputs)
	case "k8s_create_configmap":
		result = e.executeCreateConfigMap(ctx, inputs)
	case "k8s_delete_pod":
		result = e.executeDeletePod(ctx, inputs)
	case "k8s_list_pods":
		result = e.executeListPods(ctx, inputs)
	default:
		result = &ExecuteResult{
			Success:   false,
			Message:   "Unknown tool",
			Error:     fmt.Sprintf("Tool '%s' is not supported", toolName),
			Timestamp: start,
		}
		e.logger.LogMCPResponse("tool_call", time.Since(start), fmt.Errorf("unknown tool: %s", toolName))
	}

	return result
}

// executeScaleDeployment handles deployment scaling
func (e *ToolExecutor) executeScaleDeployment(ctx context.Context, inputs map[string]interface{}) *ExecuteResult {
	namespace := inputs["namespace"].(string)
	name := inputs["name"].(string)
	replicas := int32(inputs["replicas"].(float64)) // Assuming replicas is passed as a float64

	deployment, err := e.k8sClient.ScaleDeployment(ctx, namespace, name, replicas)
	if err != nil {
		return &ExecuteResult{
			Success:   false,
			Message:   "Failed to scale deployment",
			Error:     err.Error(),
			Timestamp: time.Now(),
		}
	}

	return &ExecuteResult{
		Success: true,
		Message: fmt.Sprintf("Successfully scaled deployment %s/%s to %d replicas", namespace, name, replicas),
		Data: map[string]interface{}{
			"namespace":      deployment.Namespace,
			"name":           deployment.Name,
			"targetReplicas": *deployment.Spec.Replicas,
			"readyReplicas":  deployment.Status.ReadyReplicas,
			"updatedAt":      deployment.ObjectMeta.CreationTimestamp.Time,
		},
		Timestamp: time.Now(),
	}
}

// executeRestartDeployment handles deployment restarts
func (e *ToolExecutor) executeRestartDeployment(ctx context.Context, inputs map[string]interface{}) *ExecuteResult {
	namespace := inputs["namespace"].(string)
	name := inputs["name"].(string)

	deployment, err := e.k8sClient.RestartDeployment(ctx, namespace, name)
	if err != nil {
		return &ExecuteResult{
			Success:   false,
			Message:   "Failed to restart deployment",
			Error:     err.Error(),
			Timestamp: time.Now(),
		}
	}

	restartedAt := deployment.Spec.Template.ObjectMeta.Annotations["kubectl.kubernetes.io/restartedAt"]

	return &ExecuteResult{
		Success: true,
		Message: fmt.Sprintf("Successfully restarted deployment %s/%s", namespace, name),
		Data: map[string]interface{}{
			"namespace":   deployment.Namespace,
			"name":        deployment.Name,
			"restartedAt": restartedAt,
			"replicas":    *deployment.Spec.Replicas,
		},
		Timestamp: time.Now(),
	}
}

// executeGetPodLogs handles log retrieval
func (e *ToolExecutor) executeGetPodLogs(ctx context.Context, inputs map[string]interface{}) *ExecuteResult {
	namespace := inputs["namespace"].(string)
	name := inputs["name"].(string)

	// Handle optional parameters
	var containerName string
	if container, exists := inputs["container"]; exists {
		containerName = container.(string)
	}

	var tailLines *int64
	if tl, exists := inputs["tailLines"]; exists {
		lines := int64(tl.(float64))
		tailLines = &lines
	} else {
		// Default to 100 lines
		lines := int64(100)
		tailLines = &lines
	}

	var sinceSeconds *int64
	if ss, exists := inputs["sinceSeconds"]; exists {
		seconds := int64(ss.(float64))
		sinceSeconds = &seconds
	}

	// If no container specified, get the first one
	if containerName == "" {
		containers, err := e.k8sClient.GetPodContainers(ctx, namespace, name)
		if err != nil {
			return &ExecuteResult{
				Success:   false,
				Message:   "Failed to get pod containers",
				Error:     err.Error(),
				Timestamp: time.Now(),
			}
		}
		if len(containers) == 0 {
			return &ExecuteResult{
				Success:   false,
				Message:   "Pod has no containers",
				Error:     "No containers found in pod",
				Timestamp: time.Now(),
			}
		}
		containerName = containers[0]
	}

	logs, err := e.k8sClient.GetPodLogs(ctx, namespace, name, containerName, tailLines, sinceSeconds)
	if err != nil {
		return &ExecuteResult{
			Success:   false,
			Message:   "Failed to retrieve pod logs",
			Error:     err.Error(),
			Timestamp: time.Now(),
		}
	}

	return &ExecuteResult{
		Success: true,
		Message: fmt.Sprintf("Successfully retrieved logs from pod %s/%s (container: %s)", namespace, name, containerName),
		Data: map[string]interface{}{
			"namespace": namespace,
			"pod":       name,
			"container": containerName,
			"tailLines": *tailLines,
			"logs":      logs,
			"logLength": len(logs),
		},
		Timestamp: time.Now(),
	}
}

// executeCreateConfigMap handles ConfigMap creation/update
func (e *ToolExecutor) executeCreateConfigMap(ctx context.Context, inputs map[string]interface{}) *ExecuteResult {
	namespace := inputs["namespace"].(string)
	name := inputs["name"].(string)

	// Convert data interface{} to map[string]string
	dataInterface := inputs["data"].(map[string]interface{})
	data := make(map[string]string)
	for key, value := range dataInterface {
		data[key] = value.(string)
	}

	// Handle optional labels
	var labels map[string]string
	if labelsInterface, exists := inputs["labels"]; exists {
		labelsMap := labelsInterface.(map[string]interface{})
		labels = make(map[string]string)
		for key, value := range labelsMap {
			labels[key] = value.(string)
		}
	}

	configMap, err := e.k8sClient.CreateOrUpdateConfigMap(ctx, namespace, name, data, labels)
	if err != nil {
		return &ExecuteResult{
			Success:   false,
			Message:   "Failed to create/update ConfigMap",
			Error:     err.Error(),
			Timestamp: time.Now(),
		}
	}

	return &ExecuteResult{
		Success: true,
		Message: fmt.Sprintf("Successfully created/updated ConfigMap %s/%s", namespace, name),
		Data: map[string]interface{}{
			"namespace": configMap.Namespace,
			"name":      configMap.Name,
			"data":      configMap.Data,
			"labels":    configMap.Labels,
			"createdAt": configMap.CreationTimestamp.Time,
		},
		Timestamp: time.Now(),
	}
}

// executeDeletePod handles pod deletion
func (e *ToolExecutor) executeDeletePod(ctx context.Context, inputs map[string]interface{}) *ExecuteResult {
	namespace := inputs["namespace"].(string)
	name := inputs["name"].(string)

	// Handle optional force parameter
	force := false
	if forceValue, exists := inputs["force"]; exists {
		force = forceValue.(bool)
	}

	err := e.k8sClient.DeletePod(ctx, namespace, name, force)
	if err != nil {
		return &ExecuteResult{
			Success:   false,
			Message:   "Failed to delete pod",
			Error:     err.Error(),
			Timestamp: time.Now(),
		}
	}

	forceMsg := ""
	if force {
		forceMsg = " (forced)"
	}

	return &ExecuteResult{
		Success: true,
		Message: fmt.Sprintf("Successfully deleted pod %s/%s%s", namespace, name, forceMsg),
		Data: map[string]interface{}{
			"namespace": namespace,
			"name":      name,
			"force":     force,
		},
		Timestamp: time.Now(),
	}
}

// executeListPods handles listing pods in a namespace
func (e *ToolExecutor) executeListPods(ctx context.Context, inputs map[string]interface{}) *ExecuteResult {
	namespace := inputs["namespace"].(string)

	pods, err := e.k8sClient.ListPods(ctx, namespace)
	if err != nil {
		return &ExecuteResult{
			Success:   false,
			Message:   "Failed to list pods",
			Error:     err.Error(),
			Timestamp: time.Now(),
		}
	}

	// Convert pods to a format suitable for the response
	podList := make([]map[string]interface{}, len(pods))
	for i, pod := range pods {
		podList[i] = map[string]interface{}{
			"name":      pod.Name,
			"namespace": pod.Namespace,
			"status":    pod.Status,
			"phase":     pod.Phase,
			"node":      pod.Node,
			"labels":    pod.Labels,
			"createdAt": pod.CreatedAt.Format(time.RFC3339),
			"restarts":  pod.Restarts,
		}
	}

	return &ExecuteResult{
		Success: true,
		Message: fmt.Sprintf("Successfully listed %d pods in namespace %s", len(pods), namespace),
		Data: map[string]interface{}{
			"namespace": namespace,
			"podCount":  len(pods),
			"pods":      podList,
		},
		Timestamp: time.Now(),
	}
}
