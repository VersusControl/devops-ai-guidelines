// Package profiler exposes net/http/pprof on a private mux so the operator
// can opt into runtime profiling without affecting the MCP transport.
package profiler

import (
	"context"
	"net/http"
	"net/http/pprof"
	"time"
)

// Server is a stoppable pprof HTTP server.
type Server struct {
	srv *http.Server
}

// New constructs the Server bound to `addr` (e.g. ":6060"). Call Start to
// begin serving.
func New(addr string) *Server {
	mux := http.NewServeMux()
	mux.HandleFunc("/debug/pprof/", pprof.Index)
	mux.HandleFunc("/debug/pprof/cmdline", pprof.Cmdline)
	mux.HandleFunc("/debug/pprof/profile", pprof.Profile)
	mux.HandleFunc("/debug/pprof/symbol", pprof.Symbol)
	mux.HandleFunc("/debug/pprof/trace", pprof.Trace)

	return &Server{
		srv: &http.Server{
			Addr:              addr,
			Handler:           mux,
			ReadHeaderTimeout: 5 * time.Second,
		},
	}
}

// Start runs ListenAndServe in a goroutine.
func (s *Server) Start() {
	go func() {
		_ = s.srv.ListenAndServe()
	}()
}

// Stop gracefully shuts the server down.
func (s *Server) Stop(ctx context.Context) error {
	return s.srv.Shutdown(ctx)
}
