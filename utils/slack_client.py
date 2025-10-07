"""
Slack Integration for Fundraising Team Notifications
Sends comprehensive analysis reports and strategy recommendations to Slack
"""

import os
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from .ai_context import ThreadAnalysis
from .strategy_generator import FundraisingStrategy, EmailStrategy


class SlackClient:
    """Handles Slack notifications for fundraising team."""
    
    def __init__(self):
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.bot_token = os.getenv("SLACK_BOT_TOKEN")
        
    def send_thread_analysis_report(self, analysis_data: Dict[str, Any], 
                                   strategy: FundraisingStrategy,
                                   thread_url: Optional[str] = None) -> bool:
        """
        Send comprehensive thread analysis report to Slack.
        
        Args:
            analysis_data: Complete analysis data from email analyzer
            strategy: Generated fundraising strategy
            thread_url: Optional link to the email thread
            
        Returns:
            True if sent successfully, False otherwise
        """
        
        if not self.webhook_url:
            print("No Slack webhook URL configured")
            return False
        
        try:
            # Build comprehensive Slack message
            message = self._build_analysis_message(analysis_data, strategy, thread_url)
            
            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"Error sending Slack notification: {e}")
            return False
    
    def send_strategy_approval_request(self, strategy: EmailStrategy, 
                                     thread_summary: str,
                                     approval_link: Optional[str] = None) -> bool:
        """
        Send strategy approval request to Slack with action buttons.
        
        Args:
            strategy: Email strategy to approve
            thread_summary: Brief thread summary
            approval_link: Link to approval interface
            
        Returns:
            True if sent successfully
        """
        
        if not self.webhook_url:
            return False
        
        try:
            message = self._build_approval_message(strategy, thread_summary, approval_link)
            
            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"Error sending approval request: {e}")
            return False
    
    def _build_analysis_message(self, analysis_data: Dict[str, Any], 
                              strategy: FundraisingStrategy,
                              thread_url: Optional[str] = None) -> Dict[str, Any]:
        """Build comprehensive analysis message for Slack."""
        
        analysis = analysis_data.get("analysis")
        metadata = analysis_data.get("metadata", {})
        
        # Determine emoji based on interest level
        interest_emoji = {
            "high": "🔥",
            "medium": "⚡",
            "low": "❄️",
            "unknown": "❓"
        }.get(analysis.investor_interest_level, "❓")
        
        # Build header
        header = f"{interest_emoji} *Investor Thread Analysis*"
        
        # Build main content blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": header
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Summary:* {analysis.summary}"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        # Analysis details
        analysis_fields = [
            {
                "type": "mrkdwn",
                "text": f"*Stage:* {analysis.conversation_stage.replace('_', ' ').title()}"
            },
            {
                "type": "mrkdwn",
                "text": f"*Interest Level:* {analysis.investor_interest_level.title()}"
            },
            {
                "type": "mrkdwn",
                "text": f"*Relationship:* {strategy.relationship_temperature.title()}"
            },
            {
                "type": "mrkdwn",
                "text": f"*Urgency:* {analysis.urgency_level.title()}"
            }
        ]
        
        blocks.append({
            "type": "section",
            "fields": analysis_fields
        })
        
        # Thread metadata
        if metadata:
            blocks.extend([
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Thread Stats*"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Messages:* {metadata.get('total_messages', 0)}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Participants:* {len(metadata.get('external_participants', []))}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Duration:* {metadata.get('conversation_span_days', 0)} days"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Last from team:* {'Yes' if metadata.get('last_sender_is_team') else 'No'}"
                        }
                    ]
                }
            ])
        
        # Investment signals
        if analysis.investment_signals:
            blocks.extend([
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*🎯 Investment Signals:*\n• " + "\n• ".join(analysis.investment_signals[:3])
                    }
                }
            ])
        
        # Concerns
        if analysis.concerns_raised:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*⚠️ Concerns Raised:*\n• " + "\n• ".join(analysis.concerns_raised[:3])
                }
            })
        
        # Primary strategy
        blocks.extend([
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📧 Recommended Strategy: {strategy.primary_strategy.strategy_type.replace('_', ' ').title()}*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Priority:* {strategy.primary_strategy.priority.title()} | *Timing:* {strategy.primary_strategy.timing.replace('_', ' ')}\n\n*Subject:* {strategy.primary_strategy.subject_line}"
                }
            }
        ])
        
        # Next steps
        if strategy.next_steps:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🎯 Next Steps:*\n• " + "\n• ".join(strategy.next_steps[:3])
                }
            })
        
        # Add action buttons if thread URL provided
        if thread_url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Thread"
                        },
                        "url": thread_url,
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Approve Strategy"
                        },
                        "url": thread_url,  # This would link to approval interface
                        "style": "primary"
                    }
                ]
            })
        
        return {
            "text": f"Investor Thread Analysis - {analysis.investor_interest_level.title()} Interest",
            "blocks": blocks
        }
    
    def _build_approval_message(self, strategy: EmailStrategy, 
                              thread_summary: str,
                              approval_link: Optional[str] = None) -> Dict[str, Any]:
        """Build approval request message."""
        
        priority_emoji = {
            "high": "🔴",
            "medium": "🟡", 
            "low": "🟢"
        }.get(strategy.priority, "🟡")
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{priority_emoji} Email Strategy Approval Required"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Thread:* {thread_summary}\n*Strategy:* {strategy.strategy_type.replace('_', ' ').title()}\n*Priority:* {strategy.priority.title()}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Subject Line:*\n{strategy.subject_line}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Email Preview:*\n```{strategy.email_body[:300]}{'...' if len(strategy.email_body) > 300 else ''}```"
                }
            }
        ]
        
        if approval_link:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Review & Approve"
                        },
                        "url": approval_link,
                        "style": "primary"
                    }
                ]
            })
        
        return {
            "text": f"Email Strategy Approval Required - {strategy.priority.title()} Priority",
            "blocks": blocks
        }
    
    def send_simple_notification(self, message: str, channel: Optional[str] = None) -> bool:
        """Send a simple text notification."""
        
        if not self.webhook_url:
            return False
        
        try:
            payload = {"text": message}
            if channel:
                payload["channel"] = channel
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"Error sending simple notification: {e}")
            return False


def send_fundraising_analysis_to_slack(analysis_data: Dict[str, Any], 
                                     strategy: FundraisingStrategy,
                                     thread_url: Optional[str] = None) -> bool:
    """
    Convenience function to send fundraising analysis to Slack.
    
    Args:
        analysis_data: Complete analysis from email analyzer
        strategy: Generated fundraising strategy
        thread_url: Optional thread URL
        
    Returns:
        True if sent successfully
    """
    slack_client = SlackClient()
    return slack_client.send_thread_analysis_report(analysis_data, strategy, thread_url)