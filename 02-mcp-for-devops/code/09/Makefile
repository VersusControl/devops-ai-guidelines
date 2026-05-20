.PHONY: image push deploy lint test render

IMAGE ?= ghcr.io/devops-ai-guidelines/k8s-mcp-server
TAG   ?= dev
NAMESPACE ?= mcp

image:
	docker build -f Dockerfile -t $(IMAGE):$(TAG) ../

push:
	docker push $(IMAGE):$(TAG)

deploy:
	helm upgrade --install k8s-mcp deploy/helm/k8s-mcp-server \
		--namespace $(NAMESPACE) --create-namespace \
		--set image.repository=$(IMAGE) --set image.tag=$(TAG)

render:
	helm template k8s-mcp deploy/helm/k8s-mcp-server \
		--set image.repository=$(IMAGE) --set image.tag=$(TAG)

lint:
	helm lint deploy/helm/k8s-mcp-server
	kustomize build deploy/kustomize/overlays/prod >/dev/null

test:
	cd ../08 && go test ./...
