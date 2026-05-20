// Package metrics centralises Prometheus instrumentation used across the
// MCP server. All metrics live on the default registry so the operator only
// needs to expose `/metrics` once.
package metrics

import (
	"net/http"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

// Recorder owns the metric families.
type Recorder struct {
	ToolCalls    *prometheus.CounterVec
	ToolErrors   *prometheus.CounterVec
	ToolDuration *prometheus.HistogramVec
	K8sCalls     *prometheus.CounterVec
	K8sDuration  *prometheus.HistogramVec
	CacheHits    *prometheus.CounterVec
	RateLimited  *prometheus.CounterVec
}

// New constructs and registers a Recorder.
func New(namespace string) *Recorder {
	return &Recorder{
		ToolCalls: promauto.NewCounterVec(prometheus.CounterOpts{
			Namespace: namespace, Subsystem: "tool", Name: "calls_total",
			Help: "Total MCP tool invocations.",
		}, []string{"tool"}),
		ToolErrors: promauto.NewCounterVec(prometheus.CounterOpts{
			Namespace: namespace, Subsystem: "tool", Name: "errors_total",
			Help: "Tool invocations that returned an error.",
		}, []string{"tool", "reason"}),
		ToolDuration: promauto.NewHistogramVec(prometheus.HistogramOpts{
			Namespace: namespace, Subsystem: "tool", Name: "duration_seconds",
			Help:    "Latency of MCP tool calls.",
			Buckets: prometheus.ExponentialBuckets(0.005, 2, 12),
		}, []string{"tool"}),
		K8sCalls: promauto.NewCounterVec(prometheus.CounterOpts{
			Namespace: namespace, Subsystem: "k8s", Name: "calls_total",
			Help: "Kubernetes API calls issued by the server.",
		}, []string{"verb", "resource"}),
		K8sDuration: promauto.NewHistogramVec(prometheus.HistogramOpts{
			Namespace: namespace, Subsystem: "k8s", Name: "duration_seconds",
			Help:    "Latency of Kubernetes API calls.",
			Buckets: prometheus.ExponentialBuckets(0.001, 2, 14),
		}, []string{"verb", "resource"}),
		CacheHits: promauto.NewCounterVec(prometheus.CounterOpts{
			Namespace: namespace, Subsystem: "cache", Name: "events_total",
			Help: "Cache hit/miss counter.",
		}, []string{"outcome"}),
		RateLimited: promauto.NewCounterVec(prometheus.CounterOpts{
			Namespace: namespace, Subsystem: "ratelimit", Name: "rejected_total",
			Help: "Requests rejected by the rate limiter.",
		}, []string{"identity"}),
	}
}

// Handler returns the Prometheus exposition HTTP handler.
func Handler() http.Handler {
	return promhttp.Handler()
}
