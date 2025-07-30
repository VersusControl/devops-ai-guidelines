package k8s

import (
	"context"
	"encoding/json"
	"fmt"
	"path/filepath"

	"github.com/sirupsen/logrus"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/homedir"

	"kubernetes-mcp-server/pkg/types"
)

type Client struct {
	clientset *kubernetes.Clientset
	logger    *logrus.Logger
}

func NewClient(configPath string, logger *logrus.Logger) (*Client, error) {
	config, err := buildConfig(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to build kubernetes config: %w", err)
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create kubernetes client: %w", err)
	}

	return &Client{
		clientset: clientset,
		logger:    logger,
	}, nil
}

func buildConfig(configPath string) (*rest.Config, error) {
	// Try in-cluster config first
	if config, err := rest.InClusterConfig(); err == nil {
		return config, nil
	}

	// Fall back to kubeconfig
	if configPath == "" {
		if home := homedir.HomeDir(); home != "" {
			configPath = filepath.Join(home, ".kube", "config")
		}
	}

	return clientcmd.BuildConfigFromFlags("", configPath)
}

func (c *Client) HealthCheck(ctx context.Context) error {
	_, err := c.clientset.Discovery().ServerVersion()
	if err != nil {
		return fmt.Errorf("kubernetes cluster not reachable: %w", err)
	}
	return nil
}

func (c *Client) GetClusterInfo(ctx context.Context) (map[string]interface{}, error) {
	version, err := c.clientset.Discovery().ServerVersion()
	if err != nil {
		return nil, fmt.Errorf("failed to get server version: %w", err)
	}

	info := map[string]interface{}{
		"serverVersion": version.String(),
		"platform":      version.Platform,
		"buildDate":     version.BuildDate,
	}

	return info, nil
}

func (c *Client) ListPods(ctx context.Context, namespace string) ([]PodInfo, error) {
	pods, err := c.clientset.CoreV1().Pods(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to list pods in namespace %s: %w", namespace, err)
	}

	var podInfos []PodInfo
	for _, pod := range pods.Items {
		podInfo := PodInfo{
			Name:      pod.Name,
			Namespace: pod.Namespace,
			Status:    string(pod.Status.Phase),
			Phase:     string(pod.Status.Phase),
			Node:      pod.Spec.NodeName,
			Labels:    pod.Labels,
			CreatedAt: pod.CreationTimestamp.Time,
			Restarts:  getTotalRestarts(&pod),
		}
		podInfos = append(podInfos, podInfo)
	}

	return podInfos, nil
}

func (c *Client) ListServices(ctx context.Context, namespace string) ([]ServiceInfo, error) {
	services, err := c.clientset.CoreV1().Services(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to list services in namespace %s: %w", namespace, err)
	}

	var serviceInfos []ServiceInfo
	for _, svc := range services.Items {
		var ports []ServicePort
		for _, port := range svc.Spec.Ports {
			ports = append(ports, ServicePort{
				Name:       port.Name,
				Port:       port.Port,
				TargetPort: port.TargetPort.String(),
				Protocol:   string(port.Protocol),
			})
		}

		serviceInfo := ServiceInfo{
			Name:      svc.Name,
			Namespace: svc.Namespace,
			Type:      string(svc.Spec.Type),
			ClusterIP: svc.Spec.ClusterIP,
			Ports:     ports,
			Labels:    svc.Labels,
			CreatedAt: svc.CreationTimestamp.Time,
		}
		serviceInfos = append(serviceInfos, serviceInfo)
	}

	return serviceInfos, nil
}

func (c *Client) ListDeployments(ctx context.Context, namespace string) ([]DeploymentInfo, error) {
	deployments, err := c.clientset.AppsV1().Deployments(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to list deployments in namespace %s: %w", namespace, err)
	}

	var deploymentInfos []DeploymentInfo
	for _, deploy := range deployments.Items {
		strategy := "RollingUpdate"
		if deploy.Spec.Strategy.Type == appsv1.RecreateDeploymentStrategyType {
			strategy = "Recreate"
		}

		deploymentInfo := DeploymentInfo{
			Name:            deploy.Name,
			Namespace:       deploy.Namespace,
			TotalReplicas:   *deploy.Spec.Replicas,
			ReadyReplicas:   deploy.Status.ReadyReplicas,
			UpdatedReplicas: deploy.Status.UpdatedReplicas,
			Labels:          deploy.Labels,
			CreatedAt:       deploy.CreationTimestamp.Time,
			Strategy:        strategy,
		}
		deploymentInfos = append(deploymentInfos, deploymentInfo)
	}

	return deploymentInfos, nil
}

