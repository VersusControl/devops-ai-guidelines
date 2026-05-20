.PHONY: build run bench load deps clean

BINARY=bin/k8s-mcp-perf

deps:
	go mod tidy

build:
	mkdir -p bin
	go build -o $(BINARY) ./cmd/server

run: build
	$(BINARY) --metrics-addr :9090 --pprof-addr :6060

bench:
	go test -bench=. -benchmem -run=^$$ ./...

load:
	@command -v hey >/dev/null || { echo "install hey: brew install hey" >&2; exit 1; }
	hey -n 5000 -c 50 -m POST http://localhost:9090/metrics

clean:
	rm -rf bin
