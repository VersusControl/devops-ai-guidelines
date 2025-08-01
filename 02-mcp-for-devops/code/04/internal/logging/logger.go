package logging

import (
	"os"
	"time"

	"github.com/sirupsen/logrus"
)

type Logger struct {
	*logrus.Logger
}

func NewLogger(level, format string) *Logger {
	logger := logrus.New()

	// Set log level
	logLevel, err := logrus.ParseLevel(level)
	if err != nil {
		logLevel = logrus.InfoLevel
	}
	logger.SetLevel(logLevel)

	// Set formatter
	if format == "json" {
		logger.SetFormatter(&logrus.JSONFormatter{
			TimestampFormat: time.RFC3339,
		})
	} else {
		logger.SetFormatter(&logrus.TextFormatter{
			FullTimestamp:   true,
			TimestampFormat: time.RFC3339,
		})
	}

	logger.SetOutput(os.Stdout)

	return &Logger{Logger: logger}
}

// LogMCPRequest logs MCP requests with context
func (l *Logger) LogMCPRequest(method, uri string, params interface{}) {
	l.WithFields(logrus.Fields{
		"component": "mcp",
		"method":    method,
		"uri":       uri,
		"params":    params,
	}).Info("Processing MCP request")
}

// LogMCPResponse logs MCP responses with timing
func (l *Logger) LogMCPResponse(method string, duration time.Duration, err error) {
	fields := logrus.Fields{
		"component": "mcp",
		"method":    method,
		"duration":  duration.String(),
	}

	if err != nil {
		l.WithFields(fields).WithError(err).Error("MCP request failed")
	} else {
		l.WithFields(fields).Info("MCP request completed")
	}
}

// LogK8sOperation logs Kubernetes operations
func (l *Logger) LogK8sOperation(operation, namespace, resource string, duration time.Duration, err error) {
	fields := logrus.Fields{
		"component": "kubernetes",
		"operation": operation,
		"namespace": namespace,
		"resource":  resource,
		"duration":  duration.String(),
	}

	if err != nil {
		l.WithFields(fields).WithError(err).Error("Kubernetes operation failed")
	} else {
		l.WithFields(fields).Debug("Kubernetes operation completed")
	}
}