func (c *Client) ListConfigMaps(ctx context.Context, namespace string) ([]ConfigMapInfo, error) {
	configmaps, err := c.clientset.CoreV1().ConfigMaps(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to list configmaps in namespace %s: %w", namespace, err)
	}

	var configmapInfos []ConfigMapInfo
	for _, cm := range configmaps.Items {
		configmapInfo := ConfigMapInfo{
			Name:      cm.Name,
			Namespace: cm.Namespace,
			Data:      cm.Data,
			Labels:    cm.Labels,
			CreatedAt: cm.CreationTimestamp.Time,
		}
		configmapInfos = append(configmapInfos, configmapInfo)
	}

	return configmapInfos, nil
}

func (c *Client) ListNamespaces(ctx context.Context) ([]NamespaceInfo, error) {
	namespaces, err := c.clientset.CoreV1().Namespaces().List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to list namespaces: %w", err)
	}

	var namespaceInfos []NamespaceInfo
	for _, ns := range namespaces.Items {
		namespaceInfo := NamespaceInfo{
			Name:      ns.Name,
			Status:    string(ns.Status.Phase),
			Labels:    ns.Labels,
			CreatedAt: ns.CreationTimestamp.Time,
		}
		namespaceInfos = append(namespaceInfos, namespaceInfo)
	}

	return namespaceInfos, nil
}

func (c *Client) GetResource(ctx context.Context, identifier *types.ResourceIdentifier) (string, error) {
	switch identifier.Type {
	case types.ResourceTypePod:
		return c.getPodDetails(ctx, identifier.Namespace, identifier.Name)
	case types.ResourceTypeService:
		return c.getServiceDetails(ctx, identifier.Namespace, identifier.Name)
	case types.ResourceTypeDeployment:
		return c.getDeploymentDetails(ctx, identifier.Namespace, identifier.Name)
	case types.ResourceTypeConfigMap:
		return c.getConfigMapDetails(ctx, identifier.Namespace, identifier.Name)
	case types.ResourceTypeNamespace:
		return c.getNamespaceDetails(ctx, identifier.Name)
	default:
		return "", fmt.Errorf("unsupported resource type: %s", identifier.Type)
	}
}

func (c *Client) getPodDetails(ctx context.Context, namespace, name string) (string, error) {
	pod, err := c.clientset.CoreV1().Pods(namespace).Get(ctx, name, metav1.GetOptions{})
	if err != nil {
		return "", fmt.Errorf("failed to get pod %s/%s: %w", namespace, name, err)
	}

	// Create detailed pod information
	podDetail := struct {
		*PodInfo
		Containers []ContainerInfo `json:"containers"`
		Events     []string        `json:"recentEvents"`
		Conditions []string        `json:"conditions"`
	}{
		PodInfo: &PodInfo{
			Name:      pod.Name,
			Namespace: pod.Namespace,
			Status:    string(pod.Status.Phase),
			Phase:     string(pod.Status.Phase),
			Node:      pod.Spec.NodeName,
			Labels:    pod.Labels,
			CreatedAt: pod.CreationTimestamp.Time,
			Restarts:  getTotalRestarts(pod),
		},
		Containers: getContainerInfo(pod),
		Conditions: getPodConditions(pod),
	}

	data, err := json.MarshalIndent(podDetail, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to marshal pod details: %w", err)
	}

	return string(data), nil
}

func (c *Client) getServiceDetails(ctx context.Context, namespace, name string) (string, error) {
	service, err := c.clientset.CoreV1().Services(namespace).Get(ctx, name, metav1.GetOptions{})
	if err != nil {
		return "", fmt.Errorf("failed to get service %s/%s: %w", namespace, name, err)
	}

	var ports []ServicePort
	for _, port := range service.Spec.Ports {
		ports = append(ports, ServicePort{
			Name:       port.Name,
			Port:       port.Port,
			TargetPort: port.TargetPort.String(),
			Protocol:   string(port.Protocol),
		})
	}

	serviceDetail := struct {
		*ServiceInfo
		Selector  map[string]string `json:"selector"`
		Endpoints []string          `json:"endpoints"`
	}{
		ServiceInfo: &ServiceInfo{
			Name:      service.Name,
			Namespace: service.Namespace,
			Type:      string(service.Spec.Type),
			ClusterIP: service.Spec.ClusterIP,
			Ports:     ports,
			Labels:    service.Labels,
			CreatedAt: service.CreationTimestamp.Time,
		},
		Selector: service.Spec.Selector,
	}

	data, err := json.MarshalIndent(serviceDetail, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to marshal service details: %w", err)
	}

	return string(data), nil
}

