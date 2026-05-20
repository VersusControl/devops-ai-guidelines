"""
Slack Notification Tool
Send incident reports and notifications to Slack channels.
Uses placeholder mode when Slack webhook is not configured.
"""
import os
import json
from langchain_core.tools import tool


def _is_slack_configured() -> bool:
    """Check if Slack webhook URL is available"""
    return bool(os.getenv('SLACK_WEBHOOK_URL'))


@tool
def send_slack_notification(
    channel: str,
    summary: str,
    severity: str = "P1",
    details: str = "",
    actions_taken: str = ""
) -> str:
    """
    Send an incident notification to a Slack channel with details about the issue and actions taken.
    Use this AFTER an action has been executed to notify the team about what happened.
    
    Args:
        channel: Slack channel name (e.g., '#devops-alerts', '#incident-response')
        summary: Brief incident summary (e.g., 'RDS connection exhaustion on orders-db-prod')
        severity: Incident severity level ('P1', 'P2', 'P3', 'info')
        details: Detailed description of the issue and root cause
        actions_taken: Description of remediation actions that were executed
    
    Returns:
        str: Success or error message
    """
    if _is_slack_configured():
        return _send_slack_real(channel, summary, severity, details, actions_taken)
    else:
        return _send_slack_placeholder(channel, summary, severity, details, actions_taken)


def _build_slack_payload(channel: str, summary: str, severity: str, details: str, actions_taken: str) -> dict:
    """Build a structured Slack message payload"""
    severity_tags = {
        "P1": "[CRITICAL]",
        "P2": "[HIGH]", 
        "P3": "[MEDIUM]",
        "info": "[INFO]"
    }
    tag = severity_tags.get(severity, "[UNKNOWN]")
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{tag} {severity} Incident: {summary}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Severity:* {severity}\n*Summary:* {summary}"
            }
        }
    ]
    
    if details:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Details:*\n{details}"
            }
        })
    
    if actions_taken:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Actions Taken:*\n{actions_taken}"
            }
        })
    
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "Sent by AI Logging Agent | DevOps Automation"
            }
        ]
    })
    
    return {
        "channel": channel,
        "blocks": blocks,
        "text": f"{tag} {severity}: {summary}"  # Fallback text
    }


def _send_slack_real(channel: str, summary: str, severity: str, details: str, actions_taken: str) -> str:
    """Send real Slack notification via webhook"""
    try:
        import urllib.request
        import urllib.error
        
        webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        payload = _build_slack_payload(channel, summary, severity, details, actions_taken)
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                return (
                    f"Slack notification sent to {channel}.\n"
                    f"Summary: {severity} - {summary}"
                )
            else:
                return f"Slack API returned status {response.status}"
                
    except urllib.error.URLError as e:
        return f"Failed to send Slack notification: {str(e)}"
    except Exception as e:
        return f"Error sending Slack notification: {str(e)}"


def _send_slack_placeholder(channel: str, summary: str, severity: str, details: str, actions_taken: str) -> str:
    """Placeholder Slack notification for learning/testing"""
    payload = _build_slack_payload(channel, summary, severity, details, actions_taken)
    
    print(f"\n{'='*70}")
    print(f"PLACEHOLDER: Would send Slack notification")
    print(f"{'='*70}")
    print(f"Channel:  {channel}")
    print(f"Severity: {severity}")
    print(f"Summary:  {summary}")
    if details:
        print(f"Details:  {details[:200]}...")
    if actions_taken:
        print(f"Actions:  {actions_taken[:200]}...")
    print(f"\nPayload preview:")
    print(json.dumps(payload, indent=2)[:500])
    print(f"{'='*70}\n")
    
    return (
        f"[SIMULATED] Slack notification sent to {channel}.\n"
        f"Summary: {severity} - {summary}\n"
        f"The team has been notified about the incident and actions taken."
    )
