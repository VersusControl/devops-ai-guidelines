package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/sirupsen/logrus"

	"kubernetes-mcp-server/internal/config"
	"kubernetes-mcp-server/internal/logging"
	"kubernetes-mcp-server/pkg/audit"
	"kubernetes-mcp-server/pkg/auth"
	"kubernetes-mcp-server/pkg/k8s"
	"kubernetes-mcp-server/pkg/mcp"
	"kubernetes-mcp-server/pkg/rbac"
	"kubernetes-mcp-server/pkg/security"
)

func main() {
	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// Initialize logger
	logger := logging.NewLogger("info", "text")
	logrusLogger := logrus.New()
	logger.Info("Starting Kubernetes MCP Server with security features")

	// Initialize Kubernetes client
	k8sClient, err := k8s.NewClient(cfg.K8s.ConfigPath, logger)
	if err != nil {
		logger.Fatalf("Failed to create Kubernetes client: %v", err)
	}

	// Test Kubernetes connection
	ctx := context.Background()
	if err := k8sClient.HealthCheck(ctx); err != nil {
		logger.Fatalf("Kubernetes health check failed: %v", err)
	}
	logger.Info("Kubernetes connection established successfully")

	// Initialize audit logger
	auditLogger := audit.NewAuditLogger(logrusLogger)

	// Initialize RBAC enforcer
	rbacEnforcer := rbac.NewRBACEnforcer(logrusLogger)

	// Load RBAC policies from file (optional - will use default policies if file doesn't exist)
	if policyData, err := os.ReadFile("./configs/rbac-policies.yaml"); err == nil {
		if err := rbacEnforcer.LoadPolicy(policyData); err != nil {
			logger.Warnf("Failed to load RBAC policies: %v", err)
		}
	} else {
		logger.Warnf("RBAC policy file not found, using default policies: %v", err)
	}

	// Initialize authenticators
	// API Key store and authenticator with demo keys
	apiKeyStore := auth.NewInMemoryAPIKeyStore(logrusLogger)
	apiKeyStore.AddAPIKey("demo-admin-key-67890", &auth.APIKeyInfo{
		ID:   "admin-key",
		Name: "Admin Key",
		Permissions: []string{
			"k8s:pods:list",
			"k8s:pods:logs",
			"k8s:pods:restart",
			"k8s:pods:delete",
			"k8s:deployments:list",
			"k8s:deployments:scale",
			"k8s:services:list",
			"k8s:secrets:manage",
			"k8s:resources:create",
			"k8s:*", // Wildcard for admin access
		},
		CreatedAt: time.Now(),
	})
	apiKeyStore.AddAPIKey("demo-user-key-12345", &auth.APIKeyInfo{
		ID:   "user-key",
		Name: "Developer Key",
		Permissions: []string{
			"k8s:pods:list",
			"k8s:pods:logs",
			"k8s:deployments:list",
		},
		CreatedAt: time.Now(),
	})
	apiKeyAuth := auth.NewAPIKeyAuthenticator(apiKeyStore, logrusLogger)

	// JWT authenticator with demo secret
	jwtAuth := auth.NewJWTAuthenticator([]byte("demo-secret-key-for-jwt-signing-change-in-production"), logrusLogger)

	// Multi-authenticator that tries API key first, then JWT
	multiAuth := auth.NewMultiAuthenticator()
	multiAuth.AddAuthenticator("apikey", apiKeyAuth)
	multiAuth.AddAuthenticator("jwt", jwtAuth)

	// Initialize security middleware
	securityMiddleware := security.NewSecurityMiddleware(multiAuth, rbacEnforcer, auditLogger, logrusLogger)

	// Create original MCP server
	mcpServer := mcp.NewServer(cfg, k8sClient)

	// Wrap with security
	secureMCPServer := mcp.NewSecureMCPServer(mcpServer, securityMiddleware, logrusLogger)

	// Start demo HTTP server for testing security features
	// In production, you would integrate with the actual MCP protocol transport
	startDemoHTTPServer(secureMCPServer, 8080, logger)
}

