"""
Tools package for the AI agent
"""
from .log_reader import read_log_file, list_log_files, search_logs, get_log_tools
from .actions import restart_kubernetes_pod


def get_all_tools():
    """Get all available tools for the agent"""
    tools = get_log_tools()
    tools.append(restart_kubernetes_pod)
    return tools


__all__ = [
    'read_log_file', 
    'list_log_files', 
    'search_logs', 
    'get_log_tools',
    'restart_kubernetes_pod',
    'get_all_tools'
]
