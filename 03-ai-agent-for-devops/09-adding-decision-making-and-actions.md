# Chapter 9: Adding Decision-Making and Actions

In Chapter 8, we built a web interface that lets anyone analyze logs through natural conversation. The agent reads files, searches patterns, and explains what it finds. That's useful, but it's passive. It observes. It reports. It doesn't act.

Real incidents require action. When a pod crashes due to OutOfMemoryError, you don't just want analysis. You need someone to restart it. When a service goes down, reading logs is step one. Fixing the problem is step two.

This chapter closes that gap. We're adding the ability for our agent to take actions—specifically, restarting failed Kubernetes pods. But here's what makes this interesting: we're not building automation scripts. We're building an AI that decides when action is needed, recommends the right action, and executes it with your approval.

## The Problem with Analysis-Only Agents

I'll be direct: a log analyzer that only reads logs is half-finished.

Imagine the following situation, your Java application pod is in CrashLoopBackOff. You open the logs. OutOfMemoryError everywhere. Exit code 137. The fix is obvious: restart the pod.

Now imagine your workflow:
1. Use the AI agent to analyze the logs
2. Read the agent's analysis
3. Manually run `kubectl delete pod pod-name -n namespace`
4. Wait for Kubernetes to recreate the pod

The agent told you what's wrong and what to do. But you still had to leave the conversation, open a terminal, remember the kubectl command, and execute it manually.

That context switch kills efficiency. More importantly, it wastes the potential of having an AI agent. If the agent knows what's wrong and knows what to do, why can't it just do it?

The answer: it can. That's what we're building.

## What We're Adding

This chapter extends our agent with decision-making and action capabilities:

**Severity Classification**: The agent learns to classify incidents as P1 (critical), P2 (high), P3 (medium), or info. Not all issues are equal. OutOfMemoryError crashes are P1. Slow query warnings are P3. The agent needs to understand the difference.

**Action Recommendation**: Based on severity and issue type, the agent recommends specific actions. For OOM crashes, it recommends pod restart. For high memory usage, it recommends investigation. The recommendation comes with reasoning.

**User Approval Workflow**: The agent never executes actions blindly. It explains what it will do, why it will do it, and asks for confirmation. You stay in control.

**Action Execution**: After approval, the agent executes the action using Kubernetes tools. In this chapter, we use placeholder implementations—the tools print what they would do without touching real infrastructure. This lets you learn the patterns safely.

**Post-Action Guidance**: After executing an action, the agent provides next steps: what to monitor, how to prevent recurrence, what permanent fixes to consider.

The result: a complete incident response workflow from detection to resolution, all within a single conversation.

## Real-World Integration Patterns

Let me address something important: the interactive web UI we're building is for learning and demonstration. In production, you wouldn't sit at a browser refreshing logs.

Real-world AI logging agents run in one of these patterns:

### Pattern 1: Scheduled Analysis
The agent runs every N minutes, analyzes recent logs, and reports issues. Think of it as intelligent log monitoring that scales with your complexity.

```python
# Pseudocode - not in this chapter, coming later
while True:
    logs = fetch_recent_logs(last_5_minutes)
    issues = agent.analyze(logs)
    if issues.severity >= P2:
        notify_team(issues)
        if issues.severity == P1:
            action = agent.recommend_action(issues)
            if auto_approve(action):
                agent.execute(action)
    sleep(300)
```

### Pattern 2: Alert-Driven Analysis
Your monitoring system (Prometheus, Datadog, CloudWatch) triggers an alert. Instead of going to a human immediately, it goes to the AI agent first. The agent analyzes relevant logs, classifies severity, and either resolves it automatically or escalates with context.

```python
# Pseudocode - future chapter
@app.post("/webhook/alert")
def handle_alert(alert: Alert):
    # Alert from Prometheus/Datadog
    related_logs = fetch_logs(
        service=alert.service,
        timerange=alert.timerange
    )
    
    analysis = agent.analyze(related_logs)
    
    if analysis.can_auto_resolve:
        action = agent.recommend_action(analysis)
        result = agent.execute(action)
        notify_team(f"Auto-resolved: {result}")
    else:
        escalate_to_oncall(analysis)
```

### Pattern 3: API Integration
Other services call your agent via API. Your CI/CD pipeline runs tests, finds failures, and asks the agent to analyze test logs. Your deployment system detects a bad deploy and asks the agent to compare current logs with pre-deploy baselines.

The UI we're building demonstrates the core workflow. Later chapters will show you how to deploy these patterns in production. The decision-making logic stays the same. Only the trigger mechanism changes.

