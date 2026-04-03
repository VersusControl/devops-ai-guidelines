"""
Tools package for the AI agent.
Log analysis + Kubernetes + AWS RDS + Slack actions.
"""
from .log_reader import read_log_file, list_log_files, search_logs, get_log_tools
from .actions import restart_kubernetes_pod
from .aws_actions import reboot_rds_instance
from .slack_notifier import send_slack_notification

# Tool classification for auto-execute vs human approval
SAFE_TOOLS = {'read_log_file', 'list_log_files', 'search_logs', 'send_slack_notification'}
APPROVAL_REQUIRED_TOOLS = {'reboot_rds_instance', 'restart_kubernetes_pod'}


def requires_approval(tool_name: str) -> bool:
    """Check if a tool requires human approval before execution"""
    return tool_name in APPROVAL_REQUIRED_TOOLS


def get_all_tools():
    """Get all available tools for the agent"""
    tools = get_log_tools()
    tools.append(restart_kubernetes_pod)
    tools.append(reboot_rds_instance)
    tools.append(send_slack_notification)
    return tools


__all__ = [
    'read_log_file', 
    'list_log_files', 
    'search_logs', 
    'get_log_tools',
    'restart_kubernetes_pod',
    'reboot_rds_instance',
    'send_slack_notification',
    'get_all_tools',
    'requires_approval',
    'SAFE_TOOLS',
    'APPROVAL_REQUIRED_TOOLS',
]
