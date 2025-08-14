package rbac

import (
	"context"
	"fmt"
	"strings"

	"github.com/sirupsen/logrus"
	"gopkg.in/yaml.v3"
)

type Permission string

const (
	// Kubernetes resource permissions
	PermissionListPods        Permission = "k8s:pods:list"
	PermissionGetPodLogs      Permission = "k8s:pods:logs"
	PermissionScaleDeployment Permission = "k8s:deployments:scale"
	PermissionRestartPod      Permission = "k8s:pods:restart"
	PermissionListServices    Permission = "k8s:services:list"
	PermissionListDeployments Permission = "k8s:deployments:list"

	// Admin permissions
	PermissionManageSecrets   Permission = "k8s:secrets:manage"
	PermissionDeletePods      Permission = "k8s:pods:delete"
	PermissionCreateResources Permission = "k8s:resources:create"
)

type Role struct {
	Name        string       `yaml:"name"`
	Description string       `yaml:"description"`
	Permissions []Permission `yaml:"permissions"`
	Namespaces  []string     `yaml:"namespaces,omitempty"` // Empty means all namespaces
}

type Policy struct {
	Roles []Role `yaml:"roles"`
}

type RBACEnforcer struct {
	policy *Policy
	logger *logrus.Logger
}

func NewRBACEnforcer(logger *logrus.Logger) *RBACEnforcer {
	return &RBACEnforcer{
		policy: &Policy{},
		logger: logger,
	}
}

func (r *RBACEnforcer) LoadPolicy(policyYAML []byte) error {
	err := yaml.Unmarshal(policyYAML, r.policy)
	if err != nil {
		return fmt.Errorf("failed to parse RBAC policy: %w", err)
	}

	r.logger.WithField("roles_count", len(r.policy.Roles)).Info("RBAC policy loaded")
	return nil
}

func (r *RBACEnforcer) CheckPermission(ctx context.Context, userPermissions []string, requiredPermission Permission, namespace string) error {
	// First, check for direct permissions (non-role based)
	for _, userPerm := range userPermissions {
		if Permission(userPerm) == requiredPermission {
			r.logger.WithFields(logrus.Fields{
				"direct_permission": userPerm,
				"namespace":         namespace,
			}).Debug("Direct permission granted")
			return nil
		}

		// Check for wildcard permissions
		if strings.HasSuffix(userPerm, ":*") {
			prefix := strings.TrimSuffix(userPerm, "*")
			if strings.HasPrefix(string(requiredPermission), prefix) {
				r.logger.WithFields(logrus.Fields{
					"wildcard_permission": userPerm,
					"namespace":           namespace,
				}).Debug("Wildcard permission granted")
				return nil
			}
		}

		// Check for full wildcard (admin access)
		if userPerm == "k8s:*" {
			r.logger.WithFields(logrus.Fields{
				"admin_permission": userPerm,
				"namespace":        namespace,
			}).Debug("Admin permission granted")
			return nil
		}
	}

	// If no direct permissions found, try role-based permissions
	userRoles := r.getUserRoles(userPermissions)

	for _, roleName := range userRoles {
		role := r.findRole(roleName)
		if role == nil {
			continue
		}

		// Check if role has the required permission
		if r.roleHasPermission(role, requiredPermission) {
			// Check namespace access
			if r.roleHasNamespaceAccess(role, namespace) {
				r.logger.WithFields(logrus.Fields{
					"role":       roleName,
					"permission": requiredPermission,
					"namespace":  namespace,
				}).Debug("Permission granted")
				return nil
			}
		}
	}

	r.logger.WithFields(logrus.Fields{
		"user_permissions":    userPermissions,
		"required_permission": requiredPermission,
		"namespace":           namespace,
	}).Warn("Permission denied")

	return fmt.Errorf("permission denied: %s in namespace %s", requiredPermission, namespace)
}

func (r *RBACEnforcer) getUserRoles(permissions []string) []string {
	var roles []string
	for _, permission := range permissions {
		// Extract role from permission format: "role:admin" or just "admin"
		if strings.HasPrefix(permission, "role:") {
			roles = append(roles, strings.TrimPrefix(permission, "role:"))
		} else if !strings.Contains(permission, ":") {
			// Assume it's a role name if no colon
			roles = append(roles, permission)
		}
	}
	return roles
}

func (r *RBACEnforcer) findRole(roleName string) *Role {
	for _, role := range r.policy.Roles {
		if role.Name == roleName {
			return &role
		}
	}
	return nil
}

func (r *RBACEnforcer) roleHasPermission(role *Role, permission Permission) bool {
	for _, rolePermission := range role.Permissions {
		if rolePermission == permission {
			return true
		}
		// Check for wildcard permissions
		if strings.HasSuffix(string(rolePermission), ":*") {
			prefix := strings.TrimSuffix(string(rolePermission), "*")
			if strings.HasPrefix(string(permission), prefix) {
				return true
			}
		}
	}
	return false
}

func (r *RBACEnforcer) roleHasNamespaceAccess(role *Role, namespace string) bool {
	// Empty namespaces list means access to all namespaces
	if len(role.Namespaces) == 0 {
		return true
	}

	for _, allowedNamespace := range role.Namespaces {
		if allowedNamespace == namespace || allowedNamespace == "*" {
			return true
		}
	}
	return false
}
