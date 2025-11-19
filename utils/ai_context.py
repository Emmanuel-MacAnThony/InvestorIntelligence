"""
AI Context Engine for Fundraising Email Analysis
Optimized for fundraising teams to analyze investor email threads
"""

import os
import openai
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json


@dataclass
class EmailMessage:
    """Represents a single email in a thread."""

    sender: str
    recipient: str
    subject: str
    body: str
    timestamp: str
    is_from_team: bool = False


@dataclass
class ThreadAnalysis:
    """Results of AI analysis on email thread."""

    conversation_stage: (
        str  # cold_outreach, follow_up, due_diligence, negotiation, closed
    )
    investor_interest_level: str  # high, medium, low, unknown
    key_topics: List[str]
    pain_points: List[str]
    value_propositions_mentioned: List[str]
    next_actions: List[str]
    sentiment_score: float  # -1 to 1
    urgency_level: str  # high, medium, low
    investment_signals: List[str]
    concerns_raised: List[str]
    summary: str


class AIContextEngine:
    """AI-powered analysis engine for fundraising email threads."""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not found")

        self.client = openai.OpenAI(api_key=api_key)

    def analyze_thread(
        self, messages: List[EmailMessage], company_context: Optional[str] = None
    ) -> ThreadAnalysis:
        """
        Analyze an email thread for fundraising insights.

        Args:
            messages: List of email messages in chronological order
            company_context: Optional context about the company raising funds

        Returns:
            ThreadAnalysis with comprehensive insights
        """

        # Prepare thread context for AI
        thread_text = self._format_thread_for_analysis(messages)

        # Create fundraising-specific prompt
        system_prompt = self._get_fundraising_analysis_prompt()

        user_prompt = f"""
        CRITICAL: Analyze this conversation using SPECIFIC details from the actual messages.
        DO NOT provide generic analysis - extract CONCRETE information from what was actually said.

        BUSINESS CONTEXT: {company_context or "Professional business discussion"}

        FULL CONVERSATION TRANSCRIPT (READ EVERY MESSAGE):
        {thread_text}

        INSTRUCTIONS:
        1. Read EVERY message in the conversation above
        2. Extract SPECIFIC topics, concerns, and requests that were actually mentioned
        3. Quote or reference ACTUAL statements made in the messages
        4. Identify CONCRETE next actions based on what was discussed
        5. Base sentiment on ACTUAL language used, not assumptions

        Provide strategic analysis in JSON format with SPECIFIC, NON-GENERIC content:

        {{
            "conversation_stage": "based on actual conversation progression, not message count",
            "investor_interest_level": "based on actual engagement signals in messages",
            "key_topics": ["specific topic 1 they mentioned", "specific topic 2 discussed", "actual subject 3"],
            "pain_points": ["actual challenge 1 they raised", "specific concern 2 mentioned"],
            "value_propositions_mentioned": ["specific value 1 discussed", "actual proposition 2"],
            "next_actions": ["concrete action based on conversation", "specific follow-up mentioned"],
            "sentiment_score": 0.5,
            "urgency_level": "based on actual timeline/urgency mentioned",
            "investment_signals": ["specific signal 1 from messages", "actual indicator 2"],
            "concerns_raised": ["exact concern 1 they stated", "specific question 2 they asked"],
            "summary": "DETAILED summary referencing specific points from the conversation, actual topics discussed, and concrete next steps. Must be 2-3 sentences minimum with SPECIFIC details from the messages."
        }}

        REQUIREMENTS:
        - If they mentioned specific interests, list those exact interests (not "technology" but "AI capabilities" if that's what they said)
        - If they asked questions, include those actual questions in concerns_raised
        - If they requested materials, mention the specific materials in next_actions
        - The summary MUST reference actual conversation points, not generic descriptions
        - Use empty arrays [] if no specific information is available (don't make it up)

        EXAMPLES of what to DO:
        - "Interested in AI/ML capabilities" vs "Interested in technology" (GOOD vs BAD)
        - "Asked about burn rate and runway" vs "Interested in financials" (GOOD vs BAD)
        - "Requested pitch deck and latest metrics" vs "Requested materials" (GOOD vs BAD)
        """

        try:
            # Try GPT-4o-mini first (less restrictive filtering)
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",  # Less restrictive filtering
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.3,
                    max_tokens=1500,
                )
            except Exception as gpt4_error:
                # Fallback to original model
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo-16k",  # Fallback model
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.3,
                    max_tokens=1500,  # Reduced to leave room for input
                )

            # Get response content
            if not response.choices:
                raise ValueError("No choices in OpenAI response")

            choice = response.choices[0]
            message = choice.message

            # Check for content filter
            if choice.finish_reason == "content_filter":
                return self._create_fallback_analysis(messages)

            response_content = message.content
            if response_content:
                response_content = response_content.strip()
            else:
                raise ValueError("Empty response from OpenAI API")

            # Try to extract JSON if response contains extra text 2=aE[90{
            if response_content.startswith("```json"):
                # Extract JSON from markdown code block
                start = response_content.find("{")
                end = response_content.rfind("}") + 1
                if start != -1 and end != 0:
                    response_content = response_content[start:end]
            elif not response_content.startswith("{"):
                # Look for JSON object in the response
                start = response_content.find("{")
                end = response_content.rfind("}") + 1
                if start != -1 and end != 0:
                    response_content = response_content[start:end]
                else:
                    raise ValueError("No JSON object found in response")

            # Parse JSON response
            analysis_json = json.loads(response_content)

            return ThreadAnalysis(
                conversation_stage=analysis_json.get("conversation_stage", "unknown"),
                investor_interest_level=analysis_json.get(
                    "investor_interest_level", "unknown"
                ),
                key_topics=analysis_json.get("key_topics", []),
                pain_points=analysis_json.get("pain_points", []),
                value_propositions_mentioned=analysis_json.get(
                    "value_propositions_mentioned", []
                ),
                next_actions=analysis_json.get("next_actions", []),
                sentiment_score=float(analysis_json.get("sentiment_score", 0.0)),
                urgency_level=analysis_json.get("urgency_level", "medium"),
                investment_signals=analysis_json.get("investment_signals", []),
                concerns_raised=analysis_json.get("concerns_raised", []),
                summary=analysis_json.get("summary", "Analysis not available"),
            )

        except json.JSONDecodeError as e:
            # Return default analysis if JSON parsing fails
            return ThreadAnalysis(
                conversation_stage="unknown",
                investor_interest_level="unknown",
                key_topics=[],
                pain_points=[],
                value_propositions_mentioned=[],
                next_actions=["Review thread manually - AI analysis failed"],
                sentiment_score=0.0,
                urgency_level="medium",
                investment_signals=[],
                concerns_raised=[],
                summary=f"JSON parsing failed: {str(e)}",
            )
        except Exception as e:
            # Return default analysis if AI fails
            return ThreadAnalysis(
                conversation_stage="unknown",
                investor_interest_level="unknown",
                key_topics=[],
                pain_points=[],
                value_propositions_mentioned=[],
                next_actions=["Review thread manually - AI request failed"],
                sentiment_score=0.0,
                urgency_level="medium",
                investment_signals=[],
                concerns_raised=[],
                summary=f"AI analysis failed: {str(e)}",
            )

    def _smart_sanitize_for_context(self, content: str) -> str:
        """Smart sanitization that preserves business context while avoiding filters."""
        import re

        # Only sanitize the most problematic elements, keep business context

        # Replace email addresses but keep the domain context for business understanding
        content = re.sub(
            r"\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b",
            lambda m: f"ContactPerson@{m.group(2)}",
            content,
        )

        # Keep phone format but anonymize numbers
        content = re.sub(
            r"\b(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})\b", "XXX-XXX-XXXX", content
        )

        # Preserve financial context but anonymize specific amounts
        content = re.sub(
            r"\$(\d{1,3}(?:,\d{3})*)",
            lambda m: f"$[{len(m.group(1).replace(',', ''))}digits]",
            content,
        )
        content = re.sub(r"\b(\d+)([KMB])\b", r"[\1\2]", content)  # Keep 5M, 10K format

        # Keep company context but anonymize specific names
        content = re.sub(
            r"\b([A-Z][a-z]+)\s+(Inc\.?|LLC|Corp\.?)\b", r"[Company] \2", content
        )

        # Only remove obviously sensitive tokens (very long strings)
        content = re.sub(r"\b[A-Za-z0-9]{25,}\b", "[SecureToken]", content)

        # Keep most URLs but sanitize domain
        content = re.sub(r"(https?://)([^/\s]+)(.*)", r"\1[domain]\3", content)

        return content

    def _create_fallback_analysis(self, messages: List[EmailMessage]) -> ThreadAnalysis:
        """Create a basic analysis when AI content is filtered."""

        # Basic heuristics based on message patterns
        total_messages = len(messages)
        team_messages = sum(1 for msg in messages if msg.is_from_team)
        external_messages = total_messages - team_messages

        # Determine stage based on message count and patterns
        if total_messages <= 2:
            stage = "cold_outreach"
        elif total_messages <= 5:
            stage = "follow_up"
        else:
            stage = "due_diligence"

        # Determine interest based on response pattern
        if external_messages > team_messages:
            interest = "high"
        elif external_messages == team_messages:
            interest = "medium"
        else:
            interest = "low"

        # Basic sentiment based on message frequency
        sentiment = 0.3 if external_messages > 0 else 0.0

        # Look for investment keywords in a safe way
        all_text = " ".join([msg.body.lower() for msg in messages])
        investment_signals = []
        if "interested" in all_text or "meeting" in all_text:
            investment_signals.append("Interest expressed")
        if "call" in all_text or "schedule" in all_text:
            investment_signals.append("Meeting requested")
        if "deck" in all_text or "presentation" in all_text:
            investment_signals.append("Materials requested")

        return ThreadAnalysis(
            conversation_stage=stage,
            investor_interest_level=interest,
            key_topics=["Business discussion", "Investment opportunity"],
            pain_points=["Content filtered - unable to analyze specific concerns"],
            value_propositions_mentioned=["Business value proposition discussed"],
            next_actions=[
                f"Continue conversation - {total_messages} messages exchanged"
            ],
            sentiment_score=sentiment,
            urgency_level="medium",
            investment_signals=investment_signals,
            concerns_raised=[
                "Content privacy restrictions prevented detailed analysis"
            ],
            summary=f"Email thread with {total_messages} messages between team and external contact. Content was filtered for privacy, but basic interaction patterns suggest {interest} interest level at {stage} stage.",
        )

    def _format_thread_for_analysis(self, messages: List[EmailMessage]) -> str:
        """Format email thread for AI analysis with smart truncation."""
        if not messages:
            return "No messages found."

        # Smart selection: prioritize first, last, and most important messages
        selected_messages = []

        # Always include first message (context)
        if len(messages) > 0:
            selected_messages.append((0, messages[0]))

        # Always include last few messages (current state)
        recent_count = min(3, len(messages) - 1)
        for i in range(max(1, len(messages) - recent_count), len(messages)):
            if i not in [msg[0] for msg in selected_messages]:
                selected_messages.append((i, messages[i]))

        # If we have space, add some middle messages
        if len(selected_messages) < 6 and len(messages) > 4:
            middle_start = len(messages) // 3
            middle_end = min(middle_start + 2, len(messages) - recent_count)
            for i in range(middle_start, middle_end):
                if (
                    i not in [msg[0] for msg in selected_messages]
                    and len(selected_messages) < 6
                ):
                    selected_messages.append((i, messages[i]))

        # Sort by original order
        selected_messages.sort(key=lambda x: x[0])

        formatted = []
        total_chars = 0
        max_chars = 10000  # Slightly higher limit for 16k model

        for orig_idx, msg in selected_messages:
            sender_type = "TEAM" if msg.is_from_team else "INVESTOR"

            # Truncate very long email bodies but keep key information
            body = msg.body
            if len(body) > 1500:
                # Try to keep important parts (beginning and end)
                body = (
                    body[:800] + "\n[... middle content truncated ...]\n" + body[-500:]
                )

            # Use smart sanitization to preserve context
            body = self._smart_sanitize_for_context(body)
            sender = self._smart_sanitize_for_context(msg.sender)
            recipient = self._smart_sanitize_for_context(msg.recipient)

            # Present as conversation/dialogue instead of email format
            email_section = f"""
Message {orig_idx+1} ({sender_type}):
Speaker: {sender.split('@')[0] if '@' in sender else 'TeamMember' if msg.is_from_team else 'Contact'}
Topic: {self._smart_sanitize_for_context(msg.subject)}

"{body}"

---
"""

            if total_chars + len(email_section) > max_chars:
                formatted.append(
                    "\n[... some messages truncated to fit context window ...]"
                )
                break

            formatted.append(email_section)
            total_chars += len(email_section)

        # Add summary info
        if len(selected_messages) < len(messages):
            formatted.insert(
                0,
                f"[Business conversation with {len(messages)} total exchanges, showing {len(selected_messages)} key interactions]",
            )

        return "\n".join(formatted)

    def _get_fundraising_analysis_prompt(self) -> str:
        """Get system prompt optimized for business conversation analysis."""
        return """
You are a business strategist analyzing professional conversations to provide strategic insights.
Focus on communication patterns, engagement signals, and business development opportunities.

ANALYSIS FOCUS:
- Engagement signals (meeting requests, information requests, referral offers)
- Communication stage (initial contact, ongoing discussion, detailed exploration, negotiation)
- Business challenges or concerns mentioned
- Value propositions and business strengths discussed
- Strategic next steps for business development
- Urgency and timing indicators

ENGAGEMENT SIGNALS TO IDENTIFY:
- Requests for presentations, documentation, or detailed information
- Questions about team, market, or business model
- Introductions to other stakeholders or decision makers
- Discussion of timelines or processes
- Requests for references or case studies
- Mentions of specific criteria or requirements

COMMUNICATION STAGES:
- Initial: First contact, general interest exploration
- Ongoing: Continued dialogue after initial contact
- Detailed: In-depth questions, document requests, reference checks
- Advanced: Specific discussions, timeline coordination
- Concluded: Process completed or definitively ended

BUSINESS CONCERNS TO TRACK:
- Market opportunity questions
- Competitive positioning discussions
- Team capability inquiries
- Business model validation needs
- Timing or readiness considerations

Provide strategic insights for effective business relationship development.
"""
