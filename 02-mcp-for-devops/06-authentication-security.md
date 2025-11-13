# Chapter 6: Authentication & Security

*Implementing robust security measures for production-ready MCP servers in enterprise environments*

> ⭐ **Starring** this repository to support this work

## Learning Objectives

By the end of this chapter, you will be able to:

- Implement multiple authentication mechanisms (API keys, JWT tokens)
- Design and enforce role-based access control (RBAC) policies
- Build comprehensive audit logging for security compliance
- Apply security best practices for production MCP deployments
- Configure TLS and secure communication channels
- Handle credential management and rotation securely

## Chapter Overview

Security is paramount when deploying MCP servers in production environments, especially when they have access to critical Kubernetes infrastructure. This chapter transforms our basic MCP server into a security-hardened system suitable for enterprise deployment.

We'll implement a multi-layered security approach:
1. **Authentication**: Who are you?
2. **Authorization**: What are you allowed to do?
3. **Audit**: What did you do?
4. **Transport Security**: How do we protect data in transit?

## 🚨 Security Challenges in MCP for DevOps

### Traditional DevOps Security Pain Points

**❌ Common Security Problems:**
- Shared service accounts with overly broad permissions
- Lack of audit trails for infrastructure changes
- Insecure API endpoints exposed to AI systems
- No fine-grained access control for different user roles
- Manual credential management and rotation

**✅ MCP Security Solutions:**
- Multiple authentication methods with proper validation
- Role-based access control with namespace isolation
- Comprehensive audit logging for compliance
- Secure communication channels with TLS
- Automated credential rotation and management

### Enterprise Security Requirements

When deploying MCP servers in enterprise environments, you must address:

- **Compliance**: SOC 2, ISO 27001, PCI DSS requirements
- **Zero Trust**: Never trust, always verify principle
- **Least Privilege**: Minimal required permissions only
- **Audit Trails**: Complete logging for security investigations
- **Incident Response**: Rapid detection and response to security events

---

## 🏗️ Security Architecture Overview

Our secure MCP server implements a layered security model:

```mermaid
graph TB
    A[AI Client] --> B[TLS Termination]
    B --> C[Authentication Layer]
    C --> D[Authorization Layer]
    D --> E[Audit Logger]
    E --> F[MCP Server Core]
    F --> G[Kubernetes API]
    
    H[Security Middleware] --> C
    H --> D
    H --> E
    
    I[RBAC Policies] --> D
    J[Auth Providers] --> C
    K[Audit Storage] --> E
```

### Security Components

1. **Authentication Layer**: Multiple auth methods (API key, JWT)
2. **Authorization Engine**: RBAC with fine-grained permissions
3. **Audit System**: Comprehensive logging and monitoring
4. **Security Middleware**: Request validation and security headers
5. **TLS Configuration**: Secure transport encryption

---

## 🔑 Part 1: Multi-Factor Authentication System

### Understanding Authentication Flow

```mermaid
sequenceDiagram
    participant AI as AI Client
    participant MW as Security Middleware
    participant MA as MultiAuthenticator
    participant AP as Auth Provider
    participant AU as Audit Logger

    AI->>MW: Request with Auth Header
    MW->>MA: Parse & Authenticate
    MA->>AP: Validate Credentials
    AP-->>MA: AuthInfo or Error
    MA-->>MW: Authentication Result
    MW->>AU: Log Auth Event
    MW-->>AI: Success/Failure Response
```

### 1.1 Authentication Architecture

Let's examine our multi-authenticator system:

