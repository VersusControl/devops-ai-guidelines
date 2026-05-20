package ratelimit

import (
	"strconv"
	"testing"
	"time"
)

func BenchmarkLimiterAllow(b *testing.B) {
	l := New(10000, 100, time.Minute)
	keys := make([]string, 64)
	for i := range keys {
		keys[i] = "user-" + strconv.Itoa(i)
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		l.Allow(keys[i%len(keys)])
	}
}

func TestLimiterRejectsBurst(t *testing.T) {
	// Very low refill rate so the test is not flaky. Burst=2 grants
	// exactly two immediate calls before the bucket drains.
	l := New(0.01, 2, time.Minute)
	if !l.Allow("u") {
		t.Fatal("first call should succeed")
	}
	if !l.Allow("u") {
		t.Fatal("second call should succeed (burst=2)")
	}
	if l.Allow("u") {
		t.Fatal("third call should be rejected")
	}
}
