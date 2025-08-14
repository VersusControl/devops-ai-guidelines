package tools

import (
	"fmt"
	"regexp"
	"strings"
)

// ValidationError represents a validation failure with details
type ValidationError struct {
	Field   string `json:"field"`
	Value   string `json:"value"`
	Message string `json:"message"`
}

func (e ValidationError) Error() string {
	return fmt.Sprintf("validation failed for field '%s' with value '%s': %s", e.Field, e.Value, e.Message)
}

// ValidationResult holds validation results and any errors
type ValidationResult struct {
	Valid  bool              `json:"valid"`
	Errors []ValidationError `json:"errors,omitempty"`
}

// Validator provides comprehensive input validation for tool parameters
type Validator struct {
	kubernetesNamePattern *regexp.Regexp
}

// NewValidator creates a new validator with compiled patterns
func NewValidator() *Validator {
	return &Validator{
		kubernetesNamePattern: regexp.MustCompile(`^[a-z0-9]([-a-z0-9]*[a-z0-9])?$`),
	}
}

// ValidateToolInput validates tool parameters based on the tool name and inputs
func (v *Validator) ValidateToolInput(toolName string, inputs map[string]interface{}) *ValidationResult {
	result := &ValidationResult{Valid: true, Errors: []ValidationError{}}

	// Common validations for all tools
	v.validateNamespace(inputs, result)

	// Only validate resource name for tools that require a specific resource
	if toolName != "k8s_list_pods" {
		v.validateResourceName(inputs, result)
	}

	// Tool-specific validations
	switch toolName {
	case "k8s_scale_deployment":
		v.validateScaleOperation(inputs, result)
	case "k8s_restart_deployment":
		v.validateRestartOperation(inputs, result)
	case "k8s_get_pod_logs":
		v.validateLogOperation(inputs, result)
	case "k8s_create_configmap":
		v.validateConfigMapOperation(inputs, result)
	case "k8s_delete_pod":
		v.validateDeleteOperation(inputs, result)
	case "k8s_list_pods":
		v.validateListOperation(inputs, result)
	default:
		result.Valid = false
		result.Errors = append(result.Errors, ValidationError{
			Field:   "toolName",
			Value:   toolName,
			Message: "unknown tool name",
		})
	}

	if len(result.Errors) > 0 {
		result.Valid = false
	}

	return result
}

// validateNamespace checks if namespace parameter is valid
func (v *Validator) validateNamespace(inputs map[string]interface{}, result *ValidationResult) {
	namespace, exists := inputs["namespace"]
	if !exists {
		result.Errors = append(result.Errors, ValidationError{
			Field:   "namespace",
			Value:   "",
			Message: "namespace is required",
		})
		return
	}

	namespaceStr, ok := namespace.(string)
	if !ok {
		result.Errors = append(result.Errors, ValidationError{
			Field:   "namespace",
			Value:   fmt.Sprintf("%v", namespace),
			Message: "namespace must be a string",
		})
		return
	}

	if !v.kubernetesNamePattern.MatchString(namespaceStr) {
		result.Errors = append(result.Errors, ValidationError{
			Field:   "namespace",
			Value:   namespaceStr,
			Message: "namespace must follow Kubernetes naming conventions (lowercase alphanumeric and hyphens)",
		})
	}

	if len(namespaceStr) > 63 {
		result.Errors = append(result.Errors, ValidationError{
			Field:   "namespace",
			Value:   namespaceStr,
			Message: "namespace must be 63 characters or less",
		})
	}
}

// validateResourceName checks if name parameter is valid
func (v *Validator) validateResourceName(inputs map[string]interface{}, result *ValidationResult) {
	name, exists := inputs["name"]
	if !exists {
		result.Errors = append(result.Errors, ValidationError{
			Field:   "name",
			Value:   "",
			Message: "name is required",
		})
		return
	}

	nameStr, ok := name.(string)
	if !ok {
		result.Errors = append(result.Errors, ValidationError{
			Field:   "name",
			Value:   fmt.Sprintf("%v", name),
			Message: "name must be a string",
		})
		return
	}

	if !v.kubernetesNamePattern.MatchString(nameStr) {
		result.Errors = append(result.Errors, ValidationError{
			Field:   "name",
			Value:   nameStr,
			Message: "name must follow Kubernetes naming conventions (lowercase alphanumeric and hyphens)",
		})
	}

	if len(nameStr) > 253 {
		result.Errors = append(result.Errors, ValidationError{
			Field:   "name",
			Value:   nameStr,
			Message: "name must be 253 characters or less",
		})
	}
}