```go
// pkg/auth/common.go
package auth

import (
    "context"
    "fmt"
)

type AuthInfo struct {
    Type        string                 `json:"type"`
    Identity    string                 `json:"identity"`
    Permissions []string               `json:"permissions"`
    Metadata    map[string]interface{} `json:"metadata"`
}

type Authenticator interface {
    Authenticate(ctx context.Context, credentials string) (*AuthInfo, error)
}

type MultiAuthenticator struct {
    authenticators map[string]Authenticator
}

func NewMultiAuthenticator() *MultiAuthenticator {
    return &MultiAuthenticator{
        authenticators: make(map[string]Authenticator),
    }
}

func (m *MultiAuthenticator) AddAuthenticator(name string, auth Authenticator) {
    m.authenticators[name] = auth
}

func (m *MultiAuthenticator) Authenticate(ctx context.Context, authType, credentials string) (*AuthInfo, error) {
    authenticator, exists := m.authenticators[authType]
    if !exists {
        return nil, fmt.Errorf("unsupported authentication type: %s", authType)
    }

    return authenticator.Authenticate(ctx, credentials)
}
```

**Key Design Principles:**
- **Extensible**: Easy to add new authentication methods
- **Type-Safe**: Strong typing for authentication information
- **Context-Aware**: Proper context propagation for cancellation
- **Error Handling**: Clear error messages for debugging

### 1.2 API Key Authentication

API keys provide simple, stateless authentication perfect for service-to-service communication:

```go
// pkg/auth/apikey.go
package auth

import (
    "context"
    "crypto/subtle"
    "fmt"
    "strings"
)

type APIKeyAuthenticator struct {
    keys map[string]*APIKeyInfo
}

type APIKeyInfo struct {
    Identity    string   `json:"identity"`
    Permissions []string `json:"permissions"`
    Enabled     bool     `json:"enabled"`
}

func NewAPIKeyAuthenticator() *APIKeyAuthenticator {
    return &APIKeyAuthenticator{
        keys: make(map[string]*APIKeyInfo),
    }
}

func (a *APIKeyAuthenticator) AddAPIKey(key string, info *APIKeyInfo) {
    a.keys[key] = info
}

func (a *APIKeyAuthenticator) Authenticate(ctx context.Context, credentials string) (*AuthInfo, error) {
    // Remove "Bearer " prefix if present
    apiKey := strings.TrimPrefix(credentials, "Bearer ")
    
    // Find matching key using constant-time comparison
    var keyInfo *APIKeyInfo
    var found bool
    
    for storedKey, info := range a.keys {
        if subtle.ConstantTimeCompare([]byte(apiKey), []byte(storedKey)) == 1 {
            keyInfo = info
            found = true
            break
        }
    }
    
    if !found {
        return nil, fmt.Errorf("invalid API key")
    }
    
    if !keyInfo.Enabled {
        return nil, fmt.Errorf("API key is disabled")
    }
    
    return &AuthInfo{
        Type:        "apikey",
        Identity:    keyInfo.Identity,
        Permissions: keyInfo.Permissions,
        Metadata: map[string]interface{}{
            "key_type": "api_key",
        },
    }, nil
}
```

**Security Features:**
- **Constant-Time Comparison**: Prevents timing attacks
- **Key Management**: Enable/disable keys without code changes
- **Permission Mapping**: Each key has specific permissions

### 1.3 JWT Token Authentication

JWT tokens provide stateless authentication with embedded claims:

