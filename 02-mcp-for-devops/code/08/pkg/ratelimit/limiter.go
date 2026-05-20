// Package ratelimit provides a per-identity token-bucket limiter built on
// top of golang.org/x/time/rate. The limiter is sharded by identity (API
// key, JWT subject, IP, ...) so a noisy caller cannot starve others.
package ratelimit

import (
	"sync"
	"time"

	"golang.org/x/time/rate"
)

// Limiter is a sharded token-bucket limiter.
type Limiter struct {
	r       rate.Limit
	burst   int
	ttl     time.Duration
	mu      sync.Mutex
	buckets map[string]*entry
}

type entry struct {
	limiter  *rate.Limiter
	lastSeen time.Time
}

// New constructs a Limiter that refills at `rps` requests/second with
// `burst` tokens. Entries idle for longer than `ttl` are garbage-collected
// on the next Allow call.
func New(rps float64, burst int, ttl time.Duration) *Limiter {
	if ttl <= 0 {
		ttl = 10 * time.Minute
	}
	return &Limiter{
		r:       rate.Limit(rps),
		burst:   burst,
		ttl:     ttl,
		buckets: make(map[string]*entry),
	}
}

// Allow returns true when the caller is permitted to proceed.
func (l *Limiter) Allow(identity string) bool {
	now := time.Now()
	l.mu.Lock()
	defer l.mu.Unlock()

	b, ok := l.buckets[identity]
	if !ok {
		b = &entry{limiter: rate.NewLimiter(l.r, l.burst)}
		l.buckets[identity] = b
	}
	b.lastSeen = now

	// Occasional sweep — cheap because identity space is small.
	if len(l.buckets) > 256 {
		for k, v := range l.buckets {
			if now.Sub(v.lastSeen) > l.ttl {
				delete(l.buckets, k)
			}
		}
	}
	return b.limiter.Allow()
}