## Understanding the Workflow

Let's walk through a complete incident response flow to understand what we're building. The demo:

<h1 align="center" style="border-bottom: none">
  <img alt="The AI Agent with Decision Making" src="images/09.01.png" width="800">
</h1>

**Figure 9.1:** The AI Agent with Decision Making

<h1 align="center" style="border-bottom: none">
  <img alt="The AI Agent Executes Action" src="images/09.02.png" width="800">
</h1>

**Figure 9.2:** The AI Agent Executes Action

**Step 1: Log Analysis**
User asks: "Check app.log for issues"
Agent reads the file using `read_log_file` tool (read-only, automatic).

**Step 2: Issue Detection**
Agent finds:
- OutOfMemoryError: Java heap space
- GC overhead limit exceeded
- Exit code 137 (OOMKilled)
- Pod status: CrashLoopBackOff

**Step 3: Severity Classification**
Agent classifies this as P1 (Critical) because:
- Service is completely down (CrashLoopBackOff)
- Error is definitive (OOM, not intermittent)
- Impact is immediate (no availability)

**Step 4: Root Cause Analysis**
Agent determines:
- Memory limit: 1Gi
- Memory usage at crash: 1.02Gi
- Progressive memory growth visible in warnings
- Likely causes: large batch processing, cache growth

**Step 5: Analysis Presentation**
Agent presents:
```
Issue Summary: Pod experiencing OutOfMemoryError, in CrashLoopBackOff

Severity: P1

Analysis:
- Affected systems: pod-java-app-7d9f8b6c5-xk2m9 in production namespace
- Root cause: Memory usage (1.02Gi) exceeded limit (1Gi)
- Impact: Complete service outage
- Evidence: [key log lines with timestamps]

Recommended Action: Restart the pod to clear memory state and restore service.
This is a temporary fix. The pod will be recreated by the Deployment automatically.

Would you like me to proceed with restarting the pod? (yes/no)
```

**Step 6: User Decision**
User types: "yes"

**Step 7: Action Execution**
Agent calls `restart_kubernetes_pod` tool:
```python
restart_kubernetes_pod(
    pod_name="pod-java-app-7d9f8b6c5-xk2m9",
    namespace="production",
    reason="OutOfMemoryError recovery"
)
```

**Step 8: Post-Action Report**
Agent responds:
```
I have restarted pod-java-app-7d9f8b6c5-xk2m9 in production namespace.

Next Steps:
- Monitor pod status and memory usage
- Investigate memory leak in DataProcessor and CacheService
- Consider increasing memory limit from 1Gi to 2Gi
```

Notice the two-phase response pattern:
- Phase 1: Analysis and recommendation (before action)
- Phase 2: Execution confirmation and next steps (after action)

This keeps the conversation clear and purposeful. You get focused information to make decisions, then focused guidance on what to do next.

## Code Structure

We're building on Chapter 8's foundation. Here's what's new:

```
09/
├── system_prompt.txt          # NEW: Externalized AI instructions
├── logs/
│   └── k8s-java-app.log      # NEW: Realistic OOM crash logs
├── src/
│   ├── config.py             # UPDATED: Load prompt from file, K8s config
│   ├── agents/
│   │   └── log_analyzer.py   # UPDATED: Multi-step tool execution loop
│   ├── tools/
│   │   ├── log_reader.py
│   │   └── k8s_actions.py    # NEW: Kubernetes action tool
│   └── utils/
│       └── response.py
└── app.py                     # UPDATED: Enhanced UI for actions
```

### The Action Tool

Let's look at the new Kubernetes action tool:

```python
# src/tools/k8s_actions.py
from langchain.tools import tool
from ..config import Config

@tool
def restart_kubernetes_pod(
    pod_name: str, 
    namespace: str = "default", 
    reason: str = ""
) -> str:
    """
    Restart a Kubernetes pod by deleting it (will be recreated by deployment).
    IMPORTANT: Always ask for user approval before using this tool.
    
    Args:
        pod_name: Name of the pod to restart
        namespace: Kubernetes namespace (default: 'default')
        reason: Reason for restart (e.g., 'OutOfMemoryError recovery')
    
    Returns:
        Success or error message
    """
    # if not Config.is_k8s_configured():
    #     return "❌ Kubernetes not configured."
    
    # Placeholder implementation - safe for learning
    print(f"\n{'='*70}")
    print(f"PLACEHOLDER: Would restart Kubernetes pod")
    print(f"{'='*70}")
    print(f"Namespace: {namespace}")
    print(f"Pod Name:  {pod_name}")
    print(f"Reason:    {reason}")
    print(f"Action:    kubectl delete pod {pod_name} -n {namespace}")
    print(f"Expected:  Pod will be recreated by ReplicaSet/Deployment")
    print(f"{'='*70}\n")
    
    return (
        f"✅ [SIMULATED] Successfully restarted pod '{pod_name}' "
        f"in namespace '{namespace}'. Pod will be recreated automatically."
    )
```

