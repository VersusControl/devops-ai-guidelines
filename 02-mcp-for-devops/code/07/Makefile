.PHONY: build run deps clean

BINARY=bin/k8s-mcp-advanced

deps:
	go mod tidy

build:
	mkdir -p bin
	go build -o $(BINARY) ./cmd/server

run: build
	$(BINARY) --clusters ./configs/clusters.yaml

clean:
	rm -rf bin
