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

# Quick MCP test
mcp-test: build
	@echo "Testing MCP initialization..."
	@echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"resources":{}},"clientInfo":{"name":"test","version":"1.0.0"}}}' | $(BINARY_PATH)

# List resources test
list-test: build
	@echo "Testing resource listing..."
	@echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"resources":{}},"clientInfo":{"name":"test","version":"1.0.0"}}}' | $(BINARY_PATH) && \
	echo '{"jsonrpc":"2.0","id":2,"method":"resources/list","params":{}}' | $(BINARY_PATH)

help:
	@echo "Available targets:"
	@echo "  build     - Build the application"
	@echo "  test      - Run unit tests"
	@echo "  clean     - Clean build artifacts"
	@echo "  run       - Build and run the application"
	@echo "  deps      - Download dependencies"
	@echo "  mcp-test  - Quick MCP protocol test"
	@echo "  list-test - Test resource listing"