```go
// pkg/auth/jwt.go
package auth

import (
    "context"
    "fmt"
    "strings"
    "time"

    "github.com/golang-jwt/jwt/v5"
)

type JWTAuthenticator struct {
    secretKey []byte
    issuer    string
}

type JWTClaims struct {
    Identity    string   `json:"identity"`
    Permissions []string `json:"permissions"`
    jwt.RegisteredClaims
}

func NewJWTAuthenticator(secretKey []byte, issuer string) *JWTAuthenticator {
    return &JWTAuthenticator{
        secretKey: secretKey,
        issuer:    issuer,
    }
}

func (j *JWTAuthenticator) Authenticate(ctx context.Context, credentials string) (*AuthInfo, error) {
    // Remove "Bearer " prefix
    tokenString := strings.TrimPrefix(credentials, "Bearer ")
    
    // Parse and validate token
    token, err := jwt.ParseWithClaims(tokenString, &JWTClaims{}, func(token *jwt.Token) (interface{}, error) {
        // Validate signing method
        if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
            return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
        }
        return j.secretKey, nil
    })
    
    if err != nil {
        return nil, fmt.Errorf("invalid JWT token: %w", err)
    }
    
    // Extract claims
    claims, ok := token.Claims.(*JWTClaims)
    if !ok || !token.Valid {
        return nil, fmt.Errorf("invalid JWT claims")
    }
    
    // Validate issuer
    if claims.Issuer != j.issuer {
        return nil, fmt.Errorf("invalid JWT issuer")
    }
    
    // Check expiration
    if time.Now().After(claims.ExpiresAt.Time) {
        return nil, fmt.Errorf("JWT token expired")
    }
    
    return &AuthInfo{
        Type:        "jwt",
        Identity:    claims.Identity,
        Permissions: claims.Permissions,
        Metadata: map[string]interface{}{
            "token_type": "jwt",
            "issued_at":  claims.IssuedAt.Time,
            "expires_at": claims.ExpiresAt.Time,
        },
    }, nil
}

func (j *JWTAuthenticator) GenerateToken(identity string, permissions []string, expiry time.Duration) (string, error) {
    claims := &JWTClaims{
        Identity:    identity,
        Permissions: permissions,
        RegisteredClaims: jwt.RegisteredClaims{
            Issuer:    j.issuer,
            IssuedAt:  jwt.NewNumericDate(time.Now()),
            ExpiresAt: jwt.NewNumericDate(time.Now().Add(expiry)),
        },
    }
    
    token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
    return token.SignedString(j.secretKey)
}
```

**Security Features:**
- **Token Validation**: Comprehensive signature and claim validation
- **Expiration Handling**: Automatic token expiration checking
- **Issuer Verification**: Ensures tokens come from trusted source
- **Algorithm Validation**: Prevents algorithm substitution attacks

---

## Part 2: Role-Based Access Control (RBAC)

### 2.1 RBAC Architecture

RBAC provides fine-grained access control based on user roles and permissions:

```mermaid
graph LR
    A[User] --> B[Role Assignment]
    B --> C[Role Definition]
    C --> D[Permissions]
    D --> E[Resource Access]
    
    F[Namespace] --> E
    G[Action Type] --> E
```

### 2.2 Permission System

Our RBAC system defines granular permissions for Kubernetes operations:

```go
// pkg/rbac/policies.go
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
    Namespaces  []string     `yaml:"namespaces,omitempty"`
}

type Policy struct {
    Roles []Role `yaml:"roles"`
}
```

### 2.3 RBAC Policy Engine

The policy engine enforces access control decisions:

```go
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

func (r *RBACEnforcer) CheckPermission(ctx context.Context, userPermissions []string, requiredPermission Permission, namespace string) error {
    // Check direct permissions
    for _, userPerm := range userPermissions {
        if Permission(userPerm) == requiredPermission {
            r.logger.WithFields(logrus.Fields{
                "direct_permission": userPerm,
                "namespace":         namespace,
            }).Debug("Direct permission granted")
            return nil
        }

        // Check wildcard permissions
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

        // Check admin access
        if userPerm == "k8s:*" {
            r.logger.WithFields(logrus.Fields{
                "admin_permission": userPerm,
                "namespace":        namespace,
            }).Debug("Admin permission granted")
            return nil
        }
    }

    return fmt.Errorf("permission denied: %s in namespace %s", requiredPermission, namespace)
}
```

### 2.4 RBAC Policy Configuration

Define roles and permissions in YAML for easy management:

