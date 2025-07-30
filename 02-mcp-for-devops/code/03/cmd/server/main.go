package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"

	"kubernetes-mcp-server/internal/config"
	"kubernetes-mcp-server/internal/logging"
	"kubernetes-mcp-server/pkg/k8s"
	"kubernetes-mcp-server/pkg/mcp"
)

func main() {
	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// Initialize logger
	logger := logging.NewLogger("info", "text")

	// Initialize Kubernetes client
	k8sClient, err := k8s.NewClient(cfg.K8s.ConfigPath, logger.Logger)
	if err != nil {
		logger.Fatalf("Failed to create Kubernetes client: %v", err)
	}

	// Test Kubernetes connection
	ctx := context.Background()
	if err := k8sClient.HealthCheck(ctx); err != nil {
		logger.Fatalf("Kubernetes health check failed: %v", err)
	}
	logger.Info("Kubernetes connection established successfully")

	// Create MCP server
	mcpServer := mcp.NewServer(cfg, k8sClient)

	// Setup graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Handle shutdown signals
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// Start server in a goroutine
	serverErr := make(chan error, 1)
	go func() {
		if err := mcpServer.Start(ctx); err != nil {
			serverErr <- err
		}
	}()

	// Wait for shutdown signal or server error
	select {
	case sig := <-sigChan:
		logger.Infof("Received signal %v, shutting down gracefully...", sig)
		cancel()
	case err := <-serverErr:
		logger.Errorf("Server error: %v", err)
		cancel()
	}

	logger.Info("Server shutdown complete")
}
