"""
Advanced Fundraising Intelligence Engine with LangGraph
Multi-step workflow for comprehensive investor relationship analysis and campaign optimization
"""

import os
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, TypedDict
from dataclasses import dataclass, asdict
from email.utils import parsedate_to_datetime
import re
import hashlib

# LangGraph imports
from langgraph.graph import StateGraph, END

# AI imports
import openai
from openai import OpenAI

# Local imports
from .gmail_client import GmailClient


@dataclass
class InvestorContext:
    """Comprehensive investor relationship context"""
    email: str
    name: str = ""
    firm: str = ""
    last_contact_date: Optional[datetime] = None
    relationship_stage: str = "unknown"  # cold, warm, engaged, interested, declined, deferred
    sentiment_trend: str = "neutral"  # positive, neutral, negative
    response_time_avg: Optional[float] = None  # average response time in hours
    preferred_contact_day: str = ""  # monday, tuesday, etc.
    preferred_contact_time: str = ""  # morning, afternoon, evening
    key_interests: List[str] = None
    objections_raised: List[str] = None
    questions_asked: List[str] = None
    materials_shared: List[str] = None
    next_action_suggested: str = ""
    defer_until: Optional[datetime] = None
    total_emails_sent: int = 0
    total_replies_received: int = 0
    last_reply_sentiment: str = "neutral"
    conversation_summary: str = ""
    
    def __post_init__(self):
        if self.key_interests is None:
            self.key_interests = []
        if self.objections_raised is None:
            self.objections_raised = []
        if self.questions_asked is None:
            self.questions_asked = []
        if self.materials_shared is None:
            self.materials_shared = []


@dataclass
class EmailMetadata:
    """Email metadata for timing and pattern analysis"""
    message_id: str
    thread_id: str
    sender: str
    recipient: str
    timestamp: datetime
    is_reply: bool
    subject: str
    body_length: int
    has_attachments: bool
    labels: List[str] = None
    # Enhanced context fields
    body_content: str = ""
    snippet: str = ""
    cc: str = ""
    bcc: str = ""
    reply_to: str = ""
    message_refs: List[str] = None  # In-Reply-To, References
    time_of_day: str = ""
    day_of_week: str = ""
    is_outbound: bool = False  # True if sent by user
    response_time_hours: Optional[float] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = []
        if self.message_refs is None:
            self.message_refs = []
        
        # Extract time context
        if self.timestamp:
            self.time_of_day = "morning" if self.timestamp.hour < 12 else "afternoon" if self.timestamp.hour < 17 else "evening"
            self.day_of_week = self.timestamp.strftime("%A").lower()


@dataclass
class CampaignStrategy:
    """Generated campaign strategy with multi-channel coordination"""
    investor_email: str
    strategy_type: str  # follow_up, re_engagement, milestone_update, cold_outreach
    recommended_timing: datetime
    email_draft: str
    linkedin_message: str = ""
    reasoning: str = ""
    confidence_score: float = 0.0
    channel_sequence: List[str] = None  # ["email", "linkedin", "email_follow_up"]
    expected_response_rate: float = 0.0
    
    def __post_init__(self):
        if self.channel_sequence is None:
            self.channel_sequence = ["email"]


@dataclass
class FundraisingState:
    """LangGraph state for the fundraising intelligence workflow"""
    # Input parameters (serializable)
    mailbox: str = ""
    user_email: str = ""
    company_context: str = ""
    time_window_days: int = 30
    
    # Data collection (serializable)
    raw_emails: List[Dict] = None
    email_metadata: List[EmailMetadata] = None
    thread_groups: Dict[str, List[EmailMetadata]] = None
    
    # Analysis results (serializable)
    investor_contexts: Dict[str, InvestorContext] = None
    timing_patterns: Dict[str, Dict] = None
    strategy_effectiveness: Dict[str, float] = None
    
    # Generated outputs (serializable)
    campaign_strategies: List[CampaignStrategy] = None
    retrospective_report: str = ""
    
    # Workflow control
    current_step: str = ""
    errors: List[str] = None
    
    def __post_init__(self):
        if self.raw_emails is None:
            self.raw_emails = []
        if self.email_metadata is None:
            self.email_metadata = []
        if self.thread_groups is None:
            self.thread_groups = {}
        if self.investor_contexts is None:
            self.investor_contexts = {}
        if self.timing_patterns is None:
            self.timing_patterns = {}
        if self.strategy_effectiveness is None:
            self.strategy_effectiveness = {}
        if self.campaign_strategies is None:
            self.campaign_strategies = []
        if self.errors is None:
            self.errors = []


