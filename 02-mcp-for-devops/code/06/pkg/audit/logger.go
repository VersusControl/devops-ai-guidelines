package audit

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/sirupsen/logrus"
)

type AuditEvent struct {
	Timestamp    time.Time              `json:"timestamp"`
	EventID      string                 `json:"event_id"`
	EventType    string                 `json:"event_type"`
	User         string                 `json:"user"`
	Action       string                 `json:"action"`
	Resource     string                 `json:"resource"`
	Namespace    string                 `json:"namespace,omitempty"`
	Result       string                 `json:"result"` // "success", "failure", "error"
	ErrorMessage string                 `json:"error_message,omitempty"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
	Duration     time.Duration          `json:"duration_ms"`
}

type AuditLogger struct {
	logger *logrus.Logger
}

func NewAuditLogger(logger *logrus.Logger) *AuditLogger {
	return &AuditLogger{
		logger: logger,
	}
}

func (a *AuditLogger) LogEvent(ctx context.Context, event *AuditEvent) {
	// Set timestamp if not provided
	if event.Timestamp.IsZero() {
		event.Timestamp = time.Now()
	}

	// Generate event ID if not provided
	if event.EventID == "" {
		event.EventID = generateEventID()
	}

	// Log as structured JSON for easy parsing
	eventJSON, err := json.Marshal(event)
	if err != nil {
		a.logger.WithError(err).Error("Failed to marshal audit event")
		return
	}

	// Use structured logging with audit-specific fields
	a.logger.WithFields(logrus.Fields{
		"audit":      true,
		"event_type": event.EventType,
		"user":       event.User,
		"action":     event.Action,
		"result":     event.Result,
		"duration":   event.Duration.Milliseconds(),
	}).Info(string(eventJSON))
}

func (a *AuditLogger) LogMCPRequest(ctx context.Context, user, action, resource, namespace string, startTime time.Time, err error) {
	result := "success"
	errorMessage := ""

	if err != nil {
		result = "failure"
		errorMessage = err.Error()
	}

	event := &AuditEvent{
		EventType:    "mcp_request",
		User:         user,
		Action:       action,
		Resource:     resource,
		Namespace:    namespace,
		Result:       result,
		ErrorMessage: errorMessage,
		Duration:     time.Since(startTime),
		Metadata: map[string]interface{}{
			"protocol": "mcp",
			"version":  "1.0",
		},
	}

	a.LogEvent(ctx, event)
}

func (a *AuditLogger) LogAuthentication(ctx context.Context, user, authType string, success bool, errorMessage string) {
	result := "success"
	if !success {
		result = "failure"
	}

	event := &AuditEvent{
		EventType:    "authentication",
		User:         user,
		Action:       "authenticate",
		Result:       result,
		ErrorMessage: errorMessage,
		Metadata: map[string]interface{}{
			"auth_type": authType,
		},
	}

	a.LogEvent(ctx, event)
}

func (a *AuditLogger) LogAuthorization(ctx context.Context, user, action, resource, namespace string, granted bool) {
	result := "granted"
	if !granted {
		result = "denied"
	}

	event := &AuditEvent{
		EventType: "authorization",
		User:      user,
		Action:    action,
		Resource:  resource,
		Namespace: namespace,
		Result:    result,
		Metadata: map[string]interface{}{
			"permission_check": true,
		},
	}

	a.LogEvent(ctx, event)
}

func generateEventID() string {
	// Simple event ID generation - in production, use UUID
	return fmt.Sprintf("evt_%d", time.Now().UnixNano())
}
