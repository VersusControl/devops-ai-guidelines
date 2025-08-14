package mcp

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/sirupsen/logrus"

	"kubernetes-mcp-server/pkg/auth"
	"kubernetes-mcp-server/pkg/security"
)

// ContextKey is a custom type for context keys to avoid collisions
type ContextKey string

const (
	// HeadersContextKey is used to store HTTP headers in context
	HeadersContextKey ContextKey = "headers"
	// AuthInfoContextKey is used to store authentication info in context
	AuthInfoContextKey ContextKey = "auth_info"
)

type SecureMCPServer struct {
	*Server  // Embed the original server
	security *security.SecurityMiddleware
	logger   *logrus.Logger
}

func NewSecureMCPServer(originalServer *Server, securityMiddleware *security.SecurityMiddleware, logger *logrus.Logger) *SecureMCPServer {
	return &SecureMCPServer{
		Server:   originalServer,
		security: securityMiddleware,
		logger:   logger,
	}
}

func (s *SecureMCPServer) HandleToolCall(ctx context.Context, toolName string, arguments map[string]interface{}) (map[string]interface{}, error) {
	startTime := time.Now()

	// Extract headers from context (this would come from the transport layer)
	headers := extractHeadersFromContext(ctx)

	// Authenticate request
	authInfo, err := s.security.AuthenticateRequest(ctx, headers)
	if err != nil {
		s.logger.WithError(err).Warn("Authentication failed")
		return nil, fmt.Errorf("authentication failed: %w", err)
	}

	// Extract resource and namespace from tool call
	resource, namespace := parseToolArguments(toolName, arguments)
	action := parseActionFromToolName(toolName)

	// Authorize request
	err = s.security.AuthorizeRequest(ctx, authInfo, action, resource, namespace)
	if err != nil {
		s.logger.WithError(err).WithFields(logrus.Fields{
			"user": authInfo.Identity,
			"tool": toolName,
		}).Warn("Authorization failed")

		s.security.LogRequest(ctx, authInfo, toolName, resource, namespace, startTime, err)

		return nil, fmt.Errorf("access denied: %w", err)
	}

	// Add authentication info to context for the actual tool execution
	ctxWithAuth := context.WithValue(ctx, AuthInfoContextKey, authInfo)

	// Call the original tool implementation through the tool executor
	result := s.Server.toolExecutor.ExecuteTool(ctxWithAuth, toolName, arguments)

	// Log the request
	s.security.LogRequest(ctx, authInfo, toolName, resource, namespace, startTime, nil)

	// Check if execution was successful
	if !result.Success {
		return nil, fmt.Errorf("tool execution failed: %s", result.Error)
	}

	return result.Data, nil
}

func extractHeadersFromContext(ctx context.Context) map[string]string {
	// This would extract headers from the actual transport context
	// For now, we'll simulate headers for demonstration
	// In a real implementation, this would depend on your transport layer (HTTP, gRPC, etc.)
	if headers, ok := ctx.Value(HeadersContextKey).(map[string]string); ok {
		return headers
	}

	// For demo purposes, create a mock authorization header
	// In production, this would come from the actual transport
	return map[string]string{
		"Authorization": "apikey demo-admin-key-67890", // Demo admin key
	}
}

func parseToolArguments(toolName string, arguments map[string]interface{}) (resource, namespace string) {
	// Extract resource and namespace from tool arguments
	if ns, ok := arguments["namespace"].(string); ok {
		namespace = ns
	}

	// Determine resource type from tool name
	switch {
	case strings.Contains(toolName, "pod"):
		resource = "pods"
	case strings.Contains(toolName, "deployment"):
		resource = "deployments"
	case strings.Contains(toolName, "service"):
		resource = "services"
	case strings.Contains(toolName, "secret"):
		resource = "secrets"
	case strings.Contains(toolName, "configmap"):
		resource = "configmaps"
	default:
		resource = "unknown"
	}

	// Default values
	if namespace == "" {
		namespace = "default"
	}

	return resource, namespace
}

func parseActionFromToolName(toolName string) string {
	// Parse action from tool name
	// Tool names follow pattern: k8s_<action>_<resource>
	// Examples: k8s_list_pods -> "list", k8s_scale_deployment -> "scale"

	parts := strings.Split(toolName, "_")
	if len(parts) >= 3 && parts[0] == "k8s" {
		return parts[1] // Return the action part
	}

	// Fallback: extract action from common patterns
	switch {
	case strings.Contains(toolName, "list"):
		return "list"
	case strings.Contains(toolName, "get") && strings.Contains(toolName, "logs"):
		return "logs"
	case strings.Contains(toolName, "get"):
		return "get"
	case strings.Contains(toolName, "scale"):
		return "scale"
	case strings.Contains(toolName, "logs"):
		return "logs"
	case strings.Contains(toolName, "restart"):
		return "restart"
	case strings.Contains(toolName, "delete"):
		return "delete"
	case strings.Contains(toolName, "create"):
		return "create"
	default:
		return "unknown"
	}
}

// GetAuthInfoFromContext extracts authentication info from context
func GetAuthInfoFromContext(ctx context.Context) (*auth.AuthInfo, bool) {
	authInfo, ok := ctx.Value(AuthInfoContextKey).(*auth.AuthInfo)
	return authInfo, ok
}
