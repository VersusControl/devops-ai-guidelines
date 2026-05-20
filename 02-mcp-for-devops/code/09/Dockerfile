# syntax=docker/dockerfile:1.7
# Multi-stage build producing a distroless image suitable for production.

ARG GO_VERSION=1.23
ARG SOURCE_DIR=../08

FROM golang:${GO_VERSION}-bookworm AS builder
WORKDIR /src
COPY ${SOURCE_DIR}/go.mod ${SOURCE_DIR}/go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download
COPY ${SOURCE_DIR}/ ./
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath -ldflags "-s -w" -o /out/k8s-mcp-server ./cmd/server

FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app
COPY --from=builder /out/k8s-mcp-server /app/k8s-mcp-server
USER nonroot:nonroot
EXPOSE 9090 6060
ENTRYPOINT ["/app/k8s-mcp-server"]
CMD ["--metrics-addr=:9090"]
