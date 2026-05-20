// Package watch exposes a thin wrapper around the client-go SharedInformer
// pattern. The Watcher fan-outs Kubernetes events to subscribers so the MCP
// layer can translate them into protocol notifications without blocking.
package watch

import (
	"context"
	"fmt"
	"sync"
	"time"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/informers"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/cache"
)

// EventType enumerates the lifecycle events surfaced to subscribers.
type EventType string

const (
	EventAdded    EventType = "added"
	EventModified EventType = "modified"
	EventDeleted  EventType = "deleted"
)

// Event is the high-level event handed to subscribers.
type Event struct {
	Type      EventType
	Kind      string
	Namespace string
	Name      string
	Object    any
	Timestamp time.Time
}

// Subscriber receives events. Implementations must be non-blocking.
type Subscriber func(Event)

// Watcher owns a SharedInformerFactory and a list of subscribers.
type Watcher struct {
	clientset kubernetes.Interface
	factory   informers.SharedInformerFactory
	resync    time.Duration

	mu          sync.RWMutex
	subscribers []Subscriber

	stopCh chan struct{}
	once   sync.Once
}

// New constructs a Watcher with the given resync period (use 0 to disable).
func New(clientset kubernetes.Interface, resync time.Duration) *Watcher {
	return &Watcher{
		clientset: clientset,
		factory:   informers.NewSharedInformerFactory(clientset, resync),
		resync:    resync,
		stopCh:    make(chan struct{}),
	}
}

// Subscribe registers a callback. The returned function unsubscribes.
func (w *Watcher) Subscribe(fn Subscriber) func() {
	w.mu.Lock()
	defer w.mu.Unlock()
	w.subscribers = append(w.subscribers, fn)
	idx := len(w.subscribers) - 1
	return func() {
		w.mu.Lock()
		defer w.mu.Unlock()
		w.subscribers[idx] = nil
	}
}

// Start wires informers for the supplied kinds and blocks until ctx is done.
//
// Supported kinds: "pods", "deployments", "services", "events".
func (w *Watcher) Start(ctx context.Context, kinds []string) error {
	for _, kind := range kinds {
		if err := w.attach(kind); err != nil {
			return fmt.Errorf("attach %q: %w", kind, err)
		}
	}

	w.factory.Start(w.stopCh)
	w.factory.WaitForCacheSync(w.stopCh)

	<-ctx.Done()
	w.once.Do(func() { close(w.stopCh) })
	return nil
}

func (w *Watcher) attach(kind string) error {
	var informer cache.SharedIndexInformer

	switch kind {
	case "pods":
		informer = w.factory.Core().V1().Pods().Informer()
	case "deployments":
		informer = w.factory.Apps().V1().Deployments().Informer()
	case "services":
		informer = w.factory.Core().V1().Services().Informer()
	case "events":
		informer = w.factory.Core().V1().Events().Informer()
	default:
		return fmt.Errorf("unsupported kind %q", kind)
	}

	_, err := informer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    func(obj any) { w.publish(EventAdded, kind, obj) },
		UpdateFunc: func(_, obj any) { w.publish(EventModified, kind, obj) },
		DeleteFunc: func(obj any) { w.publish(EventDeleted, kind, obj) },
	})
	return err
}

func (w *Watcher) publish(t EventType, kind string, obj any) {
	meta, ok := metaOf(obj)
	if !ok {
		return
	}
	ev := Event{
		Type:      t,
		Kind:      kind,
		Namespace: meta.Namespace,
		Name:      meta.Name,
		Object:    obj,
		Timestamp: time.Now(),
	}

	w.mu.RLock()
	subs := append([]Subscriber(nil), w.subscribers...)
	w.mu.RUnlock()

	for _, fn := range subs {
		if fn != nil {
			fn(ev)
		}
	}
}

func metaOf(obj any) (metav1.ObjectMeta, bool) {
	switch v := obj.(type) {
	case *corev1.Pod:
		return v.ObjectMeta, true
	case *corev1.Service:
		return v.ObjectMeta, true
	case *corev1.Event:
		return v.ObjectMeta, true
	default:
		if accessor, ok := obj.(metav1.Object); ok {
			return metav1.ObjectMeta{
				Name:      accessor.GetName(),
				Namespace: accessor.GetNamespace(),
			}, true
		}
	}
	return metav1.ObjectMeta{}, false
}
