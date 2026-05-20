// Package cache provides a small TTL + LRU store used to memoise expensive
// Kubernetes API calls. It is intentionally dependency-free so it can be
// dropped into any of the chapter modules.
package cache

import (
	"container/list"
	"sync"
	"time"
)

// Store is a thread-safe TTL+LRU cache keyed by string.
type Store struct {
	mu      sync.Mutex
	maxSize int
	ttl     time.Duration
	items   map[string]*list.Element
	lru     *list.List
	now     func() time.Time
}

type entry struct {
	key       string
	value     any
	expiresAt time.Time
}

// New constructs a Store with the supplied max size and TTL.
func New(maxSize int, ttl time.Duration) *Store {
	if maxSize <= 0 {
		maxSize = 1024
	}
	return &Store{
		maxSize: maxSize,
		ttl:     ttl,
		items:   make(map[string]*list.Element, maxSize),
		lru:     list.New(),
		now:     time.Now,
	}
}

// Get returns the cached value and true if present and unexpired.
func (s *Store) Get(key string) (any, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()

	elem, ok := s.items[key]
	if !ok {
		return nil, false
	}
	e := elem.Value.(*entry)
	if s.now().After(e.expiresAt) {
		s.removeLocked(elem)
		return nil, false
	}
	s.lru.MoveToFront(elem)
	return e.value, true
}

// Set inserts or refreshes a value, evicting the LRU entry when full.
func (s *Store) Set(key string, value any) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if elem, ok := s.items[key]; ok {
		e := elem.Value.(*entry)
		e.value = value
		e.expiresAt = s.now().Add(s.ttl)
		s.lru.MoveToFront(elem)
		return
	}

	e := &entry{key: key, value: value, expiresAt: s.now().Add(s.ttl)}
	elem := s.lru.PushFront(e)
	s.items[key] = elem

	if s.lru.Len() > s.maxSize {
		s.removeLocked(s.lru.Back())
	}
}

// Invalidate drops a single key.
func (s *Store) Invalidate(key string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if elem, ok := s.items[key]; ok {
		s.removeLocked(elem)
	}
}

// Len returns the current number of live entries.
func (s *Store) Len() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.lru.Len()
}

func (s *Store) removeLocked(elem *list.Element) {
	e := elem.Value.(*entry)
	delete(s.items, e.key)
	s.lru.Remove(elem)
}