```yaml
# configs/rbac-policies.yaml
roles:
  - name: "viewer"
    description: "Read-only access to Kubernetes resources"
    permissions:
      - "k8s:pods:list"
      - "k8s:services:list"
      - "k8s:deployments:list"
      - "k8s:pods:logs"
    namespaces:
      - "default"
      - "development"

  - name: "operator"
    description: "Operational access for routine maintenance"
    permissions:
      - "k8s:pods:*"
      - "k8s:services:list"
      - "k8s:deployments:*"
    namespaces:
      - "default"
      - "development"
      - "staging"

  - name: "admin"
    description: "Full administrative access"
    permissions:
      - "k8s:*"
    # No namespaces = access to all namespaces

  - name: "developer"
    description: "Development environment access"
    permissions:
      - "k8s:pods:list"
      - "k8s:pods:logs"
      - "k8s:deployments:list"
      - "k8s:deployments:scale"
    namespaces:
      - "development"
      - "feature-*"  # Wildcard namespace matching
```

**RBAC Features:**
- **Role-Based**: Clear separation of concerns
- **Namespace Isolation**: Control access by namespace
- **Wildcard Support**: Flexible permission patterns
- **YAML Configuration**: Easy policy management

---

## 📊 Part 3: Comprehensive Audit Logging

### 3.1 Audit Event Structure

Comprehensive audit logging tracks all security-relevant events:

```go
// pkg/audit/logger.go
package audit

import (
    "context"
    "encoding/json"
    "fmt"
    "time"

    "github.com/sirupsen/logrus"
)

type AuditEvent struct {
    Timestamp    time.Time              `json:"timestamp"`
    EventID      string                 `json:"event_id"`
    EventType    string                 `json:"event_type"`
    User         string                 `json:"user"`
    Action       string                 `json:"action"`
    Resource     string                 `json:"resource"`
    Namespace    string                 `json:"namespace,omitempty"`
    Result       string                 `json:"result"` // "success", "failure", "error"
    ErrorMessage string                 `json:"error_message,omitempty"`
    Metadata     map[string]interface{} `json:"metadata,omitempty"`
    Duration     time.Duration          `json:"duration_ms"`
}
```

### 3.2 Specialized Audit Methods

The audit logger provides specialized methods for different event types:

```go
func (a *AuditLogger) LogAuthentication(ctx context.Context, user, authType string, success bool, errorMsg string) {
    result := "success"
    if !success {
        result = "failure"
    }

    event := &AuditEvent{
        EventType: "authentication",
        User:      user,
        Action:    "authenticate",
        Result:    result,
        ErrorMessage: errorMsg,
        Metadata: map[string]interface{}{
            "auth_type": authType,
        },
    }

    a.LogEvent(ctx, event)
}

func (a *AuditLogger) LogAuthorization(ctx context.Context, user, action, resource, namespace string, success bool) {
    result := "success"
    if !success {
        result = "failure"
    }

    event := &AuditEvent{
        EventType: "authorization",
        User:      user,
        Action:    action,
        Resource:  resource,
        Namespace: namespace,
        Result:    result,
        Metadata: map[string]interface{}{
            "permission_check": fmt.Sprintf("%s:%s", resource, action),
        },
    }

    a.LogEvent(ctx, event)
}

func (a *AuditLogger) LogMCPRequest(ctx context.Context, user, action, resource, namespace string, startTime time.Time, err error) {
    result := "success"
    errorMsg := ""
    if err != nil {
        result = "error"
        errorMsg = err.Error()
    }

    event := &AuditEvent{
        EventType: "mcp_request",
        User:      user,
        Action:    action,
        Resource:  resource,
        Namespace: namespace,
        Result:    result,
        ErrorMessage: errorMsg,
        Duration:  time.Since(startTime),
        Metadata: map[string]interface{}{
            "request_id": generateRequestID(),
        },
    }

    a.LogEvent(ctx, event)
}
```

### 3.3 Audit Event Examples

Here are examples of audit events for different scenarios:

