// Package pagination converts MCP tool arguments into Kubernetes
// ListOptions and back-paginates large result sets transparently.
package pagination

import (
	"context"
	"encoding/base64"
	"errors"
	"fmt"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// Options describes how a caller wants to slice a list.
type Options struct {
	Limit         int64
	ContinueToken string
	LabelSelector string
	FieldSelector string
}

// Page is one chunk of results with the cursor for the next page.
type Page[T any] struct {
	Items         []T
	NextToken     string
	TotalReturned int
}

// Lister calls the Kubernetes API to return a single page.
type Lister[T any] func(ctx context.Context, opts metav1.ListOptions) ([]T, string, error)

// Fetch returns one page using the supplied Lister.
func Fetch[T any](ctx context.Context, opts Options, lister Lister[T]) (Page[T], error) {
	if opts.Limit <= 0 || opts.Limit > 500 {
		opts.Limit = 100
	}
	lo := metav1.ListOptions{
		Limit:         opts.Limit,
		Continue:      opts.ContinueToken,
		LabelSelector: opts.LabelSelector,
		FieldSelector: opts.FieldSelector,
	}
	items, next, err := lister(ctx, lo)
	if err != nil {
		return Page[T]{}, err
	}
	return Page[T]{Items: items, NextToken: next, TotalReturned: len(items)}, nil
}

// FetchAll walks every page up to maxItems. Pass maxItems<=0 for unbounded.
func FetchAll[T any](ctx context.Context, opts Options, maxItems int, lister Lister[T]) ([]T, error) {
	var out []T
	for {
		page, err := Fetch(ctx, opts, lister)
		if err != nil {
			return nil, err
		}
		out = append(out, page.Items...)
		if maxItems > 0 && len(out) >= maxItems {
			return out[:maxItems], nil
		}
		if page.NextToken == "" {
			return out, nil
		}
		opts.ContinueToken = page.NextToken
	}
}

// EncodeCursor wraps an opaque continue token for safe transport over JSON.
// The Kubernetes API already returns base64-ish strings, but downstream
// consumers may apply their own escaping, so we re-encode for safety.
func EncodeCursor(token string) string {
	if token == "" {
		return ""
	}
	return base64.StdEncoding.EncodeToString([]byte(token))
}

// DecodeCursor is the inverse of EncodeCursor.
func DecodeCursor(cursor string) (string, error) {
	if cursor == "" {
		return "", nil
	}
	b, err := base64.StdEncoding.DecodeString(cursor)
	if err != nil {
		return "", fmt.Errorf("decode cursor: %w", err)
	}
	return string(b), nil
}

// ErrInvalidPageSize is returned when the requested page size is negative.
var ErrInvalidPageSize = errors.New("page size must be >= 0")
