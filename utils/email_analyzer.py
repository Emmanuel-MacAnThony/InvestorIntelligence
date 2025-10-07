"""
Email Thread Analyzer for Fundraising Teams
Extracts context from Gmail threads and prepares for AI analysis
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from .ai_context import EmailMessage, ThreadAnalysis, AIContextEngine
from .gmail_client import GmailClient


class EmailThreadAnalyzer:
    """Analyzes email threads for fundraising context and insights."""
    
    def __init__(self):
        self.ai_engine = AIContextEngine()
        
    def analyze_thread_from_gmail(self, gmail_client: GmailClient, mailbox: str, thread_id: str, 
                                 user_email: str, company_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a Gmail thread for fundraising insights.
        
        Args:
            gmail_client: Authenticated Gmail client
            mailbox: Mailbox/email address to use for authentication
            thread_id: Gmail thread ID
            user_email: Email address of the fundraising team member
            company_context: Optional context about the company
            
        Returns:
            Complete analysis with thread data and AI insights
        """
        
        # Get thread messages from Gmail
        thread_data = gmail_client.get_thread(mailbox, thread_id)
        if not thread_data or 'messages' not in thread_data:
            return {"error": "Could not retrieve thread data"}
        
        if thread_data.get("error"):
            return {"error": f"Gmail API error: {thread_data['error']}"}
        
        # Parse messages into structured format
        messages = self._parse_gmail_messages(thread_data['messages'], user_email)
        
        if not messages:
            return {"error": "No messages found in thread"}
        
        # Get AI analysis
        analysis = self.ai_engine.analyze_thread(messages, company_context)
        
        # Extract additional metadata
        metadata = self._extract_thread_metadata(messages)
        
        return {
            "thread_id": thread_id,
            "messages": messages,
            "analysis": analysis,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
    
    def _parse_gmail_messages(self, gmail_messages: List[Dict], user_email: str) -> List[EmailMessage]:
        """Parse Gmail API messages into EmailMessage objects."""
        messages = []
        
        for msg in gmail_messages:
            try:
                # Extract headers
                headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
                
                sender = headers.get('From', 'Unknown')
                recipient = headers.get('To', 'Unknown')
                subject = headers.get('Subject', 'No Subject')
                date = headers.get('Date', '')
                
                # Extract body
                body = self._extract_message_body(msg.get('payload', {}))
                
                # Determine if message is from team
                is_from_team = self._is_from_team(sender, user_email)
                
                # Parse timestamp
                timestamp = self._parse_timestamp(date)
                
                messages.append(EmailMessage(
                    sender=self._clean_email_address(sender),
                    recipient=self._clean_email_address(recipient),
                    subject=subject,
                    body=body,
                    timestamp=timestamp,
                    is_from_team=is_from_team
                ))
                
            except Exception as e:
                print(f"Error parsing message: {e}")
                continue
        
        # Sort by timestamp
        messages.sort(key=lambda x: x.timestamp)
        return messages
    
    def _extract_message_body(self, payload: Dict) -> str:
        """Extract text body from Gmail message payload."""
        
        def extract_text_from_part(part):
            """Recursively extract text from message parts."""
            mime_type = part.get('mimeType', '')
            
            if mime_type == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    import base64
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            
            elif mime_type == 'text/html':
                data = part.get('body', {}).get('data', '')
                if data:
                    import base64
                    html_content = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    return self._html_to_text(html_content)
            
            elif 'parts' in part:
                # Multipart message
                text_parts = []
                for subpart in part['parts']:
                    text = extract_text_from_part(subpart)
                    if text:
                        text_parts.append(text)
                return '\n'.join(text_parts)
            
            return ''
        
        body = extract_text_from_part(payload)
        return self._clean_email_body(body)
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text()
        except:
            # Fallback: simple HTML tag removal
            return re.sub(r'<[^>]+>', '', html)
    
    def _clean_email_body(self, body: str) -> str:
        """Clean and normalize email body text."""
        if not body:
            return ""
        
        # Remove excessive whitespace
        body = re.sub(r'\n\s*\n', '\n\n', body)
        body = re.sub(r' +', ' ', body)
        
        # Remove common email signatures and footers
        body = re.sub(r'\n-- \n.*$', '', body, flags=re.DOTALL)
        body = re.sub(r'\nSent from my.*$', '', body, flags=re.DOTALL)
        
        # Remove forwarded/replied headers
        body = re.sub(r'\n\s*On .* wrote:\n', '\n[Previous message]\n', body)
        body = re.sub(r'\n\s*From:.*\nTo:.*\nSubject:.*\n', '\n[Previous message]\n', body)
        
        return body.strip()
    
    def _clean_email_address(self, email_str: str) -> str:
        """Extract clean email address from header string."""
        # Handle "Name <email@domain.com>" format
        match = re.search(r'<([^>]+)>', email_str)
        if match:
            return match.group(1)
        
        # Handle just email format
        match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', email_str)
        if match:
            return match.group(1)
        
        return email_str
    
    def _is_from_team(self, sender: str, user_email: str) -> bool:
        """Determine if message is from the fundraising team."""
        sender_clean = self._clean_email_address(sender).lower()
        user_domain = user_email.split('@')[1].lower() if '@' in user_email else ''
        sender_domain = sender_clean.split('@')[1] if '@' in sender_clean else ''
        
        # Same domain indicates team member
        return sender_domain == user_domain
    
    def _parse_timestamp(self, date_str: str) -> str:
        """Parse email date string to ISO format."""
        if not date_str:
            return datetime.now().isoformat()
        
        try:
            # Gmail date format: "Mon, 15 Jan 2024 10:30:00 -0800"
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            return dt.isoformat()
        except:
            return datetime.now().isoformat()
    
    def _extract_thread_metadata(self, messages: List[EmailMessage]) -> Dict[str, Any]:
        """Extract metadata about the thread."""
        if not messages:
            return {}
        
        # Identify participants
        team_participants = set()
        external_participants = set()
        
        for msg in messages:
            if msg.is_from_team:
                team_participants.add(msg.sender)
                external_participants.add(msg.recipient)
            else:
                external_participants.add(msg.sender)
                team_participants.add(msg.recipient)
        
        # Thread statistics
        total_messages = len(messages)
        team_messages = sum(1 for msg in messages if msg.is_from_team)
        external_messages = total_messages - team_messages
        
        # Timeline
        first_message = messages[0]
        last_message = messages[-1]
        
        return {
            "total_messages": total_messages,
            "team_messages": team_messages,
            "external_messages": external_messages,
            "team_participants": list(team_participants),
            "external_participants": list(external_participants),
            "first_message_date": first_message.timestamp,
            "last_message_date": last_message.timestamp,
            "conversation_span_days": self._calculate_span_days(first_message.timestamp, last_message.timestamp),
            "last_sender_is_team": last_message.is_from_team
        }
    
    def _calculate_span_days(self, start_date: str, end_date: str) -> int:
        """Calculate days between first and last message."""
        try:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            return (end - start).days
        except:
            return 0


def analyze_fundraising_thread(gmail_client: GmailClient, mailbox: str, thread_id: str, 
                             user_email: str, company_context: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to analyze a fundraising email thread.
    
    Args:
        gmail_client: Authenticated Gmail client
        mailbox: Mailbox/email address to use for authentication
        thread_id: Gmail thread ID
        user_email: Email of the team member
        company_context: Optional company context
        
    Returns:
        Complete thread analysis
    """
    analyzer = EmailThreadAnalyzer()
    return analyzer.analyze_thread_from_gmail(gmail_client, mailbox, thread_id, user_email, company_context)