// Package mcp wires metrics + rate limiting around tool handlers so every
// tool defined in earlier chapters benefits without per-tool boilerplate.
package mcp

import (
	"context"
	"fmt"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	"k8s-mcp-perf/pkg/metrics"
	"k8s-mcp-perf/pkg/ratelimit"
)

// Server wraps an mcp-go server with performance middleware.
type Server struct {
	mcp     *server.MCPServer
	rec     *metrics.Recorder
	limiter *ratelimit.Limiter
}

// New builds a fresh server. Tools must be registered through AddTool so the
// middleware is applied.
func New(name, version string, rec *metrics.Recorder, limiter *ratelimit.Limiter) *Server {
	return &Server{
		mcp: server.NewMCPServer(name, version,
			server.WithResourceCapabilities(true, true),
			server.WithToolCapabilities(true),
		),
		rec:     rec,
		limiter: limiter,
	}
}

// AddTool registers a handler wrapped with metrics + rate limiting.
func (s *Server) AddTool(tool mcp.Tool, handler server.ToolHandlerFunc) {
	wrapped := s.instrument(tool.Name, handler)
	s.mcp.AddTool(tool, wrapped)
}

// MCP exposes the underlying mcp-go server.
func (s *Server) MCP() *server.MCPServer { return s.mcp }

// ServeStdio runs stdio transport.
func (s *Server) ServeStdio() error { return server.ServeStdio(s.mcp) }

func (s *Server) instrument(name string, h server.ToolHandlerFunc) server.ToolHandlerFunc {
	return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		identity := identityFrom(ctx)
		if s.limiter != nil && !s.limiter.Allow(identity) {
			s.rec.RateLimited.WithLabelValues(identity).Inc()
			return mcp.NewToolResultError(fmt.Sprintf("rate limit exceeded for %s", identity)), nil
		}

		start := time.Now()
		s.rec.ToolCalls.WithLabelValues(name).Inc()
		res, err := h(ctx, req)
		s.rec.ToolDuration.WithLabelValues(name).Observe(time.Since(start).Seconds())

		switch {
		case err != nil:
			s.rec.ToolErrors.WithLabelValues(name, "handler_error").Inc()
		case res != nil && res.IsError:
			s.rec.ToolErrors.WithLabelValues(name, "tool_error").Inc()
		}
		return res, err
	}
}

type identityKey struct{}

// WithIdentity stamps a caller identifier onto the context. Auth middleware
// should call this after verifying credentials.
func WithIdentity(ctx context.Context, id string) context.Context {
	if id == "" {
		return ctx
	}
	return context.WithValue(ctx, identityKey{}, id)
}

func identityFrom(ctx context.Context) string {
	if v, ok := ctx.Value(identityKey{}).(string); ok && v != "" {
		return v
	}
	return "anonymous"
}