This is a placeholder. It prints what it would do without actually doing it. This is intentional:

1. **Safety**: You can learn and test without risking your infrastructure
2. **Portability**: Code runs anywhere, no Kubernetes cluster required
3. **Clarity**: You see exactly what would happen
4. **Patterns**: The real implementation would replace the print statements with actual kubectl calls

The tool description is critical: "IMPORTANT: Always ask for user approval before using this tool." The AI reads this and knows not to execute automatically.

### The Enhanced Agent Loop

Chapter 8's agent executed tools once and returned. That worked for read-only operations. But action tools need a multi-step loop:

1. Agent analyzes logs (calls read_log_file)
2. Agent receives log content
3. Agent formulates response with recommendation
4. User confirms action
5. Agent calls restart_kubernetes_pod
6. Agent receives execution result
7. Agent formulates final response

Here's the key code change in `log_analyzer.py`:

```python
def _handle_tool_calls(self, response, user_input: str, chat_history: list) -> str:
    """Handle tool calls with iterative execution loop"""
    from langchain_core.messages import AIMessage, ToolMessage
    
    messages = self.prompt.format_messages(
        chat_history=chat_history,
        input=user_input
    )
    
    max_iterations = 5
    iteration = 0
    current_response = response
    
    while iteration < max_iterations:
        iteration += 1
        
        # Check if there are tool calls
        if not (hasattr(current_response, 'tool_calls') and 
                current_response.tool_calls):
            # No more tools to call, return final response
            return extract_response_text(current_response)
        
        # Execute each tool call
        tool_messages = []
        for tool_call in current_response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            
            # Find and execute the tool
            tool_func = next(
                (t for t in self.tools if t.name == tool_name), 
                None
            )
            
            if tool_func:
                result = tool_func.invoke(tool_args)
                tool_messages.append(
                    ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call['id']
                    )
                )
        
        # Add messages to conversation
        messages.append(AIMessage(
            content=current_response.content,
            tool_calls=current_response.tool_calls
        ))
        messages.extend(tool_messages)
        
        # Get next response (might call more tools or finish)
        current_response = self.llm_with_tools.invoke(messages)
    
    return extract_response_text(current_response)
```

The loop allows the agent to:
- Call read_log_file
- Analyze results
- Present recommendation
- Wait for user confirmation (via chat)
- Call restart_kubernetes_pod
- Present results

All within a single conversation flow.

### Externalizing the System Prompt

Chapter 8 had the system prompt hardcoded in Python. That works, but editing prompts means editing code. For an AI system, the prompt is configuration, not code.

We moved it to `system_prompt.txt`:

```python
# src/config.py
@classmethod
def get_system_prompt(cls) -> str:
    """Get the system prompt for the agent"""
    prompt_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'system_prompt.txt'
    )
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read()
```

Now you can iterate on the prompt without touching Python code. This is important because prompt engineering is iterative. You'll want to tweak the instructions, add examples, adjust the tone. Keeping it in a text file makes that workflow faster.

## The System Prompt

The prompt is where we teach the AI how to think about incidents. Here's the structure:

**Core Capabilities**: What the agent does (analyze logs, classify severity, recommend actions, execute with approval)

**Severity Classification**: Clear definitions of P1, P2, P3, info with examples

