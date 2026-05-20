package main

import (
	"context"
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"

	"k8s-mcp-advanced/pkg/mcp"
	"k8s-mcp-advanced/pkg/multicluster"
)

func main() {
	clusterFile := flag.String("clusters", "./configs/clusters.yaml", "cluster registry YAML")
	flag.Parse()

	mgr, err := multicluster.LoadFromFile(*clusterFile)
	if err != nil {
		log.Fatalf("load clusters: %v", err)
	}
	log.Printf("loaded %d clusters (default=%s)", len(mgr.Names()), mgr.Default())

	srv := mcp.NewServer(mgr)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-sigCh
		log.Println("shutting down")
		cancel()
	}()

	if err := srv.Serve(ctx); err != nil {
		log.Fatalf("serve: %v", err)
	}
}
