# Chapter 6: Authentication & Security - Code Implementation

This folder contains the complete implementation of the security features described in Chapter 6: Authentication & Security.

## 🔐 Security Features Implemented

### 1. Authentication System
- **API Key Authentication**: Simple and secure API key validation
- **JWT Authentication**: Token-based authentication with configurable secrets
- **Multi-Authentication**: Composite authenticator supporting multiple auth methods

### 2. Authorization System
- **RBAC (Role-Based Access Control)**: Flexible policy-based authorization
- **Resource-level permissions**: Fine-grained control over Kubernetes resources
- **Action-based access control**: Specific permissions for different operations

### 3. Audit & Monitoring
- **Comprehensive audit logging**: Track all authentication and authorization events
- **Security event monitoring**: Monitor failed login attempts and access violations
- **Structured logging**: JSON-formatted logs for easy parsing and analysis

### 4. Security Middleware
- **Request validation**: Comprehensive security checks on all requests
- **Rate limiting ready**: Foundation for implementing rate limiting
- **Security headers**: Proper security header management

### 5. TLS Configuration
- **Certificate management**: Support for custom TLS certificates
- **Secure transport**: HTTPS endpoint configuration
- **Certificate validation**: Proper certificate chain validation

## 📁 Code Structure

```
06/
├── cmd/server/main.go              # Main server with security integration
├── pkg/
│   ├── auth/                       # Authentication components
│   │   ├── common.go              # Common auth interfaces and types
│   │   ├── apikey.go              # API key authentication
│   │   └── jwt.go                 # JWT token authentication
│   ├── rbac/                      # Role-based access control
│   │   └── policies.go            # RBAC policy engine
│   ├── audit/                     # Audit logging
│   │   └── logger.go              # Structured audit logger
│   ├── security/                  # Security middleware
│   │   ├── middleware.go          # Main security middleware
│   │   └── tls.go                 # TLS configuration
│   └── mcp/
│       └── secure_server.go       # Secure MCP server wrapper
├── configs/
│   └── rbac-policies.yaml         # RBAC policy configuration
└── scripts/
    └── demo-security.sh           # Security features demo script
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
go mod tidy
```

### 2. Create Required Directories
```bash
mkdir -p logs certs
```

### 3. Build the Application
```bash
go build ./...
```

### 4. Run the Server
```bash
go run cmd/server/main.go
```

### 5. Test Security Features
```bash
./scripts/demo-security.sh
```

## 🔧 Configuration

### API Keys (Demo)
The server comes pre-configured with demo API keys:
- **Admin Key**: `demo-admin-key-67890` (cluster-admin role)
- **Developer Key**: `demo-user-key-12345` (developer role)

### JWT Configuration
- **Secret**: `demo-secret-key-for-jwt-signing-change-in-production`
- **Algorithm**: HS256
- **Expiration**: Configurable

### RBAC Policies
See `configs/rbac-policies.yaml` for role and permission definitions.

## 🧪 Testing

### Manual Testing
```bash
# Test with valid API key
curl -X POST -H 'Authorization: apikey demo-admin-key-67890' \
  'http://localhost:8080/mcp/tools?tool=k8s_list_pods&namespace=default'

# Test with invalid key (should fail)
curl -X POST -H 'Authorization: apikey invalid-key' \
  'http://localhost:8080/mcp/tools?tool=k8s_list_pods&namespace=default'
```

### Automated Testing
```bash
./scripts/demo-security.sh
```

## 📊 Monitoring & Logs

### Audit Logs
Audit logs are written to `./logs/audit.log` in JSON format:
```json
{
  "timestamp": "2024-01-15T10:30:45Z",
  "event_type": "AUTH_SUCCESS",
  "user": "admin",
  "action": "execute_k8s_list_pods",
  "resource": "pods",
  "namespace": "default",
  "result": "success"
}
```

### Health Check
```bash
curl http://localhost:8080/health
```

## 🔒 Production Deployment

### Security Checklist
- [ ] Replace demo API keys with secure, randomly generated keys
- [ ] Use environment variables for sensitive configuration
- [ ] Configure proper TLS certificates
- [ ] Set up log rotation for audit logs
- [ ] Implement rate limiting
- [ ] Configure monitoring and alerting
- [ ] Review and customize RBAC policies

### Environment Variables
```bash
export MCP_JWT_SECRET="your-secure-jwt-secret"
export MCP_API_KEYS="key1:user1:role1,key2:user2:role2"
export MCP_TLS_CERT_PATH="/path/to/cert.pem"
export MCP_TLS_KEY_PATH="/path/to/key.pem"
```

## 🛠 Development

### Adding New Authentication Methods
1. Implement the `Authenticator` interface in `pkg/auth/`
2. Add the authenticator to the multi-authenticator in `main.go`
3. Update RBAC policies if needed

### Customizing RBAC Policies
1. Edit `configs/rbac-policies.yaml`
2. Add new roles and permissions as needed
3. Restart the server to reload policies

### Extending Audit Logging
1. Add new event types in `pkg/audit/logger.go`
2. Emit audit events from relevant components
3. Configure log aggregation and monitoring

## 📖 Related Documentation

- [Chapter 6: Authentication & Security](../06-authentication-security.md)
- [MCP Server Implementation](../03-building-mcp-server-go-kubernetes.md)
- [Kubernetes Tools & Actions](../04-kubernetes-tools-actions.md)

## 🤝 Contributing

When contributing to the security components:
1. Follow secure coding practices
2. Add comprehensive tests for security features
3. Update audit logging for new operations
4. Review RBAC implications of changes
5. Update documentation

## 📝 License

This code is part of the DevOps AI Guidelines project. See the main LICENSE file for details.
