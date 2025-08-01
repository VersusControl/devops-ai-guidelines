package mcp

import (
	"context"
	"fmt"
	"kubernetes-mcp-server/pkg/tools"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
)

func (s *Server) registerTools() {
	// Register tool capabilities
	toolDefinitions := tools.GetToolDefinitions()

	for _, toolDef := range toolDefinitions {
		s.mcpServer.AddTool(toolDef, s.handleToolCall)
		s.logger.Infof("Registered tool: %s", toolDef.Name)
	}

	s.logger.Infof("Registered %d tools", len(toolDefinitions))
}

// Add new method to handle tool calls
func (s *Server) handleToolCall(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	toolName := request.Params.Name
	arguments := request.Params.Arguments

	s.logger.Infof("Handling tool call: %s with arguments: %v", toolName, arguments)

	// Use the stored context from the server instead of the MCP framework context
	// This prevents tool execution from being cancelled prematurely
	result := s.toolExecutor.ExecuteTool(s.ctx, toolName, arguments.(map[string]interface{}))

	// Convert result to MCP format
	if result.Success {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				&mcp.TextContent{
					Type: "text",
					Text: formatToolResult(result),
				},
			},
		}, nil
	} else {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				&mcp.TextContent{
					Type: "text",
					Text: formatToolError(result),
				},
			},
		}, fmt.Errorf("tool execution failed: %s", result.Error)
	}
}

// formatToolResult formats successful tool execution results
func formatToolResult(result *tools.ExecuteResult) string {
	output := fmt.Sprintf("# ✅ %s\n\n", result.Message)
	output += fmt.Sprintf("**Executed at**: %s\n\n", result.Timestamp.Format(time.RFC3339))

	if len(result.Data) > 0 {
		output += "## Result Details\n\n"
		for key, value := range result.Data {
			switch v := value.(type) {
			case string:
				if key == "logs" {
					// Special handling for logs - truncate if too long
					if len(v) > 5000 {
						output += fmt.Sprintf("**%s**: (truncated to 5000 chars)\n```\n%s\n...\n```\n\n", key, v[:5000])
					} else {
						output += fmt.Sprintf("**%s**:\n```\n%s\n```\n\n", key, v)
					}
				} else {
					output += fmt.Sprintf("- **%s**: %s\n", key, v)
				}
			case int, int32, int64, float64:
				output += fmt.Sprintf("- **%s**: %v\n", key, v)
			case time.Time:
				output += fmt.Sprintf("- **%s**: %s\n", key, v.Format(time.RFC3339))
			case map[string]interface{}:
				output += fmt.Sprintf("- **%s**: %v\n", key, v)
			default:
				output += fmt.Sprintf("- **%s**: %v\n", key, v)
			}
		}
	}

	output += "\n---\n*Operation completed successfully*"
	return output
}

// formatToolError formats tool execution errors
func formatToolError(result *tools.ExecuteResult) string {
	output := fmt.Sprintf("# ❌ %s\n\n", result.Message)
	output += fmt.Sprintf("**Error**: %s\n\n", result.Error)
	output += fmt.Sprintf("**Timestamp**: %s\n\n", result.Timestamp.Format(time.RFC3339))

	output += "## Troubleshooting\n\n"
	output += "- Check that the resource exists and you have permission to access it\n"
	output += "- Verify that the namespace and resource names are correct\n"
	output += "- Ensure the Kubernetes cluster is accessible\n"
	output += "- Review the error message above for specific details\n\n"

	output += "---\n*Operation failed - review the error details above*"
	return output
}
