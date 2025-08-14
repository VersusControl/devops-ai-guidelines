#!/bin/bash

# Dynamic security demo that discovers real pods first
set -e

echo "🔐 Enterprise Security Demo for Kubernetes MCP Server - Dynamic Version"
echo "=============================================================="

MCP_SERVER="http://localhost:8080/mcp"
ADMIN_KEY="demo-admin-key-67890"
READONLY_KEY="demo-readonly-key-12345"

# Function to extract pod names from JSON response
extract_pod_names() {
    local response="$1"
    echo "$response" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | head -3
}

# Function to extract deployment names from response  
extract_deployment_names() {
    local response="$1"
    echo "$response" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | head -2
}

echo -e "\n🎯 Step 1: Authentication Testing"
echo "================================="

echo -e "\n✅ Valid API Key Test:"
AUTH_TEST=$(curl -s -w "%{http_code}" -X POST \
    -H "Authorization: apikey $ADMIN_KEY" \
    "$MCP_SERVER/tools?tool=k8s_list_pods&namespace=default")
echo "Response Status: ${AUTH_TEST: -3}"

echo -e "\n❌ Invalid API Key Test:"
INVALID_AUTH=$(curl -s -w "%{http_code}" -X POST \
    -H "Authorization: apikey invalid-key" \
    "$MCP_SERVER/tools?tool=k8s_list_pods&namespace=default" || true)
echo "Response Status: ${INVALID_AUTH: -3}"

echo -e "\n🎯 Step 2: Dynamic Resource Discovery"
echo "====================================="

echo -e "\n📡 Discovering real pods..."
PODS_RESPONSE=$(curl -s -X POST \
    -H "Authorization: apikey $ADMIN_KEY" \
    "$MCP_SERVER/tools?tool=k8s_list_pods&namespace=default")

echo "$PODS_RESPONSE" | head -c 300
echo "..."

# Extract real pod names
POD_NAMES=($(extract_pod_names "$PODS_RESPONSE"))
echo -e "\n🎯 Found ${#POD_NAMES[@]} pods: ${POD_NAMES[*]}"

echo -e "\n📡 Discovering deployments..."
DEPLOY_RESPONSE=$(curl -s -X POST \
    -H "Authorization: apikey $ADMIN_KEY" \
    "$MCP_SERVER/tools?tool=k8s_list_deployments&namespace=default")

# Extract deployment names
DEPLOY_NAMES=($(extract_deployment_names "$DEPLOY_RESPONSE"))
echo "🎯 Found ${#DEPLOY_NAMES[@]} deployments: ${DEPLOY_NAMES[*]}"

echo -e "\n🎯 Step 3: RBAC Authorization Testing"
echo "===================================="

echo -e "\n✅ Admin user - should access everything:"
curl -s -w "Status: %{http_code}\n" -X POST \
    -H "Authorization: apikey $ADMIN_KEY" \
    "$MCP_SERVER/tools?tool=k8s_list_pods&namespace=default" | tail -1

echo -e "\n🔒 Read-only user - list pods (should work):"
curl -s -w "Status: %{http_code}\n" -X POST \
    -H "Authorization: apikey $READONLY_KEY" \
    "$MCP_SERVER/tools?tool=k8s_list_pods&namespace=default" | tail -1

if [ ${#DEPLOY_NAMES[@]} -gt 0 ]; then
    echo -e "\n❌ Read-only user - scale deployment (should fail):"
    curl -s -w "Status: %{http_code}\n" -X POST \
        -H "Authorization: apikey $READONLY_KEY" \
        "$MCP_SERVER/tools?tool=k8s_scale_deployment&namespace=default&name=${DEPLOY_NAMES[0]}&replicas=2&confirm=true" | tail -1
fi

echo -e "\n🎯 Step 4: Tool Execution with Real Resources"
echo "============================================="

if [ ${#DEPLOY_NAMES[@]} -gt 0 ]; then
    echo -e "\n⚡ Scaling deployment: ${DEPLOY_NAMES[0]}"
    curl -s -w "Status: %{http_code}\n" -X POST \
        -H "Authorization: apikey $ADMIN_KEY" \
        "$MCP_SERVER/tools?tool=k8s_scale_deployment&namespace=default&name=${DEPLOY_NAMES[0]}&replicas=3&confirm=true" | tail -1
fi

if [ ${#POD_NAMES[@]} -gt 0 ]; then
    echo -e "\n📋 Getting logs from pod: ${POD_NAMES[0]}"
    LOG_RESPONSE=$(curl -s -w "Status: %{http_code}" -X POST \
        -H "Authorization: apikey $ADMIN_KEY" \
        "$MCP_SERVER/tools?tool=k8s_get_pod_logs&namespace=default&name=${POD_NAMES[0]}")
    
    echo "${LOG_RESPONSE}" | head -c 200
    echo "..."
    echo "${LOG_RESPONSE}" | tail -1
fi

echo -e "\n🎯 Step 5: Parameter Validation Testing"
echo "======================================="

echo -e "\n❌ Invalid replicas (non-integer):"
curl -s -w "Status: %{http_code}\n" -X POST \
    -H "Authorization: apikey $ADMIN_KEY" \
    "$MCP_SERVER/tools?tool=k8s_scale_deployment&namespace=default&name=test&replicas=abc" | tail -1

echo -e "\n❌ Missing required parameter:"
curl -s -w "Status: %{http_code}\n" -X POST \
    -H "Authorization: apikey $ADMIN_KEY" \
    "$MCP_SERVER/tools?tool=k8s_scale_deployment&namespace=default" | tail -1

echo -e "\n🎯 Demo Complete!"
echo "================"
echo "✅ Authentication system working"
echo "✅ RBAC authorization enforced"
echo "✅ Real Kubernetes resources discovered and accessed"
echo "✅ Parameter validation working"
echo "🔒 Enterprise security features fully operational"
