package pagination

import (
	"context"
	"testing"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

func TestFetchAllWalksAllPages(t *testing.T) {
	pages := [][]int{{1, 2, 3}, {4, 5, 6}, {7}}
	idx := 0
	lister := func(_ context.Context, _ metav1.ListOptions) ([]int, string, error) {
		page := pages[idx]
		idx++
		next := ""
		if idx < len(pages) {
			next = "more"
		}
		return page, next, nil
	}
	got, err := FetchAll(context.Background(), Options{Limit: 3}, 0, lister)
	if err != nil {
		t.Fatal(err)
	}
	if len(got) != 7 {
		t.Fatalf("want 7 items got %d", len(got))
	}
}

func TestFetchAllRespectsMaxItems(t *testing.T) {
	lister := func(_ context.Context, _ metav1.ListOptions) ([]int, string, error) {
		return []int{1, 2, 3, 4, 5}, "more", nil
	}
	got, err := FetchAll(context.Background(), Options{Limit: 5}, 3, lister)
	if err != nil {
		t.Fatal(err)
	}
	if len(got) != 3 {
		t.Fatalf("want 3 items got %d", len(got))
	}
}