**Successful Authentication:**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "event_id": "auth_12345",
  "event_type": "authentication",
  "user": "admin@company.com",
  "action": "authenticate",
  "result": "success",
  "metadata": {
    "auth_type": "jwt"
  }
}
```

**Failed Authorization:**
```json
{
  "timestamp": "2024-01-15T10:31:00Z",
  "event_id": "authz_12346",
  "event_type": "authorization",
  "user": "developer@company.com",
  "action": "delete",
  "resource": "pods",
  "namespace": "production",
  "result": "failure",
  "metadata": {
    "permission_check": "pods:delete"
  }
}
```

**MCP Request:**
```json
{
  "timestamp": "2024-01-15T10:32:00Z",
  "event_id": "mcp_12347",
  "event_type": "mcp_request",
  "user": "operator@company.com",
  "action": "scale",
  "resource": "deployments",
  "namespace": "staging",
  "result": "success",
  "duration_ms": 1250,
  "metadata": {
    "request_id": "req_abc123"
  }
}
```

---

## 🔒 Part 4: Security Middleware Integration

### 4.1 Security Middleware Architecture

The security middleware orchestrates authentication, authorization, and audit logging:

```go
// pkg/security/middleware.go
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
```

### 4.2 Request Processing Flow

The middleware processes each request through the security pipeline:

```go
func (s *SecurityMiddleware) AuthenticateRequest(ctx context.Context, headers map[string]string) (*auth.AuthInfo, error) {
    // Extract authentication information
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
```

### 4.3 Secure MCP Server Integration

The secure MCP server wraps the original server with security middleware:

```go
// pkg/mcp/secure_server.go
package mcp

import (
    "context"
    "encoding/json"
    "fmt"
    "time"

    "kubernetes-mcp-server/pkg/security"
    "kubernetes-mcp-server/pkg/auth"
)

type SecureMCPServer struct {
    server     *MCPServer
    middleware *security.SecurityMiddleware
}

func NewSecureMCPServer(server *MCPServer, middleware *security.SecurityMiddleware) *SecureMCPServer {
    return &SecureMCPServer{
        server:     server,
        middleware: middleware,
    }
}

func (s *SecureMCPServer) HandleRequest(ctx context.Context, request *MCPRequest) (*MCPResponse, error) {
    startTime := time.Now()

    // Extract headers from request
    headers := extractHeaders(request)

    // Authenticate request
    authInfo, err := s.middleware.AuthenticateRequest(ctx, headers)
    if err != nil {
        return nil, fmt.Errorf("authentication failed: %w", err)
    }

    // Extract action, resource, and namespace from request
    action, resource, namespace := parseRequestDetails(request)

    // Authorize request
    err = s.middleware.AuthorizeRequest(ctx, authInfo, action, resource, namespace)
    if err != nil {
        return nil, fmt.Errorf("authorization failed: %w", err)
    }

    // Add authentication info to context
    ctx = context.WithValue(ctx, "auth_info", authInfo)

    // Process request
    response, err := s.server.HandleRequest(ctx, request)

    // Log request
    s.middleware.LogRequest(ctx, authInfo, action, resource, namespace, startTime, err)

    return response, err
}
```

---

## Part 5: TLS and Transport Security

### 5.1 TLS Configuration

Secure communication channels are essential for production deployments:

```go
// pkg/security/tls.go
package security

import (
    "crypto/tls"
    "crypto/x509"
    "fmt"
    "io/ioutil"
)

type TLSConfig struct {
    CertFile string
    KeyFile  string
    CAFile   string
}

func NewTLSConfig(certFile, keyFile, caFile string) (*tls.Config, error) {
    cert, err := tls.LoadX509KeyPair(certFile, keyFile)
    if err != nil {
        return nil, fmt.Errorf("failed to load certificate: %w", err)
    }

    tlsConfig := &tls.Config{
        Certificates: []tls.Certificate{cert},
        MinVersion:   tls.VersionTLS12,
        CipherSuites: []uint16{
            tls.TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,
            tls.TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305,
            tls.TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384,
            tls.TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305,
        },
    }

    // Load CA certificate if provided
    if caFile != "" {
        caCert, err := ioutil.ReadFile(caFile)
        if err != nil {
            return nil, fmt.Errorf("failed to read CA certificate: %w", err)
        }

        caCertPool := x509.NewCertPool()
        if !caCertPool.AppendCertsFromPEM(caCert) {
            return nil, fmt.Errorf("failed to parse CA certificate")
        }

        tlsConfig.ClientCAs = caCertPool
        tlsConfig.ClientAuth = tls.RequireAndVerifyClientCert
    }

    return tlsConfig, nil
}
```

**TLS Security Features:**
- **Modern TLS**: TLS 1.2+ only with secure cipher suites
- **Certificate Validation**: Proper certificate chain validation
- **Client Certificates**: Mutual TLS authentication support
- **Secure Defaults**: Hardened configuration out of the box

---

## Part 6: Hands-On Lab - Implementing Secure MCP Server

### Lab Setup

Let's build and test our secure MCP server step by step.

#### Step 1: Environment Preparation

```bash
# Navigate to the code directory
cd 02-mcp-for-devops/code/06

# Install dependencies
go mod download

# Generate TLS certificates for testing
mkdir -p certs
openssl req -x509 -newkey rsa:4096 -keyout certs/server.key -out certs/server.crt -days 365 -nodes -subj "/CN=localhost"
```

#### Step 2: Configure Authentication

Create API keys and JWT configuration:

```go
// cmd/server/main.go
func setupAuthentication() *auth.MultiAuthenticator {
    multiAuth := auth.NewMultiAuthenticator()

    // Setup API Key authentication
    apiKeyAuth := auth.NewAPIKeyAuthenticator()
    apiKeyAuth.AddAPIKey("mcp-admin-key-12345", &auth.APIKeyInfo{
        Identity:    "admin@company.com",
        Permissions: []string{"k8s:*"},
        Enabled:     true,
    })
    apiKeyAuth.AddAPIKey("mcp-viewer-key-67890", &auth.APIKeyInfo{
        Identity:    "viewer@company.com",
        Permissions: []string{"k8s:pods:list", "k8s:services:list"},
        Enabled:     true,
    })

    // Setup JWT authentication
    jwtSecret := []byte("your-256-bit-secret-key-here")
    jwtAuth := auth.NewJWTAuthenticator(jwtSecret, "mcp-server")

    multiAuth.AddAuthenticator("apikey", apiKeyAuth)
    multiAuth.AddAuthenticator("bearer", jwtAuth)

    return multiAuth
}
```

#### Step 3: Load RBAC Policies

```go
func setupRBAC(logger *logrus.Logger) (*rbac.RBACEnforcer, error) {
    rbacEnforcer := rbac.NewRBACEnforcer(logger)

    // Load RBAC policies from file
    policyData, err := ioutil.ReadFile("configs/rbac-policies.yaml")
    if err != nil {
        return nil, fmt.Errorf("failed to read RBAC policies: %w", err)
    }

    err = rbacEnforcer.LoadPolicy(policyData)
    if err != nil {
        return nil, fmt.Errorf("failed to load RBAC policies: %w", err)
    }

    return rbacEnforcer, nil
}
```

#### Step 4: Initialize Secure Server

```go
func main() {
    // Setup logging
    logger := logrus.New()
    logger.SetFormatter(&logrus.JSONFormatter{})

    // Setup audit logging
    auditLogger := audit.NewAuditLogger(logger)

    // Setup authentication
    multiAuth := setupAuthentication()

    // Setup RBAC
    rbacEnforcer, err := setupRBAC(logger)
    if err != nil {
        logger.Fatal(err)
    }

    // Setup security middleware
    securityMiddleware := security.NewSecurityMiddleware(
        multiAuth,
        rbacEnforcer,
        auditLogger,
        logger,
    )

    // Create Kubernetes client
    k8sClient, err := k8s.NewClient()
    if err != nil {
        logger.Fatal(err)
    }

    // Create base MCP server
    mcpServer := mcp.NewMCPServer(k8sClient, logger)

    // Wrap with security
    secureServer := mcp.NewSecureMCPServer(mcpServer, securityMiddleware)

    // Setup TLS
    tlsConfig, err := security.NewTLSConfig("certs/server.crt", "certs/server.key", "")
    if err != nil {
        logger.Fatal(err)
    }

    // Start secure server
    logger.Info("Starting secure MCP server on :8443")
    if err := startHTTPSServer(secureServer, tlsConfig); err != nil {
        logger.Fatal(err)
    }
}
```

#### Step 5: Testing Security Features

**Test API Key Authentication:**
```bash
# Valid API key
curl -k -H "Authorization: Bearer mcp-admin-key-12345" \
     https://localhost:8443/mcp/resources

# Invalid API key
curl -k -H "Authorization: Bearer invalid-key" \
     https://localhost:8443/mcp/resources
```

**Test JWT Authentication:**
```bash
# Generate JWT token (you'll need to implement token generation endpoint)
curl -k -X POST -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "secret"}' \
     https://localhost:8443/auth/token

