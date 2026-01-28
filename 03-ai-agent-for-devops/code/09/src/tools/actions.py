"""
Action Tools
"""
from langchain.tools import tool
from ..config import Config


@tool
def restart_kubernetes_pod(pod_name: str, namespace: str = "default", reason: str = "") -> str:
    """
    Restart a Kubernetes pod by deleting it (will be recreated by deployment/replicaset).
    IMPORTANT: Always ask for user approval before using this tool as it will cause service disruption.
    
    Args:
        pod_name: Name of the pod to restart (e.g., 'pod-java-app-7d9f8b6c5-xk2m9')
        namespace: Kubernetes namespace (default: 'default')
        reason: Reason for restart (e.g., 'OutOfMemoryError recovery')
    
    Returns:
        str: Success or error message
    """
    # Placeholder implementation
    # if not Config.is_k8s_configured():
    #     return "❌ Kubernetes not configured. Set K8S_KUBECONFIG or K8S_CONTEXT in .env file to enable."
    
    # Simulate pod restart
    print(f"\n{'='*70}")
    print(f"PLACEHOLDER: Would restart Kubernetes pod")
    print(f"{'='*70}")
    print(f"Namespace: {namespace}")
    print(f"Pod Name:  {pod_name}")
    print(f"Reason:    {reason}")
    print(f"Action:    kubectl delete pod {pod_name} -n {namespace}")
    print(f"Expected:  Pod will be recreated automatically by ReplicaSet/Deployment")
    print(f"{'='*70}\n")
    
    return f"✅ [SIMULATED] Successfully restarted pod '{pod_name}' in namespace '{namespace}'. Pod will be recreated automatically."