// validateScaleOperation validates scaling-specific parameters
func (v *Validator) validateScaleOperation(inputs map[string]interface{}, result *ValidationResult) {
	// Validate replicas
	replicas, exists := inputs["replicas"]
	if !exists {
		result.Errors = append(result.Errors, ValidationError{
			Field:   "replicas",
			Value:   "",
			Message: "replicas is required for scaling operations",
		})
		return
	}

	// Handle both int and float64 (JSON numbers can be float64)
	var replicasInt int
	switch r := replicas.(type) {
	case int:
		replicasInt = r
	case float64:
		replicasInt = int(r)
	default:
		result.Errors = append(result.Errors, ValidationError{
			Field:   "replicas",
			Value:   fmt.Sprintf("%v", replicas),
			Message: "replicas must be an integer",
		})
		return
	}

	if replicasInt < 0 || replicasInt > 100 {
		result.Errors = append(result.Errors, ValidationError{
			Field:   "replicas",
			Value:   fmt.Sprintf("%d", replicasInt),
			Message: "replicas must be between 0 and 100",
		})
	}

	v.validateConfirmation(inputs, result)
}

// validateRestartOperation validates restart-specific parameters
func (v *Validator) validateRestartOperation(inputs map[string]interface{}, result *ValidationResult) {
	v.validateConfirmation(inputs, result)
}

// validateLogOperation validates log retrieval parameters
func (v *Validator) validateLogOperation(inputs map[string]interface{}, result *ValidationResult) {
	// Validate optional tailLines
	if tailLines, exists := inputs["tailLines"]; exists {
		var tailLinesInt int
		switch t := tailLines.(type) {
		case int:
			tailLinesInt = t
		case float64:
			tailLinesInt = int(t)
		default:
			result.Errors = append(result.Errors, ValidationError{
				Field:   "tailLines",
				Value:   fmt.Sprintf("%v", tailLines),
				Message: "tailLines must be an integer",
			})
			return
		}

		if tailLinesInt < 1 || tailLinesInt > 10000 {
			result.Errors = append(result.Errors, ValidationError{
				Field:   "tailLines",
				Value:   fmt.Sprintf("%d", tailLinesInt),
				Message: "tailLines must be between 1 and 10000",
			})
		}
	}

	// Validate optional sinceSeconds
	if sinceSeconds, exists := inputs["sinceSeconds"]; exists {
		var sinceSecondsInt int
		switch s := sinceSeconds.(type) {
		case int:
			sinceSecondsInt = s
		case float64:
			sinceSecondsInt = int(s)
		default:
			result.Errors = append(result.Errors, ValidationError{
				Field:   "sinceSeconds",
				Value:   fmt.Sprintf("%v", sinceSeconds),
				Message: "sinceSeconds must be an integer",
			})
			return
		}

		if sinceSecondsInt < 1 || sinceSecondsInt > 86400 {
			result.Errors = append(result.Errors, ValidationError{
				Field:   "sinceSeconds",
				Value:   fmt.Sprintf("%d", sinceSecondsInt),
				Message: "sinceSeconds must be between 1 and 86400 (24 hours)",
			})
		}
	}

	// Validate optional container name
	if container, exists := inputs["container"]; exists {
		containerStr, ok := container.(string)
		if !ok {
			result.Errors = append(result.Errors, ValidationError{
				Field:   "container",
				Value:   fmt.Sprintf("%v", container),
				Message: "container must be a string",
			})
			return
		}

		if !v.kubernetesNamePattern.MatchString(containerStr) {
			result.Errors = append(result.Errors, ValidationError{
				Field:   "container",
				Value:   containerStr,
				Message: "container name must follow Kubernetes naming conventions",
			})
		}
	}
}