func (c *Client) getDeploymentDetails(ctx context.Context, namespace, name string) (string, error) {
	deployment, err := c.clientset.AppsV1().Deployments(namespace).Get(ctx, name, metav1.GetOptions{})
	if err != nil {
		return "", fmt.Errorf("failed to get deployment %s/%s: %w", namespace, name, err)
	}

	strategy := "RollingUpdate"
	if deployment.Spec.Strategy.Type == appsv1.RecreateDeploymentStrategyType {
		strategy = "Recreate"
	}

	deploymentDetail := struct {
		*DeploymentInfo
		Selector   map[string]string `json:"selector"`
		Conditions []string          `json:"conditions"`
	}{
		DeploymentInfo: &DeploymentInfo{
			Name:            deployment.Name,
			Namespace:       deployment.Namespace,
			TotalReplicas:   *deployment.Spec.Replicas,
			ReadyReplicas:   deployment.Status.ReadyReplicas,
			UpdatedReplicas: deployment.Status.UpdatedReplicas,
			Labels:          deployment.Labels,
			CreatedAt:       deployment.CreationTimestamp.Time,
			Strategy:        strategy,
		},
		Selector:   deployment.Spec.Selector.MatchLabels,
		Conditions: getDeploymentConditions(deployment),
	}

	data, err := json.MarshalIndent(deploymentDetail, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to marshal deployment details: %w", err)
	}

	return string(data), nil
}

func (c *Client) getConfigMapDetails(ctx context.Context, namespace, name string) (string, error) {
	configmap, err := c.clientset.CoreV1().ConfigMaps(namespace).Get(ctx, name, metav1.GetOptions{})
	if err != nil {
		return "", fmt.Errorf("failed to get configmap %s/%s: %w", namespace, name, err)
	}

	configmapDetail := &ConfigMapInfo{
		Name:      configmap.Name,
		Namespace: configmap.Namespace,
		Data:      configmap.Data,
		Labels:    configmap.Labels,
		CreatedAt: configmap.CreationTimestamp.Time,
	}

	data, err := json.MarshalIndent(configmapDetail, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to marshal configmap details: %w", err)
	}

	return string(data), nil
}

func (c *Client) getNamespaceDetails(ctx context.Context, name string) (string, error) {
	namespace, err := c.clientset.CoreV1().Namespaces().Get(ctx, name, metav1.GetOptions{})
	if err != nil {
		return "", fmt.Errorf("failed to get namespace %s: %w", name, err)
	}

	namespaceDetail := &NamespaceInfo{
		Name:      namespace.Name,
		Status:    string(namespace.Status.Phase),
		Labels:    namespace.Labels,
		CreatedAt: namespace.CreationTimestamp.Time,
	}

	data, err := json.MarshalIndent(namespaceDetail, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to marshal namespace details: %w", err)
	}

	return string(data), nil
}

// Helper functions
type ContainerInfo struct {
	Name     string `json:"name"`
	Image    string `json:"image"`
	Ready    bool   `json:"ready"`
	Restarts int32  `json:"restarts"`
	State    string `json:"state"`
}

func getContainerInfo(pod *corev1.Pod) []ContainerInfo {
	var containers []ContainerInfo

	for i, container := range pod.Spec.Containers {
		info := ContainerInfo{
			Name:  container.Name,
			Image: container.Image,
		}

		if i < len(pod.Status.ContainerStatuses) {
			status := pod.Status.ContainerStatuses[i]
			info.Ready = status.Ready
			info.Restarts = status.RestartCount

			if status.State.Running != nil {
				info.State = "Running"
			} else if status.State.Waiting != nil {
				info.State = fmt.Sprintf("Waiting: %s", status.State.Waiting.Reason)
			} else if status.State.Terminated != nil {
				info.State = fmt.Sprintf("Terminated: %s", status.State.Terminated.Reason)
			}
		}

		containers = append(containers, info)
	}

	return containers
}

func getTotalRestarts(pod *corev1.Pod) int32 {
	var total int32
	for _, status := range pod.Status.ContainerStatuses {
		total += status.RestartCount
	}
	return total
}

func getPodConditions(pod *corev1.Pod) []string {
	var conditions []string
	for _, condition := range pod.Status.Conditions {
		if condition.Status == corev1.ConditionTrue {
			conditions = append(conditions, string(condition.Type))
		}
	}
	return conditions
}

func getDeploymentConditions(deployment *appsv1.Deployment) []string {
	var conditions []string
	for _, condition := range deployment.Status.Conditions {
		if condition.Status == corev1.ConditionTrue {
			conditions = append(conditions, fmt.Sprintf("%s: %s", condition.Type, condition.Message))
		}
	}
	return conditions
}
