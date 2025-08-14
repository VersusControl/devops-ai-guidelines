package auth

import (
	"context"
	"crypto/subtle"
	"fmt"
	"time"

	"github.com/sirupsen/logrus"
)

type APIKeyStore interface {
	ValidateAPIKey(ctx context.Context, key string) (*APIKeyInfo, error)
	RevokeAPIKey(ctx context.Context, keyID string) error
}

type APIKeyInfo struct {
	ID          string     `json:"id"`
	Name        string     `json:"name"`
	Permissions []string   `json:"permissions"`
	CreatedAt   time.Time  `json:"created_at"`
	ExpiresAt   *time.Time `json:"expires_at,omitempty"`
	LastUsed    *time.Time `json:"last_used,omitempty"`
}

type InMemoryAPIKeyStore struct {
	keys   map[string]*APIKeyInfo
	logger *logrus.Logger
}

func NewInMemoryAPIKeyStore(logger *logrus.Logger) *InMemoryAPIKeyStore {
	return &InMemoryAPIKeyStore{
		keys:   make(map[string]*APIKeyInfo),
		logger: logger,
	}
}

func (s *InMemoryAPIKeyStore) AddAPIKey(key string, info *APIKeyInfo) {
	s.keys[key] = info
}

func (s *InMemoryAPIKeyStore) ValidateAPIKey(ctx context.Context, key string) (*APIKeyInfo, error) {
	// Use constant-time comparison to prevent timing attacks
	var found *APIKeyInfo
	for storedKey, info := range s.keys {
		if subtle.ConstantTimeCompare([]byte(key), []byte(storedKey)) == 1 {
			found = info
			break
		}
	}

	if found == nil {
		s.logger.WithField("key_prefix", maskAPIKey(key)).Warn("Invalid API key attempted")
		return nil, fmt.Errorf("invalid API key")
	}

	// Check expiration
	if found.ExpiresAt != nil && time.Now().After(*found.ExpiresAt) {
		s.logger.WithField("key_id", found.ID).Warn("Expired API key attempted")
		return nil, fmt.Errorf("API key expired")
	}

	// Update last used time
	now := time.Now()
	found.LastUsed = &now

	s.logger.WithFields(logrus.Fields{
		"key_id":   found.ID,
		"key_name": found.Name,
	}).Info("API key authenticated successfully")

	return found, nil
}

func (s *InMemoryAPIKeyStore) RevokeAPIKey(ctx context.Context, keyID string) error {
	for key, info := range s.keys {
		if info.ID == keyID {
			delete(s.keys, key)
			s.logger.WithField("key_id", keyID).Info("API key revoked")
			return nil
		}
	}
	return fmt.Errorf("API key not found: %s", keyID)
}

// maskAPIKey shows only the first 8 characters for logging
func maskAPIKey(key string) string {
	if len(key) <= 8 {
		return "****"
	}
	return key[:8] + "****"
}

type APIKeyAuthenticator struct {
	store  APIKeyStore
	logger *logrus.Logger
}

func NewAPIKeyAuthenticator(store APIKeyStore, logger *logrus.Logger) *APIKeyAuthenticator {
	return &APIKeyAuthenticator{
		store:  store,
		logger: logger,
	}
}

func (a *APIKeyAuthenticator) Authenticate(ctx context.Context, credentials string) (*AuthInfo, error) {
	keyInfo, err := a.store.ValidateAPIKey(ctx, credentials)
	if err != nil {
		return nil, err
	}

	return &AuthInfo{
		Type:        "api_key",
		Identity:    keyInfo.Name,
		Permissions: keyInfo.Permissions,
		Metadata: map[string]interface{}{
			"key_id":    keyInfo.ID,
			"last_used": keyInfo.LastUsed,
		},
	}, nil
}