// validateConfigMapOperation validates ConfigMap creation parameters
func (v *Validator) validateConfigMapOperation(inputs map[string]interface{}, result *ValidationResult) {
	// Validate data field
	data, exists := inputs["data"]
	if !exists {
		result.Errors = append(result.Errors, ValidationError{
			Field:   "data",
			Value:   "",
			Message: "data is required for ConfigMap operations",
		})
		return
	}

	dataMap, ok := data.(map[string]interface{})
	if !ok {
		result.Errors = append(result.Errors, ValidationError{
			Field:   "data",
			Value:   fmt.Sprintf("%v", data),
			Message: "data must be an object with string keys and values",
		})
		return
	}

	if len(dataMap) == 0 {
		result.Errors = append(result.Errors, ValidationError{
			Field:   "data",
			Value:   "{}",
			Message: "data cannot be empty",
		})
	}

	// Validate each data key and value
	for key, value := range dataMap {
		if key == "" {
			result.Errors = append(result.Errors, ValidationError{
				Field:   "data.key",
				Value:   key,
				Message: "data keys cannot be empty",
			})
		}

		if _, ok := value.(string); !ok {
			result.Errors = append(result.Errors, ValidationError{
				Field:   fmt.Sprintf("data.%s", key),
				Value:   fmt.Sprintf("%v", value),
				Message: "data values must be strings",
			})
		}
	}

	// Validate optional labels
	if labels, exists := inputs["labels"]; exists {
		labelsMap, ok := labels.(map[string]interface{})
		if !ok {
			result.Errors = append(result.Errors, ValidationError{
				Field:   "labels",
				Value:   fmt.Sprintf("%v", labels),
				Message: "labels must be an object with string keys and values",
			})
			return
		}

		for key, value := range labelsMap {
			if !isValidLabelKey(key) {
				result.Errors = append(result.Errors, ValidationError{
					Field:   "labels.key",
					Value:   key,
					Message: "label key is invalid",
				})
			}

			if _, ok := value.(string); !ok {
				result.Errors = append(result.Errors, ValidationError{
					Field:   fmt.Sprintf("labels.%s", key),
					Value:   fmt.Sprintf("%v", value),
					Message: "label values must be strings",
				})
			}
		}
	}
}

// validateDeleteOperation validates deletion parameters
func (v *Validator) validateDeleteOperation(inputs map[string]interface{}, result *ValidationResult) {
	v.validateConfirmation(inputs, result)

	// Validate optional force parameter
	if force, exists := inputs["force"]; exists {
		if _, ok := force.(bool); !ok {
			result.Errors = append(result.Errors, ValidationError{
				Field:   "force",
				Value:   fmt.Sprintf("%v", force),
				Message: "force must be a boolean",
			})
		}
	}
}

// validateConfirmation ensures dangerous operations require explicit confirmation
func (v *Validator) validateConfirmation(inputs map[string]interface{}, result *ValidationResult) {
	confirm, exists := inputs["confirm"]
	if !exists {
		result.Errors = append(result.Errors, ValidationError{
			Field:   "confirm",
			Value:   "",
			Message: "confirmation is required for this operation",
		})
		return
	}

	confirmBool, ok := confirm.(bool)
	if !ok {
		result.Errors = append(result.Errors, ValidationError{
			Field:   "confirm",
			Value:   fmt.Sprintf("%v", confirm),
			Message: "confirm must be a boolean",
		})
		return
	}

	if !confirmBool {
		result.Errors = append(result.Errors, ValidationError{
			Field:   "confirm",
			Value:   "false",
			Message: "you must set confirm=true to perform this operation",
		})
	}
}

// validateListOperation validates list operation parameters
func (v *Validator) validateListOperation(inputs map[string]interface{}, result *ValidationResult) {
	// For list operations, we only need namespace validation which is already done in common validation
	// No additional validation required for listing pods
}

// isValidLabelKey validates Kubernetes label key format
func isValidLabelKey(key string) bool {
	if len(key) == 0 || len(key) > 63 {
		return false
	}

	// Check for optional prefix
	parts := strings.Split(key, "/")
	if len(parts) > 2 {
		return false
	}

	// Validate each part
	for _, part := range parts {
		if part == "" {
			return false
		}
		// Basic validation - could be more comprehensive
		if !regexp.MustCompile(`^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$`).MatchString(part) {
			return false
		}
	}

	return true
}
