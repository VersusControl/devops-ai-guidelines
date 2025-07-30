.PHONY: build test clean run docker

# Go parameters
GOCMD=go
GOBUILD=$(GOCMD) build
GOCLEAN=$(GOCMD) clean
GOTEST=$(GOCMD) test
GOGET=$(GOCMD) get
GOMOD=$(GOCMD) mod
BINARY_NAME=k8s-mcp-server
BINARY_PATH=./bin/$(BINARY_NAME)

# Build the application
build:
	mkdir -p bin
	$(GOBUILD) -o $(BINARY_PATH) -v ./cmd/server

# Run tests
test:
	$(GOTEST) -v ./...

# Run integration tests
test-integration:
	$(GOTEST) -v ./test/...

# Clean build artifacts
clean:
	$(GOCLEAN)
	rm -f $(BINARY_PATH)

# Run the application
run: build
	$(BINARY_PATH)

# Download dependencies
deps:
	$(GOMOD) download
	$(GOMOD) tidy

# Build Docker image
docker:
	docker build -t k8s-mcp-server:latest .

# Development setup
dev-setup:
	$(GOGET) github.com/stretchr/testify/assert
	$(GOGET) github.com/stretchr/testify/mock
	$(GOGET) github.com/stretchr/testify/require

# Lint code
lint:
	golangci-lint run

# Format code
fmt:
	$(GOCMD) fmt ./...

# Quick development test
dev-test: build
	@echo "Testing MCP server demo..."
	$(BINARY_PATH)

help:
	@echo "Available targets:"
	@echo "  build           - Build the application"
	@echo "  test            - Run unit tests"
	@echo "  test-integration- Run integration tests"
	@echo "  clean           - Clean build artifacts"
	@echo "  run             - Build and run the application"
	@echo "  deps            - Download dependencies"
	@echo "  docker          - Build Docker image"
	@echo "  dev-setup       - Setup development dependencies"
	@echo "  lint            - Run linter"
	@echo "  fmt             - Format code"
	@echo "  dev-test        - Quick development test"