# Use JWT token
curl -k -H "Authorization: Bearer <jwt-token>" \
     https://localhost:8443/mcp/resources
```

**Test RBAC:**
```bash
# Admin access (should work)
curl -k -H "Authorization: Bearer mcp-admin-key-12345" \
     -X POST https://localhost:8443/mcp/tools/scale_deployment \
     -d '{"name": "nginx", "namespace": "default", "replicas": 3}'

# Viewer access (should fail)
curl -k -H "Authorization: Bearer mcp-viewer-key-67890" \
     -X POST https://localhost:8443/mcp/tools/scale_deployment \
     -d '{"name": "nginx", "namespace": "default", "replicas": 3}'
```

#### Step 6: Monitor Audit Logs

```bash
# Watch audit logs
tail -f /var/log/mcp-server/audit.log | jq .

# Or if using stdout logging
docker logs -f mcp-server | grep "event_type"
```

---

## 📊 Part 7: Security Monitoring and Alerting

### 7.1 Security Metrics

Monitor security-related metrics for your MCP server:

```go
// pkg/metrics/security.go
package metrics

import (
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promauto"
)

var (
    AuthenticationAttempts = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "mcp_authentication_attempts_total",
            Help: "Total number of authentication attempts",
        },
        []string{"auth_type", "result"},
    )

    AuthorizationChecks = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "mcp_authorization_checks_total",
            Help: "Total number of authorization checks",
        },
        []string{"user", "resource", "action", "result"},
    )

    SecurityViolations = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "mcp_security_violations_total",
            Help: "Total number of security violations",
        },
        []string{"violation_type", "user"},
    )
)
```

### 7.2 Security Alerts

Configure alerts for security events:

```yaml
# alerts/security.yaml
groups:
  - name: mcp-security
    rules:
      - alert: HighFailedAuthentications
        expr: rate(mcp_authentication_attempts_total{result="failure"}[5m]) > 10
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High number of failed authentication attempts"
          description: "{{ $value }} failed authentication attempts per second"

      - alert: UnauthorizedAccess
        expr: increase(mcp_authorization_checks_total{result="failure"}[5m]) > 5
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Multiple authorization failures detected"
          description: "User {{ $labels.user }} had {{ $value }} authorization failures"

      - alert: SecurityViolation
        expr: increase(mcp_security_violations_total[1m]) > 0
        for: 0s
        labels:
          severity: critical
        annotations:
          summary: "Security violation detected"
          description: "{{ $labels.violation_type }} violation by {{ $labels.user }}"