func startDemoHTTPServer(server *mcp.SecureMCPServer, port int, logger *logging.Logger) {
	mux := http.NewServeMux()

	// Health check endpoint
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	// MCP tool execution endpoint
	mux.HandleFunc("/mcp/tools", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Extract tool name and arguments from request
		toolName := r.URL.Query().Get("tool")
		if toolName == "" {
			http.Error(w, "Missing tool parameter", http.StatusBadRequest)
			return
		}

		// Create context with headers for authentication
		ctx := context.WithValue(r.Context(), mcp.HeadersContextKey, map[string]string{
			"Authorization": r.Header.Get("Authorization"),
		})

		// Demo arguments (in production, parse from request body)
		arguments := map[string]interface{}{
			"namespace": r.URL.Query().Get("namespace"),
		}
		if arguments["namespace"] == "" {
			arguments["namespace"] = "default"
		}

		// Parse additional tool-specific parameters from query string
		if name := r.URL.Query().Get("name"); name != "" {
			arguments["name"] = name
		}
		if replicasStr := r.URL.Query().Get("replicas"); replicasStr != "" {
			// Convert replicas to integer
			if replicas, err := strconv.Atoi(replicasStr); err == nil {
				arguments["replicas"] = replicas
			} else {
				arguments["replicas"] = replicasStr // Keep as string for validation error
			}
		}
		if container := r.URL.Query().Get("container"); container != "" {
			arguments["container"] = container
		}
		if confirmStr := r.URL.Query().Get("confirm"); confirmStr != "" {
			// Convert confirm to boolean
			if confirm, err := strconv.ParseBool(confirmStr); err == nil {
				arguments["confirm"] = confirm
			} else {
				arguments["confirm"] = confirmStr // Keep as string for validation error
			}
		}

		// Execute tool through secure server
		result, err := server.HandleToolCall(ctx, toolName, arguments)
		if err != nil {
			// Determine appropriate HTTP status code based on error type
			statusCode := http.StatusInternalServerError
			errorMessage := err.Error()

			// Check for specific error types
			if strings.Contains(errorMessage, "authentication failed") {
				statusCode = http.StatusUnauthorized
			} else if strings.Contains(errorMessage, "access denied") || strings.Contains(errorMessage, "authorization failed") {
				statusCode = http.StatusForbidden
			} else if strings.Contains(errorMessage, "validation failed") || strings.Contains(errorMessage, "missing") {
				statusCode = http.StatusBadRequest
			}

			http.Error(w, fmt.Sprintf("Tool execution failed: %v", err), statusCode)
			return
		}

		// Return result (simplified - in production use proper JSON encoding)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `{"success": true, "result": %v}`, result)
	})

	httpServer := &http.Server{
		Addr:         fmt.Sprintf(":%d", port),
		Handler:      mux,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
	}

	logger.Infof("Starting demo HTTP server on port %d", port)
	logger.Info("Try: curl -X POST -H 'Authorization: apikey demo-admin-key-67890' 'http://localhost:8080/mcp/tools?tool=k8s_list_pods&namespace=default'")

	// Handle shutdown signals
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// Start server in a goroutine
	serverErr := make(chan error, 1)
	go func() {
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			serverErr <- err
		}
	}()

	// Wait for shutdown signal or server error
	select {
	case sig := <-sigChan:
		logger.Infof("Received signal %v, initiating graceful shutdown...", sig)
	case err := <-serverErr:
		logger.Errorf("Server error: %v", err)
		return
	}

	// Gracefully shutdown
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer shutdownCancel()

	if err := httpServer.Shutdown(shutdownCtx); err != nil {
		logger.Errorf("Server forced to shutdown: %v", err)
	}

	logger.Info("Server shutdown complete")
}
