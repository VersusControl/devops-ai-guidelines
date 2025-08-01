package mcp

import (
	"context"
	"fmt"
	"kubernetes-mcp-server/internal/config"
	"kubernetes-mcp-server/internal/logging"
	"kubernetes-mcp-server/pkg/k8s"
	"kubernetes-mcp-server/pkg/tools"

	"github.com/mark3labs/mcp-go/server"
)

// Server represents the MCP server
type Server struct {
	config       *config.Config
	k8sClient    *k8s.Client
	logger       *logging.Logger
	mcpServer    *server.MCPServer
	toolExecutor *tools.ToolExecutor
	formatter    *ResourceFormatter
	ctx          context.Context // Store context for tool operations
}

// NewServer creates a new MCP server instance with proper MCP protocol implementation
func NewServer(cfg *config.Config, k8sClient *k8s.Client) *Server {
	logger := logging.NewLogger("info", "text")

	// Create MCP server
	mcpServer := server.NewMCPServer(
		"k8s-mcp-server",
		"1.0.0",
		server.WithResourceCapabilities(true, true),
		server.WithToolCapabilities(true),
	)

	s := &Server{
		config:       cfg,
		k8sClient:    k8sClient,
		logger:       logger,
		mcpServer:    mcpServer,
		toolExecutor: tools.NewToolExecutor(k8sClient, logger),
		formatter:    NewResourceFormatter(),
	}

	// Register MCP resources
	s.registerResources()

	// Register MCP tools
	s.registerTools()

	return s
}

// Start starts the MCP server with stdio transport
func (s *Server) Start(ctx context.Context) error {
	s.logger.Info("Starting Kubernetes MCP Server")

	// Store the context for use in tool operations
	s.ctx = ctx

	// Use the convenient ServeStdio function
	if err := server.ServeStdio(s.mcpServer); err != nil {
		s.logger.Errorf("MCP server error: %v", err)
		return fmt.Errorf("MCP server failed: %w", err)
	}

	s.logger.Info("MCP Server stopped")
	return nil
}