```

---

## Part 8: Real-World Security Scenarios

### Scenario 1: SOC 2 Compliance

**Requirements:**
- Complete audit trail of all access and actions
- User access reviews and permission management
- Encryption in transit and at rest
- Incident response procedures

**Implementation:**
```go
// Enhanced audit logging for compliance
func (a *AuditLogger) LogComplianceEvent(ctx context.Context, event *ComplianceEvent) {
    auditEvent := &AuditEvent{
        EventType: "compliance",
        User:      event.User,
        Action:    event.Action,
        Resource:  event.Resource,
        Result:    event.Result,
        Metadata: map[string]interface{}{
            "compliance_framework": "soc2",
            "control_objective":    event.ControlObjective,
            "evidence_reference":   event.EvidenceRef,
        },
    }

    a.LogEvent(ctx, auditEvent)
}
```

### Scenario 2: Zero Trust Architecture

**Implementation:**
```go
// Zero trust security middleware
func (s *SecurityMiddleware) ZeroTrustCheck(ctx context.Context, request *MCPRequest) error {
    // Always verify identity
    authInfo := ctx.Value("auth_info").(*auth.AuthInfo)
    if authInfo == nil {
        return fmt.Errorf("no authentication context found")
    }

    // Check request patterns for anomalies
    if s.isAnomalousRequest(authInfo.Identity, request) {
        s.auditLogger.LogSecurityViolation(ctx, authInfo.Identity, "anomalous_request")
        return fmt.Errorf("anomalous request pattern detected")
    }

    // Verify request integrity
    if !s.verifyRequestIntegrity(request) {
        s.auditLogger.LogSecurityViolation(ctx, authInfo.Identity, "integrity_violation")
        return fmt.Errorf("request integrity check failed")
    }

    return nil
}
```

### Scenario 3: Multi-Tenant Security

**Implementation:**
```go
// Tenant isolation enforcement
func (s *SecurityMiddleware) EnforceTenantIsolation(ctx context.Context, authInfo *auth.AuthInfo, namespace string) error {
    // Extract tenant from auth info
    tenant, ok := authInfo.Metadata["tenant"].(string)
    if !ok {
        return fmt.Errorf("no tenant information found")
    }

    // Validate namespace belongs to tenant
    if !s.validateNamespaceTenant(namespace, tenant) {
        s.auditLogger.LogSecurityViolation(ctx, authInfo.Identity, "tenant_isolation_violation")
        return fmt.Errorf("access to namespace %s denied for tenant %s", namespace, tenant)
    }

    return nil
}
```

---

## 📝 Chapter Summary

In this chapter, we've built a comprehensive security system for our MCP server that includes:

### What We've Accomplished

1. **Multi-Factor Authentication**
   - API key authentication with constant-time comparison
   - JWT token authentication with proper validation
   - Extensible authentication framework

2. **Role-Based Access Control**
   - Fine-grained permission system
   - Namespace isolation support
   - YAML-based policy management
   - Wildcard permissions and inheritance

3. **Comprehensive Audit Logging**
   - Structured audit events in JSON format
   - Authentication, authorization, and request logging
   - Security violation tracking
   - Compliance-ready audit trails

4. **Security Middleware**
   - Integrated security pipeline
   - Request validation and sanitization
   - Security header management
   - Error handling and logging

5. **Transport Security**
   - TLS 1.2+ with secure cipher suites
   - Certificate validation and management
   - Mutual TLS support

### 🔒 Security Benefits

- **Defense in Depth**: Multiple security layers
- **Principle of Least Privilege**: Minimal required permissions
- **Complete Audit Trail**: Comprehensive logging for compliance
- **Zero Trust Ready**: Never trust, always verify
- **Enterprise Grade**: SOC 2 and ISO 27001 compliance support

### Next Steps

In Chapter 7, we'll explore advanced MCP patterns including:
- Event-driven MCP servers with Kubernetes watch APIs
- Multi-cluster federation patterns
- Custom Resource Definition (CRD) integration
- Advanced caching and performance optimization
- Service mesh integration patterns

The security foundation we've built in this chapter will support all these advanced features while maintaining enterprise-grade security standards.

---

## Key Takeaways

1. **Security is Not Optional**: Production MCP servers must implement comprehensive security measures
2. **Layered Defense**: Combine authentication, authorization, audit, and transport security
3. **Compliance Ready**: Design with regulatory requirements in mind from the start
4. **Audit Everything**: Comprehensive logging is essential for security and compliance
5. **Zero Trust Mindset**: Verify every request, never assume trust

With these security measures in place, your MCP server is ready for enterprise deployment and can safely interact with critical Kubernetes infrastructure while maintaining complete audit trails and access controls.