**Intelligent Response Workflow**: Two-phase approach
- Phase 1: Analysis and recommendation (don't include next steps yet)
- Phase 2: Execution report and next steps (after action is done)

**Interaction Principles**: Be concise, use natural language, explain WHY not just WHAT, never execute without approval

**Constraints**: Only analyze what's in logs, don't speculate, focus on actionable insights

The two-phase workflow is subtle but important. Many AI prompts try to cram everything into one response. That creates walls of text. By splitting analysis from execution, we keep each response focused on what the user needs in that moment.

Before action: "Here's what's wrong, here's what I recommend, do you want me to proceed?"
After action: "Here's what I did, here's what to watch, here's how to prevent this."

Clean. Purposeful. No information overload.

## Testing the Agent

Let's walk through testing this. Start the Streamlit app:

```bash
cd code/09
streamlit run app.py
```

The UI now shows Kubernetes-specific guidance in the sidebar:
- Configuration status (Gemini API ✅, Kubernetes ✅)
- Available tools including `restart_kubernetes_pod`
- Severity levels with action triggers
- Example questions focused on pod logs

Ask the agent: "Check app.log for issues"

The agent will:
1. Read the log file
2. Detect OutOfMemoryError and CrashLoopBackOff
3. Classify as P1
4. Analyze root cause (memory exceeded limit)
5. Show evidence (specific log lines)
6. Recommend restarting the pod
7. Ask for confirmation

You'll see a response like:

```
Issue Summary: Pod experiencing OutOfMemoryError, in CrashLoopBackOff

Severity: P1

Analysis:
- Affected systems: pod-java-app-7d9f8b6c5-xk2m9 in production namespace
- Root cause: Memory usage (1.02Gi) exceeded limit (1Gi)
- Impact: Complete service outage
- Evidence:
  2024-01-28 08:30:00 ERROR Failed to process large batch: OutOfMemoryError: Java heap space
  2024-01-28 08:30:06 ERROR Kubernetes detected pod crash: CrashLoopBackOff
  2024-01-28 08:30:10 ERROR Container killed by OOM killer

Recommended Action: Restart pod-java-app-7d9f8b6c5-xk2m9 in production 
namespace to clear memory state and restore service. The pod will be 
automatically recreated by the Deployment.

Would you like me to proceed with restarting the pod? (yes/no)
```

Notice: no "Next Steps" yet. The agent is focused on getting your decision.

Reply: "yes"

The agent executes the action and responds:

```
I have restarted pod-java-app-7d9f8b6c5-xk2m9 in production namespace.

Next Steps:
- Monitor pod status and memory usage closely
- Investigate memory leak in DataProcessor and CacheService
- Consider increasing memory limit from 1Gi to 2Gi
```

Now you get the forward-looking guidance. Two responses, two purposes, clean separation.

## What Makes This Different

You might be thinking: "This is just kubectl with extra steps." Fair question. Let's address it.

**Context**: kubectl restarts pods. But it doesn't know why you're restarting. This agent read the logs, understood the problem was OOM, identified the specific pod, checked the namespace, and recommended the exact action. That context matters.

**Decision Support**: kubectl requires you to know what to do. This agent tells you what to do and why. That's valuable when you're paged at 2 AM or when a junior engineer is on call.

**Workflow Integration**: kubectl is a separate tool. This agent combines log analysis, decision-making, and action execution in one conversation. No context switching.

**Auditability**: Every action has reasoning. "Why did we restart this pod?" Because the agent detected P1 OOM, analyzed the logs, classified severity, and recommended it based on standard recovery procedures. That's documented in the conversation.

**Scalability**: You can't scale manual kubectl commands. You can scale AI agents that analyze logs and take appropriate actions.

The real value isn't automating one kubectl command. It's creating a system that can:
- Analyze any log file
- Detect any type of issue
- Classify any severity level
- Recommend appropriate actions
- Execute with proper approval
- Provide preventive guidance

And you can extend it with more tools, more actions, more intelligence.

## Extending the System

This chapter focuses on one action: pod restart. But the architecture supports any action:

**Add a rollback tool**:
```python
@tool
def rollback_deployment(deployment_name: str, namespace: str = "default"):
    """Rollback deployment to previous revision."""
    # Implementation
```

**Add a cache clear tool**:
```python
@tool
def clear_cache(service_name: str):
    """Clear application cache."""
    # Implementation
```

The agent learns about tools from their descriptions. Add a tool, register it in `get_all_tools()`, and the agent can use it. No changes to the agent logic required.

The prompt teaches general principles (analyze, classify, recommend, execute with approval). The tools define specific capabilities. This separation scales.

## What's Next

You've built the foundation: the agent can restart a Kubernetes pod. But DevOps work involves dozens of repetitive manual actions. Every time you see "disk full" in logs, you SSH in and clean /tmp. When Redis cache hit rate drops, you flush it. When connection pool exhausted appears, you adjust the limits.

In the next chapter, you'll implement the actions you actually need:
- **Cache management** to clear Redis/Memcached when performance degrades
- **Disk cleanup** to remove old logs and temp files when space runs low
- **Service health checks** that verify and restart unresponsive services
- **Database pool management** to handle connection exhaustion
- **Queue management** to purge backed-up message queues

Each scenario maps a common log pattern to a real action. You'll move from placeholder print statements to actual kubectl, docker, and system commands—with proper safety checks and rollback mechanisms.
