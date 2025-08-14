package auth

import (
	"context"
	"fmt"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/sirupsen/logrus"
)

type JWTClaims struct {
	UserID      string   `json:"user_id"`
	Username    string   `json:"username"`
	Permissions []string `json:"permissions"`
	jwt.RegisteredClaims
}

type JWTAuthenticator struct {
	secretKey []byte
	logger    *logrus.Logger
}

func NewJWTAuthenticator(secretKey []byte, logger *logrus.Logger) *JWTAuthenticator {
	return &JWTAuthenticator{
		secretKey: secretKey,
		logger:    logger,
	}
}

func (a *JWTAuthenticator) Authenticate(ctx context.Context, tokenString string) (*AuthInfo, error) {
	token, err := jwt.ParseWithClaims(tokenString, &JWTClaims{}, func(token *jwt.Token) (interface{}, error) {
		// Verify the signing method
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return a.secretKey, nil
	})

	if err != nil {
		a.logger.WithError(err).Warn("JWT token validation failed")
		return nil, fmt.Errorf("invalid token: %w", err)
	}

	claims, ok := token.Claims.(*JWTClaims)
	if !ok || !token.Valid {
		a.logger.Warn("Invalid JWT token claims")
		return nil, fmt.Errorf("invalid token claims")
	}

	// Additional validation
	if time.Now().After(claims.ExpiresAt.Time) {
		a.logger.WithField("username", claims.Username).Warn("Expired JWT token attempted")
		return nil, fmt.Errorf("token expired")
	}

	a.logger.WithFields(logrus.Fields{
		"user_id":  claims.UserID,
		"username": claims.Username,
	}).Info("JWT authentication successful")

	return &AuthInfo{
		Type:        "jwt",
		Identity:    claims.Username,
		Permissions: claims.Permissions,
		Metadata: map[string]interface{}{
			"user_id":    claims.UserID,
			"expires_at": claims.ExpiresAt.Time,
		},
	}, nil
}

func (a *JWTAuthenticator) GenerateToken(userID, username string, permissions []string, expiresIn time.Duration) (string, error) {
	claims := &JWTClaims{
		UserID:      userID,
		Username:    username,
		Permissions: permissions,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(expiresIn)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			NotBefore: jwt.NewNumericDate(time.Now()),
			Issuer:    "k8s-mcp-server",
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString(a.secretKey)
}
