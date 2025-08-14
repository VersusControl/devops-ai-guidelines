package auth

import (
	"context"
	"fmt"
)

type AuthInfo struct {
	Type        string                 `json:"type"`
	Identity    string                 `json:"identity"`
	Permissions []string               `json:"permissions"`
	Metadata    map[string]interface{} `json:"metadata"`
}

type Authenticator interface {
	Authenticate(ctx context.Context, credentials string) (*AuthInfo, error)
}

type MultiAuthenticator struct {
	authenticators map[string]Authenticator
}

func NewMultiAuthenticator() *MultiAuthenticator {
	return &MultiAuthenticator{
		authenticators: make(map[string]Authenticator),
	}
}

func (m *MultiAuthenticator) AddAuthenticator(name string, auth Authenticator) {
	m.authenticators[name] = auth
}

func (m *MultiAuthenticator) Authenticate(ctx context.Context, authType, credentials string) (*AuthInfo, error) {
	authenticator, exists := m.authenticators[authType]
	if !exists {
		return nil, fmt.Errorf("unsupported authentication type: %s", authType)
	}

	return authenticator.Authenticate(ctx, credentials)
}
