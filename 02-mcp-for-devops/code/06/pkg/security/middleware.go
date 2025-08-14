package security

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/sirupsen/logrus"

	"kubernetes-mcp-server/pkg/audit"
	"kubernetes-mcp-server/pkg/auth"
	"kubernetes-mcp-server/pkg/rbac"
)

type SecurityMiddleware struct {
	authenticator *auth.MultiAuthenticator
	rbacEnforcer  *rbac.RBACEnforcer
	auditLogger   *audit.AuditLogger
	logger        *logrus.Logger
}

func NewSecurityMiddleware(
	authenticator *auth.MultiAuthenticator,
	rbacEnforcer *rbac.RBACEnforcer,
	auditLogger *audit.AuditLogger,
	logger *logrus.Logger,
) *SecurityMiddleware {
	return &SecurityMiddleware{
		authenticator: authenticator,
		rbacEnforcer:  rbacEnforcer,
		auditLogger:   auditLogger,
		logger:        logger,
	}
}

func (s *SecurityMiddleware) AuthenticateRequest(ctx context.Context, headers map[string]string) (*auth.AuthInfo, error) {
	// Extract authentication information from headers
	authHeader := headers["Authorization"]
	if authHeader == "" {
		s.auditLogger.LogAuthentication(ctx, "anonymous", "none", false, "missing authorization header")
		return nil, fmt.Errorf("missing authorization header")
	}

	// Parse authentication type and credentials
	authType, credentials, err := parseAuthHeader(authHeader)
	if err != nil {
		s.auditLogger.LogAuthentication(ctx, "unknown", authType, false, err.Error())
		return nil, err
	}

	// Authenticate user
	authInfo, err := s.authenticator.Authenticate(ctx, authType, credentials)
	if err != nil {
		s.auditLogger.LogAuthentication(ctx, "unknown", authType, false, err.Error())
		return nil, err
	}

	// Log successful authentication
	s.auditLogger.LogAuthentication(ctx, authInfo.Identity, authType, true, "")

	return authInfo, nil
}

func (s *SecurityMiddleware) AuthorizeRequest(ctx context.Context, authInfo *auth.AuthInfo, action, resource, namespace string) error {
	// Convert action to permission
	permission := actionToPermission(action, resource)

	// Check permission
	err := s.rbacEnforcer.CheckPermission(ctx, authInfo.Permissions, permission, namespace)

	// Log authorization decision
	s.auditLogger.LogAuthorization(ctx, authInfo.Identity, action, resource, namespace, err == nil)

	return err
}

func (s *SecurityMiddleware) LogRequest(ctx context.Context, authInfo *auth.AuthInfo, action, resource, namespace string, startTime time.Time, err error) {
	s.auditLogger.LogMCPRequest(ctx, authInfo.Identity, action, resource, namespace, startTime, err)
}

func parseAuthHeader(authHeader string) (string, string, error) {
	parts := strings.SplitN(authHeader, " ", 2)
	if len(parts) != 2 {
		return "", "", fmt.Errorf("invalid authorization header format")
	}

	authType := strings.ToLower(parts[0])
	credentials := parts[1]

	switch authType {
	case "bearer":
		return "jwt", credentials, nil
	case "apikey":
		return "apikey", credentials, nil
	default:
		return "", "", fmt.Errorf("unsupported authentication type: %s", authType)
	}
}

func actionToPermission(action, resource string) rbac.Permission {
	// Map MCP actions to RBAC permissions
	switch {
	case action == "list" && resource == "pods":
		return rbac.PermissionListPods
	case action == "get_logs" && resource == "pods":
		return rbac.PermissionGetPodLogs
	case action == "scale" && resource == "deployments":
		return rbac.PermissionScaleDeployment
	case action == "restart" && resource == "pods":
		return rbac.PermissionRestartPod
	case action == "list" && resource == "services":
		return rbac.PermissionListServices
	case action == "list" && resource == "deployments":
		return rbac.PermissionListDeployments
	default:
		return rbac.Permission(fmt.Sprintf("k8s:%s:%s", resource, action))
	}
}
