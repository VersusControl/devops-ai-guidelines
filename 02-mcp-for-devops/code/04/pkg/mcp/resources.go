package mcp

import (
	"context"
	"fmt"
	"kubernetes-mcp-server/pkg/types"
	"strings"

	"github.com/mark3labs/mcp-go/mcp"
)

// registerResources discovers and registers actual Kubernetes resources
func (s *Server) registerResources() {
	// For now, we'll register a few sample resources from common namespaces
	// In a production implementation, this could be made more dynamic

	ctx := context.Background()

	// Get some actual pods and register them
	pods, err := s.k8sClient.ListPods(ctx, "")
	if err != nil {
		s.logger.Errorf("Failed to list pods for registration: %v", err)
	} else {
		// Register first few pods as examples (limit to avoid too many resources)
		count := 0
		for _, pod := range pods {
			if count >= 5 { // Limit to first 5 pods
				break
			}
			resource := mcp.Resource{
				URI:         fmt.Sprintf("k8s://pod/%s/%s", pod.Namespace, pod.Name),
				Name:        fmt.Sprintf("Pod: %s/%s", pod.Namespace, pod.Name),
				Description: fmt.Sprintf("Kubernetes Pod in namespace %s (Status: %s)", pod.Namespace, pod.Status),
				MIMEType:    "application/json",
			}
			s.mcpServer.AddResource(resource, s.handleResourceRead)
			count++
		}
	}

	// Get some actual services and register them
	services, err := s.k8sClient.ListServices(ctx, "")
	if err != nil {
		s.logger.Errorf("Failed to list services for registration: %v", err)
	} else {
		// Register first few services as examples
		count := 0
		for _, service := range services {
			if count >= 5 { // Limit to first 5 services
				break
			}
			resource := mcp.Resource{
				URI:         fmt.Sprintf("k8s://service/%s/%s", service.Namespace, service.Name),
				Name:        fmt.Sprintf("Service: %s/%s", service.Namespace, service.Name),
				Description: fmt.Sprintf("Kubernetes Service in namespace %s (Type: %s)", service.Namespace, service.Type),
				MIMEType:    "application/json",
			}
			s.mcpServer.AddResource(resource, s.handleResourceRead)
			count++
		}
	}

	// Get some actual deployments and register them
	deployments, err := s.k8sClient.ListDeployments(ctx, "")
	if err != nil {
		s.logger.Errorf("Failed to list deployments for registration: %v", err)
	} else {
		// Register first few deployments as examples
		count := 0
		for _, deployment := range deployments {
			if count >= 5 { // Limit to first 5 deployments
				break
			}
			resource := mcp.Resource{
				URI:         fmt.Sprintf("k8s://deployment/%s/%s", deployment.Namespace, deployment.Name),
				Name:        fmt.Sprintf("Deployment: %s/%s", deployment.Namespace, deployment.Name),
				Description: fmt.Sprintf("Kubernetes Deployment in namespace %s (%d/%d replicas ready)", deployment.Namespace, deployment.ReadyReplicas, deployment.TotalReplicas),
				MIMEType:    "application/json",
			}
			s.mcpServer.AddResource(resource, s.handleResourceRead)
			count++
		}
	}
}

// handleResourceRead handles resource read requests
func (s *Server) handleResourceRead(ctx context.Context, request mcp.ReadResourceRequest) ([]mcp.ResourceContents, error) {
	uri := request.Params.URI
	s.logger.Infof("Handling read_resource request for URI: %s", uri)

	if !strings.HasPrefix(uri, "k8s://") {
		return nil, fmt.Errorf("invalid URI format. Expected k8s://<resource-type>/<namespace>/<name>, got: %s", uri)
	}

	// Parse URI: k8s://<resource-type>/<namespace>/<name>
	parts := strings.Split(strings.TrimPrefix(uri, "k8s://"), "/")
	if len(parts) != 3 {
		return nil, fmt.Errorf("invalid URI format. Expected k8s://<resource-type>/<namespace>/<name>, got %d parts", len(parts))
	}

	resourceType, namespace, name := parts[0], parts[1], parts[2]

	var resourceTypeEnum types.K8sResourceType
	switch resourceType {
	case "pod":
		resourceTypeEnum = types.ResourceTypePod
	case "service":
		resourceTypeEnum = types.ResourceTypeService
	case "deployment":
		resourceTypeEnum = types.ResourceTypeDeployment
	default:
		return nil, fmt.Errorf("unsupported resource type: %s. Supported types: pod, service, deployment", resourceType)
	}

	content, err := s.k8sClient.GetResource(ctx, &types.ResourceIdentifier{
		Type:      resourceTypeEnum,
		Namespace: namespace,
		Name:      name,
	})

	if err != nil {
		return nil, fmt.Errorf("failed to get resource %s: %w", uri, err)
	}

	// Format the content using AI-optimized formatters
	var formattedContent string
	var mimeType string

	switch resourceType {
	case "pod":
		formattedContent, err = s.formatter.FormatPodForAI(content)
		if err != nil {
			s.logger.Errorf("Failed to format pod data: %v", err)
			// Fall back to raw JSON
			formattedContent = content
			mimeType = "application/json"
		} else {
			mimeType = "text/markdown"
		}

	case "service":
		formattedContent, err = s.formatter.FormatServiceForAI(content)
		if err != nil {
			s.logger.Errorf("Failed to format service data: %v", err)
			// Fall back to raw JSON
			formattedContent = content
			mimeType = "application/json"
		} else {
			mimeType = "text/markdown"
		}

	case "deployment":
		formattedContent, err = s.formatter.FormatDeploymentForAI(content)
		if err != nil {
			s.logger.Errorf("Failed to format deployment data: %v", err)
			// Fall back to raw JSON
			formattedContent = content
			mimeType = "application/json"
		} else {
			mimeType = "text/markdown"
		}

	default:
		// For unsupported types, return raw JSON
		formattedContent = content
		mimeType = "application/json"
	}

	// Return the formatted resource contents
	return []mcp.ResourceContents{
		&mcp.TextResourceContents{
			URI:      uri,
			MIMEType: mimeType,
			Text:     formattedContent,
		},
	}, nil
}