class FundraisingIntelligenceEngine:
    """Main orchestrator for the fundraising intelligence workflow"""
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for fundraising intelligence"""
        workflow = StateGraph(FundraisingState)
        
        # Add nodes
        workflow.add_node("fetch_emails", self._fetch_emails_node)
        workflow.add_node("group_threads", self._group_threads_node)
        workflow.add_node("analyze_conversations", self._analyze_conversations_node)
        workflow.add_node("extract_timing_patterns", self._extract_timing_patterns_node)
        workflow.add_node("analyze_strategy_effectiveness", self._analyze_strategy_effectiveness_node)
        workflow.add_node("generate_campaign_strategies", self._generate_campaign_strategies_node)
        workflow.add_node("generate_retrospective", self._generate_retrospective_node)
        
        # Define edges (workflow sequence)
        workflow.set_entry_point("fetch_emails")
        workflow.add_edge("fetch_emails", "group_threads")
        workflow.add_edge("group_threads", "analyze_conversations")
        workflow.add_edge("analyze_conversations", "extract_timing_patterns")
        workflow.add_edge("extract_timing_patterns", "analyze_strategy_effectiveness")
        workflow.add_edge("analyze_strategy_effectiveness", "generate_campaign_strategies")
        workflow.add_edge("generate_campaign_strategies", "generate_retrospective")
        workflow.add_edge("generate_retrospective", END)
        
        return workflow.compile()
    
    async def run_intelligence_analysis(
        self,
        gmail_client: GmailClient,
        mailbox: str,
        user_email: str,
        company_context: str = "",
        time_window_days: int = 30
    ) -> FundraisingState:
        """
        Run the complete fundraising intelligence analysis
        
        Args:
            gmail_client: Authenticated Gmail client
            mailbox: Email address to analyze
            user_email: User's email address
            company_context: Context about the company/fundraising
            time_window_days: Number of days to analyze
            
        Returns:
            Complete analysis results with strategies and reports
        """
        
        initial_state = FundraisingState(
            mailbox=mailbox,
            user_email=user_email,
            company_context=company_context,
            time_window_days=time_window_days,
            current_step="initializing"
        )
        
        # Store the gmail_client separately since it's not serializable
        self._gmail_client = gmail_client
        
        # Run the workflow without serialization (disable checkpointing)
        final_state = await self.workflow.ainvoke(initial_state)
        
        return final_state
    
    async def _fetch_emails_node(self, state: FundraisingState) -> FundraisingState:
        """Node 1: Fetch emails from Gmail with fundraising labels"""
        try:
            print(f"[FUNDRAISING ENGINE] Starting email fetch...")
            state.current_step = "fetching_emails"
            
            # Define broader query to capture all investor communications
            since_date = datetime.now() - timedelta(days=state.time_window_days)
            query_parts = [
                f"after:{since_date.strftime('%Y/%m/%d')}",
                f"(from:{state.user_email} OR to:{state.user_email})",
                # Much broader search to catch actual investor emails
                "(investor OR funding OR investment OR vc OR capital OR round OR startup OR pitch OR deck OR valuation OR equity OR Series OR angel OR accelerator OR incubator OR demo OR meeting OR call OR coffee OR intro OR introduction OR thanks OR follow OR update OR deck OR traction OR revenue OR growth OR team OR product OR market)"
            ]
            query = " ".join(query_parts)
            
            # Search emails (use the stored gmail client)
            search_result = self._gmail_client.search_emails(state.mailbox, query, max_results=500)
            
            if search_result.get("error"):
                state.errors.append(f"Gmail search failed: {search_result['error']}")
                return state
            
            # Get full message details
            raw_emails = []
            messages = search_result.get("messages", [])
            
            for message in messages[:100]:  # Limit for performance
                msg_data = self._gmail_client.get_message(state.mailbox, message["id"])
                if msg_data and not msg_data.get("error"):
                    raw_emails.append(msg_data)
            
            state.raw_emails = raw_emails
            print(f"[FUNDRAISING ENGINE] Found {len(raw_emails)} emails, parsing metadata...")

            # Convert to metadata objects
            email_metadata = []
            for email in raw_emails:
                try:
                    headers = {h["name"]: h["value"] for h in email.get("payload", {}).get("headers", [])}
                    
                    # Parse timestamp
                    date_str = headers.get("Date", "")
                    timestamp = None
                    try:
                        timestamp = parsedate_to_datetime(date_str)
                    except:
                        timestamp = datetime.now()
                    
                    # Determine sender/recipient and additional headers
                    sender = headers.get("From", "")
                    recipient = headers.get("To", "")
                    cc = headers.get("Cc", "")
                    bcc = headers.get("Bcc", "")
                    reply_to = headers.get("Reply-To", "")
                    
                    # Check if it's a reply and extract message references
                    is_reply = "Re:" in headers.get("Subject", "") or headers.get("In-Reply-To") is not None
                    message_refs = []
                    if headers.get("In-Reply-To"):
                        message_refs.append(headers["In-Reply-To"])
                    if headers.get("References"):
                        message_refs.extend(headers["References"].split())
                    
                    # Determine if outbound (from user)
                    is_outbound = state.user_email.lower() in sender.lower()
                    
                    # Extract body content
                    body_content = self._extract_email_body(email)
                    snippet = email.get("snippet", "")
                    
                    # Get labels
                    labels = email.get("labelIds", [])
                    
                    metadata = EmailMetadata(
                        message_id=email["id"],
                        thread_id=email["threadId"],
                        sender=sender,
                        recipient=recipient,
                        timestamp=timestamp,
                        is_reply=is_reply,
                        subject=headers.get("Subject", ""),
                        body_length=len(body_content),
                        has_attachments="attachment" in str(email).lower(),
                        labels=labels,
                        body_content=body_content,
                        snippet=snippet,
                        cc=cc,
                        bcc=bcc,
                        reply_to=reply_to,
                        message_refs=message_refs,
                        is_outbound=is_outbound
                    )
                    
                    email_metadata.append(metadata)
                    
                except Exception as e:
                    state.errors.append(f"Failed to parse email metadata: {str(e)}")
                    continue
            
            state.email_metadata = email_metadata
            print(f"[FUNDRAISING ENGINE] Parsed {len(email_metadata)} emails successfully")

        except Exception as e:
            state.errors.append(f"Email fetching failed: {str(e)}")
        
        return state
    
    async def _group_threads_node(self, state: FundraisingState) -> FundraisingState:
        """Node 2: Group emails by recipient for investor-level conversation threads"""
        try:
            print(f"[FUNDRAISING ENGINE] Grouping threads...")
            state.current_step = "grouping_threads"
            
            # Group by investor email (normalize email addresses)
            thread_groups = {}
            
            for email in state.email_metadata:
                # Determine the investor email (not the user's email)
                investor_email = ""
                if state.user_email.lower() in email.sender.lower():
                    # User sent this email
                    investor_email = self._extract_email(email.recipient)
                else:
                    # User received this email
                    investor_email = self._extract_email(email.sender)
                
                if investor_email and investor_email != state.user_email.lower():
                    if investor_email not in thread_groups:
                        thread_groups[investor_email] = []
                    thread_groups[investor_email].append(email)
            
            # Sort emails in each group by timestamp
            for investor_email in thread_groups:
                thread_groups[investor_email].sort(key=lambda x: x.timestamp)
            
            state.thread_groups = thread_groups
            print(f"[FUNDRAISING ENGINE] Grouped into {len(thread_groups)} investor conversations")

        except Exception as e:
            state.errors.append(f"Thread grouping failed: {str(e)}")
        
        return state
    
    def _extract_email(self, email_field: str) -> str:
        """Extract clean email address from email field"""
        if not email_field:
            return ""
        
        # Use regex to extract email from "Name <email@domain.com>" format
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', email_field)
        if email_match:
            return email_match.group().lower()
        
        return email_field.lower().strip()
    
    async def _analyze_conversations_node(self, state: FundraisingState) -> FundraisingState:
        """Node 3: Analyze each investor conversation with LLM"""
        try:
            print(f"[FUNDRAISING ENGINE] Analyzing {len(state.thread_groups)} conversations with AI...")
            state.current_step = "analyzing_conversations"

            investor_contexts = {}

            for idx, (investor_email, emails) in enumerate(state.thread_groups.items()):
                print(f"[FUNDRAISING ENGINE] Analyzing conversation {idx+1}/{len(state.thread_groups)}: {investor_email}")
                try:
                    # Build conversation context
                    conversation_text = self._build_conversation_text(emails, state.user_email)
                    
                    # Analyze with LLM
                    analysis = await self._analyze_investor_conversation(
                        conversation_text, 
                        investor_email,
                        state.company_context
                    )
                    
                    # Calculate metrics
                    sent_count = sum(1 for e in emails if state.user_email.lower() in e.sender.lower())
                    reply_count = sum(1 for e in emails if state.user_email.lower() not in e.sender.lower())
                    
                    # Calculate response times
                    response_times = self._calculate_response_times(emails, state.user_email)
                    avg_response_time = sum(response_times) / len(response_times) if response_times else None
                    
                    # Create investor context
                    context = InvestorContext(
                        email=investor_email,
                        name=analysis.get("name", ""),
                        firm=analysis.get("firm", ""),
                        last_contact_date=emails[-1].timestamp if emails else None,
                        relationship_stage=analysis.get("relationship_stage", "unknown"),
                        sentiment_trend=analysis.get("sentiment_trend", "neutral"),
                        response_time_avg=avg_response_time,
                        key_interests=analysis.get("key_interests", []),
                        objections_raised=analysis.get("objections_raised", []),
                        questions_asked=analysis.get("questions_asked", []),
                        materials_shared=analysis.get("materials_shared", []),
                        next_action_suggested=analysis.get("next_action_suggested", ""),
                        total_emails_sent=sent_count,
                        total_replies_received=reply_count,
                        last_reply_sentiment=analysis.get("last_reply_sentiment", "neutral"),
                        conversation_summary=analysis.get("conversation_summary", "")
                    )
                    
                    investor_contexts[investor_email] = context
                    
                except Exception as e:
                    state.errors.append(f"Failed to analyze conversation with {investor_email}: {str(e)}")
                    continue
            
            state.investor_contexts = investor_contexts
            print(f"[FUNDRAISING ENGINE] Completed analyzing {len(investor_contexts)} conversations")

        except Exception as e:
            state.errors.append(f"Conversation analysis failed: {str(e)}")
        
        return state
    
    def _anonymize_email_content(self, content: str, email_map: Dict[str, str]) -> str:
        """Anonymize email content by replacing sensitive data with placeholders"""
        if not content:
            return content
            
        # Email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        # Phone patterns
        phone_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # US format
            r'\b\(\d{3}\)\s?\d{3}[-.]?\d{4}\b',  # (123) 456-7890
            r'\b\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b'  # International
        ]
        
        # URL patterns
        url_pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+\.[^\s<>"\']+'
        
        # Replace emails with consistent placeholders
        emails_found = re.findall(email_pattern, content)
        for email in emails_found:
            if email not in email_map:
                # Create consistent hash-based placeholder
                hash_suffix = hashlib.md5(email.encode()).hexdigest()[:6]
                email_map[email] = f"[EMAIL_{hash_suffix}]"
            content = content.replace(email, email_map[email])
        
        # Replace phone numbers
        for pattern in phone_patterns:
            content = re.sub(pattern, '[PHONE_NUMBER]', content)
        
        # Replace URLs (but keep general structure for context)
        content = re.sub(url_pattern, '[URL_LINK]', content)
        
        # Replace potential company/personal names in signatures (basic heuristic)
        # Look for common signature patterns and replace proper nouns
        signature_patterns = [
            r'\n--\s*\n.*',  # Email signatures starting with --
            r'\nBest regards,.*',
            r'\nSincerely,.*',
            r'\nThanks,.*'
        ]
        
        for pattern in signature_patterns:
            content = re.sub(pattern, '\n[EMAIL_SIGNATURE]', content, flags=re.DOTALL)
        
        return content
    
    def _build_conversation_text(self, emails: List[EmailMetadata], user_email: str) -> str:
        """Build rich conversation text for LLM analysis with full content and temporal context"""
        conversation_parts = []
        email_map = {}  # Consistent email anonymization mapping
        
        for i, email in enumerate(emails):
            sender_type = "YOU" if user_email.lower() in email.sender.lower() else "INVESTOR"
            
            # Enhanced timestamp with day of week and time context
            timestamp_str = email.timestamp.strftime("%Y-%m-%d %H:%M (%A)")
            time_context = f"{email.day_of_week} {email.time_of_day}" if email.day_of_week and email.time_of_day else ""
            
            # Email header with rich context
            conversation_parts.append(f"=== EMAIL #{i+1} ===")
            conversation_parts.append(f"[{timestamp_str}] {sender_type}")
            if time_context:
                conversation_parts.append(f"Time Context: {time_context}")
            # Anonymize email addresses in headers
            sender_anon = self._anonymize_email_content(email.sender, email_map)
            recipient_anon = self._anonymize_email_content(email.recipient, email_map)
            subject_anon = self._anonymize_email_content(email.subject, email_map)
            
            conversation_parts.append(f"From: {sender_anon}")
            conversation_parts.append(f"To: {recipient_anon}")
            if email.cc:
                cc_anon = self._anonymize_email_content(email.cc, email_map)
                conversation_parts.append(f"CC: {cc_anon}")
            conversation_parts.append(f"Subject: {subject_anon}")
            
            # Response time context
            if email.response_time_hours is not None:
                if email.response_time_hours < 1:
                    response_time = f"{email.response_time_hours * 60:.0f} minutes"
                elif email.response_time_hours < 24:
                    response_time = f"{email.response_time_hours:.1f} hours"
                else:
                    response_time = f"{email.response_time_hours / 24:.1f} days"
                conversation_parts.append(f"Response Time: {response_time}")
            
            # Email content - use full body if available, otherwise snippet (anonymized)
            email_content = email.body_content if email.body_content else email.snippet
            if email_content:
                # Anonymize the email content before sending to OpenAI
                anonymized_content = self._anonymize_email_content(email_content, email_map)
                conversation_parts.append("Content:")
                conversation_parts.append(anonymized_content)
            else:
                conversation_parts.append("(No content available)")
            
            # Additional metadata
            metadata_parts = []
            if email.has_attachments:
                metadata_parts.append("Has attachments")
            if email.is_outbound:
                metadata_parts.append("Outbound email")
            if email.body_length > 0:
                metadata_parts.append(f"Length: {email.body_length} chars")
            
            if metadata_parts:
                conversation_parts.append(f"Metadata: {', '.join(metadata_parts)}")
            
            conversation_parts.append("")  # Separator between emails
        
        return "\n".join(conversation_parts)
    
    def _calculate_response_times(self, emails: List[EmailMetadata], user_email: str) -> List[float]:
        """Calculate response times in hours"""
        response_times = []
        
        for i in range(len(emails) - 1):
            current_email = emails[i]
            next_email = emails[i + 1]
            
            # Check if this is a user email followed by an investor reply
            if (user_email.lower() in current_email.sender.lower() and 
                user_email.lower() not in next_email.sender.lower()):
                
                time_diff = next_email.timestamp - current_email.timestamp
                hours = time_diff.total_seconds() / 3600
                response_times.append(hours)
        
        return response_times
    
    async def _analyze_investor_conversation(self, conversation_text: str, investor_email: str, company_context: str) -> Dict[str, Any]:
        """Use LLM to analyze investor conversation with rich temporal and content analysis"""
        try:
            prompt = f"""
            Analyze this detailed investor conversation for comprehensive fundraising insights. 
            Pay special attention to timing patterns, response behaviors, and content depth.
            
            Company Context: {company_context}
            Investor Email: {investor_email}
            
            DETAILED CONVERSATION WITH TEMPORAL CONTEXT:
            {conversation_text}
            
            Provide deep analysis and extract the following information in JSON format:
            {{
                "name": "investor full name if mentioned",
                "firm": "firm/company name if mentioned", 
                "relationship_stage": "cold/warm/engaged/interested/declined/deferred/closed",
                "sentiment_trend": "positive/neutral/negative",
                "engagement_level": "high/medium/low",
                "response_patterns": {{
                    "typical_response_time": "immediate/hours/days/slow",
                    "preferred_communication_times": "morning/afternoon/evening/weekend",
                    "response_consistency": "very_consistent/consistent/inconsistent"
                }},
                "conversation_dynamics": {{
                    "who_initiates_more": "investor/founder/balanced",
                    "email_length_preference": "brief/moderate/detailed",
                    "formality_level": "formal/professional/casual"
                }},
                "investment_signals": {{
                    "interest_level": "very_high/high/medium/low/none",
                    "due_diligence_requests": ["list", "of", "requests"],
                    "concerns_raised": ["list", "of", "concerns"],
                    "positive_indicators": ["list", "of", "positive", "signals"]
                }},
                "content_analysis": {{
                    "key_topics_discussed": ["topic1", "topic2", "topic3"],
                    "questions_asked_by_investor": ["question1", "question2"],
                    "materials_requested": ["material1", "material2"],
                    "follow_up_commitments": ["commitment1", "commitment2"]
                }},
                "temporal_insights": {{
                    "conversation_momentum": "accelerating/steady/slowing/stalled",
                    "urgency_indicators": ["urgent_sign1", "urgent_sign2"],
                    "seasonal_patterns": "any notable timing patterns"
                }},
                "next_action_recommended": {{
                    "primary_action": "specific recommended next step",
                    "timing": "immediate/within_24h/this_week/next_week",
                    "rationale": "why this action at this time"
                }},
                "relationship_temperature": "hot/warm/lukewarm/cold/frozen",
                "conversation_summary": "comprehensive summary highlighting key insights, timing patterns, and strategic recommendations"
            }}
            
            Focus on actionable insights that can help optimize the fundraising approach for this specific investor.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3,
                timeout=30.0  # 30 second timeout
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {}
                
        except Exception as e:
            print(f"LLM analysis failed for {investor_email}: {str(e)}")
            return {}
    
    async def _extract_timing_patterns_node(self, state: FundraisingState) -> FundraisingState:
        """Node 4: Extract optimal timing patterns for each investor"""
        try:
            state.current_step = "extracting_timing_patterns"
            
            timing_patterns = {}
            
            for investor_email, emails in state.thread_groups.items():
                try:
                    # Analyze reply patterns
                    reply_times = []
                    reply_days = []
                    
                    for email in emails:
                        if state.user_email.lower() not in email.sender.lower():  # Investor replied
                            # Parse timestamp if it's a string
                            if isinstance(email.timestamp, str):
                                try:
                                    dt = datetime.fromisoformat(email.timestamp.replace('Z', '+00:00'))
                                    reply_times.append(dt.hour)
                                    reply_days.append(dt.strftime("%A").lower())
                                except:
                                    continue
                            else:
                                reply_times.append(email.timestamp.hour)
                                reply_days.append(email.timestamp.strftime("%A").lower())
                    
                    # Find most common reply time and day
                    most_common_hour = max(set(reply_times), key=reply_times.count) if reply_times else 10
                    most_common_day = max(set(reply_days), key=reply_days.count) if reply_days else "tuesday"
                    
                    # Calculate average response delay
                    response_times = self._calculate_response_times(emails, state.user_email)
                    avg_response_hours = sum(response_times) / len(response_times) if response_times else 24
                    
                    timing_patterns[investor_email] = {
                        "preferred_hour": most_common_hour,
                        "preferred_day": most_common_day,
                        "avg_response_hours": avg_response_hours,
                        "total_replies": len(reply_times),
                        "response_rate": len(reply_times) / len(emails) if emails else 0
                    }
                    
                except Exception as e:
                    state.errors.append(f"Failed to analyze timing for {investor_email}: {str(e)}")
                    continue
            
            state.timing_patterns = timing_patterns
            
        except Exception as e:
            state.errors.append(f"Timing pattern extraction failed: {str(e)}")
        
        return state
    
    async def _analyze_strategy_effectiveness_node(self, state: FundraisingState) -> FundraisingState:
        """Node 5: Analyze which email strategies work best"""
        try:
            state.current_step = "analyzing_strategy_effectiveness"
            
            # This would analyze email content patterns vs response rates
            # For now, implement basic effectiveness scoring
            strategy_effectiveness = {}
            
            total_sent = sum(ctx.total_emails_sent for ctx in state.investor_contexts.values())
            total_replies = sum(ctx.total_replies_received for ctx in state.investor_contexts.values())
            
            overall_reply_rate = total_replies / total_sent if total_sent > 0 else 0
            
            strategy_effectiveness = {
                "overall_reply_rate": overall_reply_rate,
                "total_conversations": len(state.investor_contexts),
                "active_conversations": len([ctx for ctx in state.investor_contexts.values() 
                                           if ctx.relationship_stage in ["warm", "engaged", "interested"]]),
                "positive_sentiment_rate": len([ctx for ctx in state.investor_contexts.values() 
                                              if ctx.sentiment_trend == "positive"]) / len(state.investor_contexts) if state.investor_contexts else 0
            }
            
            state.strategy_effectiveness = strategy_effectiveness
            
        except Exception as e:
            state.errors.append(f"Strategy effectiveness analysis failed: {str(e)}")
        
        return state
    
    async def _generate_campaign_strategies_node(self, state: FundraisingState) -> FundraisingState:
        """Node 6: Generate personalized campaign strategies"""
        try:
            print(f"[FUNDRAISING ENGINE] Generating {len(state.investor_contexts)} campaign strategies...")
            state.current_step = "generating_campaign_strategies"

            campaign_strategies = []

            for idx, (investor_email, context) in enumerate(state.investor_contexts.items()):
                print(f"[FUNDRAISING ENGINE] Generating strategy {idx+1}/{len(state.investor_contexts)}: {investor_email}")
                try:
                    # Generate strategy based on context
                    strategy = await self._generate_investor_strategy(context, state.company_context)
                    if strategy:
                        campaign_strategies.append(strategy)
                        
                except Exception as e:
                    state.errors.append(f"Failed to generate strategy for {investor_email}: {str(e)}")
                    continue
            
            state.campaign_strategies = campaign_strategies
            
        except Exception as e:
            state.errors.append(f"Campaign strategy generation failed: {str(e)}")
        
        return state
    
    async def _generate_investor_strategy(self, context: InvestorContext, company_context: str) -> Optional[CampaignStrategy]:
        """Generate personalized strategy for an investor"""
        try:
            # Determine strategy type based on relationship stage
            strategy_type = self._determine_strategy_type(context)
            
            prompt = f"""
            Generate a highly personalized fundraising strategy for this investor based on comprehensive conversation analysis:
            
            Company Context: {company_context}
            
            DETAILED INVESTOR PROFILE:
            Basic Info:
            - Email: {context.email}
            - Name: {context.name}
            - Firm: {context.firm}
            - Relationship Stage: {context.relationship_stage}
            - Overall Sentiment: {context.sentiment_trend}
            
            Communication Analysis:
            - Last Contact: {context.last_contact_date}
            - Total Emails Exchanged: {context.total_emails_sent}
            - Reply Rate: {context.total_replies_received}/{context.total_emails_sent} = {(context.total_replies_received/context.total_emails_sent*100) if context.total_emails_sent > 0 else 0:.1f}%
            - Conversation Summary: {context.conversation_summary}
            
            Key Insights:
            - Primary Interests: {', '.join(context.key_interests)}
            - Questions They've Asked: {', '.join(context.questions_asked)}
            - Concerns/Objections: {', '.join(context.objections_raised)}
            - Materials They've Requested: {', '.join(context.materials_shared)}
            - Suggested Next Actions: {context.next_action_suggested}
            
            Strategy Context: {strategy_type}
            
            INSTRUCTIONS:
            Based on this rich context, create a personalized strategy that:
            1. References specific conversation history
            2. Addresses their stated interests and concerns
            3. Uses appropriate timing based on their response patterns
            4. Matches their communication style and preferences
            5. Provides clear value proposition aligned with their focus areas
            
            Generate:
            1. Personalized email draft (200-300 words) that references specific conversation points
            2. LinkedIn message (if relevant, 75-100 words)
            3. Detailed reasoning explaining why this approach will work
            4. Expected response rate based on historical patterns
            5. Optimal communication channel sequence
            6. Best timing for outreach (immediate/hours/days)
            
            Respond in JSON format:
            {{
                "email_draft": "highly personalized email that references specific conversation history and interests",
                "linkedin_message": "personalized linkedin message or empty if not recommended",
                "reasoning": "detailed explanation of why this strategy is optimal for this specific investor based on conversation patterns",
                "expected_response_rate": 0.5,
                "channel_sequence": ["email", "linkedin"],
                "optimal_timing": "immediate/within_6h/within_24h/within_week",
                "personalization_score": 8,
                "key_talking_points": ["point1", "point2", "point3"],
                "success_metrics": ["metric1", "metric2"]
            }}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.7,
                timeout=30.0  # 30 second timeout
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # Calculate recommended timing
                recommended_timing = datetime.now() + timedelta(days=1)
                if context.last_contact_date:
                    # Handle timezone-aware vs naive datetime comparison
                    now = datetime.now()
                    try:
                        if hasattr(context.last_contact_date, 'tzinfo') and context.last_contact_date.tzinfo is not None:
                            # Strip timezone from last_contact_date to match naive datetime.now()
                            last_contact = context.last_contact_date.replace(tzinfo=None)
                        else:
                            last_contact = context.last_contact_date
                        
                        days_since_contact = (now - last_contact).days
                        if days_since_contact < 7:
                            recommended_timing = datetime.now() + timedelta(days=7-days_since_contact)
                    except (TypeError, AttributeError):
                        # Fallback if timezone handling fails
                        recommended_timing = datetime.now() + timedelta(days=1)
                
                # Calculate better timing based on AI recommendation
                timing_map = {
                    "immediate": 0,
                    "within_6h": 0.25,
                    "within_24h": 1,
                    "within_week": 7
                }
                timing_days = timing_map.get(result.get("optimal_timing", "within_24h"), 1)
                recommended_timing = datetime.now() + timedelta(days=timing_days)
                
                strategy = CampaignStrategy(
                    investor_email=context.email,
                    strategy_type=strategy_type,
                    recommended_timing=recommended_timing,
                    email_draft=result.get("email_draft", ""),
                    linkedin_message=result.get("linkedin_message", ""),
                    reasoning=result.get("reasoning", ""),
                    confidence_score=result.get("personalization_score", 8) / 10.0,  # Convert to 0-1 scale
                    channel_sequence=result.get("channel_sequence", ["email"]),
                    expected_response_rate=result.get("expected_response_rate", 0.3)
                )
                
                return strategy
            
        except Exception as e:
            print(f"Strategy generation failed for {context.email}: {str(e)}")
        
        return None
    
    def _determine_strategy_type(self, context: InvestorContext) -> str:
        """Determine the appropriate strategy type based on context"""
        if context.relationship_stage == "deferred" and context.defer_until:
            return "follow_up"
        elif context.relationship_stage in ["cold", "unknown"]:
            return "cold_outreach"
        elif context.relationship_stage == "declined":
            return "re_engagement"
        elif context.total_replies_received == 0 and context.total_emails_sent > 0:
            return "re_engagement"
        elif context.relationship_stage in ["warm", "engaged", "interested"]:
            return "milestone_update"
        else:
            return "follow_up"
    
    def _calculate_response_times(self, emails: List[EmailMetadata], user_email: str) -> List[float]:
        """Calculate response times between sent emails and replies"""
        response_times = []
        
        # Sort emails by timestamp
        sorted_emails = sorted(emails, key=lambda e: e.timestamp)
        
        for i in range(len(sorted_emails) - 1):
            current_email = sorted_emails[i]
            next_email = sorted_emails[i + 1]
            
            # Check if current is from user and next is reply from investor
            if (user_email.lower() in current_email.sender.lower() and 
                user_email.lower() not in next_email.sender.lower()):
                
                try:
                    # Parse timestamps
                    if isinstance(current_email.timestamp, str):
                        current_dt = datetime.fromisoformat(current_email.timestamp.replace('Z', '+00:00'))
                    else:
                        current_dt = current_email.timestamp
                        
                    if isinstance(next_email.timestamp, str):
                        next_dt = datetime.fromisoformat(next_email.timestamp.replace('Z', '+00:00'))
                    else:
                        next_dt = next_email.timestamp
                    
                    # Calculate response time in hours
                    response_time_hours = (next_dt - current_dt).total_seconds() / 3600
                    response_times.append(response_time_hours)
                    
                except Exception:
                    continue  # Skip if timestamp parsing fails
        
        return response_times
    
    async def _generate_retrospective_node(self, state: FundraisingState) -> FundraisingState:
        """Node 7: Generate comprehensive retrospective report"""
        try:
            print(f"[FUNDRAISING ENGINE] Generating final retrospective report...")
            state.current_step = "generating_retrospective"

            report = await self._generate_comprehensive_report(state)
            state.retrospective_report = report
            
        except Exception as e:
            state.errors.append(f"Retrospective generation failed: {str(e)}")
        
        return state
    
    async def _generate_single_investor_report(self, state: FundraisingState) -> str:
        """Generate focused report for single investor relationship"""
        try:
            # Get the single investor context
            investor_email = list(state.investor_contexts.keys())[0]
            ctx = state.investor_contexts[investor_email]

            # Get timing patterns
            timing = state.timing_patterns.get(investor_email, {})

            # Get strategy if available
            strategy = None
            if state.campaign_strategies:
                strategy = state.campaign_strategies[0]

            # Build comprehensive investor profile
            prompt = f"""
            Generate a detailed, personalized investor relationship report for a SINGLE investor in markdown format.

            This is a focused analysis of ONE specific investor relationship, not a general campaign report.

            INVESTOR PROFILE:
            - Name: {ctx.name or "Unknown"}
            - Email: {ctx.email}
            - Firm: {ctx.firm or "Unknown"}
            - Relationship Stage: {ctx.relationship_stage}
            - Sentiment: {ctx.sentiment_trend}
            - Last Reply Sentiment: {ctx.last_reply_sentiment}

            ENGAGEMENT METRICS:
            - Total Emails Sent: {ctx.total_emails_sent}
            - Total Replies Received: {ctx.total_replies_received}
            - Reply Rate: {(ctx.total_replies_received / ctx.total_emails_sent * 100) if ctx.total_emails_sent > 0 else 0:.1f}%
            - Last Contact: {ctx.last_contact_date.strftime('%Y-%m-%d') if ctx.last_contact_date else 'Unknown'}
            - Average Response Time: {timing.get('avg_response_hours', 0):.1f} hours

            COMMUNICATION PATTERNS:
            - Preferred Day: {timing.get('preferred_day', 'Unknown')}
            - Preferred Hour: {timing.get('preferred_hour', 'Unknown')}:00
            - Response Rate: {timing.get('response_rate', 0):.1%}
            - Total Interactions: {timing.get('total_replies', 0)}

            INTERESTS & CONTEXT:
            - Key Interests: {', '.join(ctx.key_interests) if ctx.key_interests else 'None identified'}
            - Questions Asked: {', '.join(ctx.questions_asked) if ctx.questions_asked else 'None identified'}
            - Objections Raised: {', '.join(ctx.objections_raised) if ctx.objections_raised else 'None identified'}
            - Materials Shared: {', '.join(ctx.materials_shared) if ctx.materials_shared else 'None shared'}

            CONVERSATION SUMMARY:
            {ctx.conversation_summary}

            SUGGESTED NEXT ACTION:
            {ctx.next_action_suggested or 'No specific action suggested'}

            COMPANY CONTEXT:
            {state.company_context}

            Generate a comprehensive, actionable report with these sections:

            # 1. Investor Overview
            - Who they are, their firm, background
            - Current relationship status and temperature

            # 2. Relationship Analysis
            - Detailed analysis of the relationship progression
            - What stage they're at in the funnel
            - Sentiment analysis and what it means

            # 3. Communication Dynamics
            - How responsive they are
            - Their communication style and preferences
            - Best times to reach them and why
            - What type of content resonates

            # 4. Interest & Engagement Signals
            - What they've shown interest in
            - Positive signals and green flags
            - Concerns or objections they've raised
            - Questions they've asked (and what that reveals)

            # 5. What's Working
            - Specific tactics or approaches that have gotten good responses
            - Topics that generated engagement
            - Communication patterns that work

            # 6. What's Not Working
            - Missed opportunities or missteps
            - Topics that didn't resonate
            - Timing issues or communication gaps

            # 7. Strategic Recommendations
            - Immediate next steps (within 1 week)
            - Medium-term strategy (1-4 weeks)
            - Long-term relationship building (1-3 months)
            - Specific email/content recommendations

            # 8. Risk Assessment
            - Deal health: strong/moderate/weak/at risk
            - Red flags to watch for
            - Competitive threats or concerns

            # 9. Action Plan
            - Specific, numbered action items with timing
            - Who should do what and when
            - Success metrics to track

            Make this report:
            - Highly personalized and specific to THIS investor
            - Data-driven with specific examples and numbers
            - Actionable with clear next steps
            - Strategic with both short and long-term thinking
            - Professional but direct and honest about the relationship status

            Use actual details from the conversation summary and metrics. Be specific, not generic.
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2500,
                temperature=0.5,
                timeout=30.0
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"# Investor Relationship Report\n\n**Error generating report:** {str(e)}"

    async def _generate_comprehensive_report(self, state: FundraisingState) -> str:
        """Generate detailed retrospective report in markdown format"""
        try:
            # Prepare data for report
            total_investors = len(state.investor_contexts)
            total_emails_sent = sum(ctx.total_emails_sent for ctx in state.investor_contexts.values())
            total_replies = sum(ctx.total_replies_received for ctx in state.investor_contexts.values())
            reply_rate = (total_replies / total_emails_sent * 100) if total_emails_sent > 0 else 0

            # Check if this is a single investor analysis
            if total_investors == 1:
                # Generate focused single-investor report
                return await self._generate_single_investor_report(state)

            # Stage breakdown
            stage_counts = {}
            for ctx in state.investor_contexts.values():
                stage = ctx.relationship_stage
                stage_counts[stage] = stage_counts.get(stage, 0) + 1

            # Top performing strategies
            positive_sentiment = len([ctx for ctx in state.investor_contexts.values() if ctx.sentiment_trend == "positive"])

            prompt = f"""
            Generate a comprehensive fundraising retrospective report in markdown format.

            Data Summary:
            - Total Investors Contacted: {total_investors}
            - Total Emails Sent: {total_emails_sent}
            - Total Replies Received: {total_replies}
            - Overall Reply Rate: {reply_rate:.1f}%
            - Positive Sentiment: {positive_sentiment} investors

            Relationship Stages:
            {json.dumps(stage_counts, indent=2)}

            Company Context: {state.company_context}

            Generate a detailed report with these sections:
            1. Executive Summary
            2. Key Metrics
            3. What Worked
            4. What Didn't Work
            5. Investor Insights
            6. Timing Analysis
            7. Next Steps & Recommendations
            8. Action Items for Next Sprint

            Make it professional, data-driven, and actionable. Use specific numbers and insights.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.5,
                timeout=30.0  # 30 second timeout
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"# Fundraising Retrospective Report\n\n**Error generating report:** {str(e)}"

    def _extract_email_body(self, email_data: Dict[str, Any]) -> str:
        """Extract the email body content from Gmail API response."""
        try:
            def extract_text_from_part(part):
                """Recursively extract text from email parts."""
                body_text = ""
                
                if part.get("body", {}).get("data"):
                    # Decode base64 content
                    import base64
                    encoded_data = part["body"]["data"]
                    # Add padding if needed
                    missing_padding = len(encoded_data) % 4
                    if missing_padding:
                        encoded_data += '=' * (4 - missing_padding)
                    
                    decoded_data = base64.urlsafe_b64decode(encoded_data)
                    body_text = decoded_data.decode('utf-8', errors='ignore')
                
                # Handle multipart messages
                if part.get("parts"):
                    for subpart in part["parts"]:
                        subpart_text = extract_text_from_part(subpart)
                        if subpart_text:
                            body_text += "\n" + subpart_text
                
                return body_text
            
            payload = email_data.get("payload", {})
            body_content = extract_text_from_part(payload)
            
            # Clean up the text
            if body_content:
                # Remove excessive whitespace and clean up
                import re
                body_content = re.sub(r'\n\s*\n', '\n\n', body_content)
                body_content = body_content.strip()
            
            # If no body content found, use snippet as fallback
            if not body_content:
                body_content = email_data.get("snippet", "")
            
            return body_content
            
        except Exception as e:
            # Fallback to snippet if extraction fails
            return email_data.get("snippet", "")


# Factory function for easy instantiation
def get_fundraising_intelligence_engine() -> FundraisingIntelligenceEngine:
    """Get instance of the fundraising intelligence engine"""
    return FundraisingIntelligenceEngine()