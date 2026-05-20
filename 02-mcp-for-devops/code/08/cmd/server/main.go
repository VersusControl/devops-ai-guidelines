package main

import (
	"context"
	"flag"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	mcpgo "github.com/mark3labs/mcp-go/mcp"

	perfmcp "k8s-mcp-perf/pkg/mcp"
	"k8s-mcp-perf/pkg/metrics"
	"k8s-mcp-perf/pkg/profiler"
	"k8s-mcp-perf/pkg/ratelimit"
)

func main() {
	metricsAddr := flag.String("metrics-addr", ":9090", "Prometheus metrics listen address")
	pprofAddr := flag.String("pprof-addr", "", "pprof listen address (empty = disabled)")
	rps := flag.Float64("ratelimit-rps", 50, "per-identity requests/second")
	burst := flag.Int("ratelimit-burst", 100, "per-identity burst")
	flag.Parse()

	rec := metrics.New("mcp")
	limiter := ratelimit.New(*rps, *burst, 10*time.Minute)

	srv := perfmcp.New("k8s-mcp-perf", "1.0.0", rec, limiter)

	// Example tool: echo back the request to exercise the middleware.
	srv.AddTool(
		mcpgo.NewTool("ping",
			mcpgo.WithDescription("Health check. Returns 'pong' with the caller identity."),
		),
		func(ctx context.Context, _ mcpgo.CallToolRequest) (*mcpgo.CallToolResult, error) {
			return mcpgo.NewToolResultText("pong"), nil
		},
	)

	// Metrics endpoint.
	mux := http.NewServeMux()
	mux.Handle("/metrics", metrics.Handler())
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
	})
	metricsSrv := &http.Server{
		Addr:              *metricsAddr,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
	}
	go func() {
		log.Printf("metrics listening on %s", *metricsAddr)
		if err := metricsSrv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Printf("metrics server: %v", err)
		}
	}()

	// pprof (optional).
	var prof *profiler.Server
	if *pprofAddr != "" {
		prof = profiler.New(*pprofAddr)
		prof.Start()
		log.Printf("pprof listening on %s", *pprofAddr)
	}

	// Graceful shutdown.
	ctx, cancel := context.WithCancel(context.Background())
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-sigCh
		log.Println("shutting down")
		shutdown, sc := context.WithTimeout(context.Background(), 5*time.Second)
		defer sc()
		_ = metricsSrv.Shutdown(shutdown)
		if prof != nil {
			_ = prof.Stop(shutdown)
		}
		cancel()
	}()

	if err := srv.ServeStdio(); err != nil {
		log.Printf("stdio: %v", err)
	}
	<-ctx.Done()
}
