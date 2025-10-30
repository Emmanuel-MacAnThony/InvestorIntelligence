"""
Fundraising Strategy Generator
Generates actionable follow-up strategies and email templates for fundraising teams
"""

import os
import openai
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from .ai_context import ThreadAnalysis, EmailMessage
import json


@dataclass
class EmailStrategy:
    """Represents a suggested email strategy."""
    strategy_type: str  # follow_up, meeting_request, information_sharing, introduction, etc.
    priority: str  # high, medium, low
    timing: str  # immediate, within_24h, within_week, etc.
    subject_line: str
    email_body: str
    talking_points: List[str]
    attachments_needed: List[str]
    success_metrics: List[str]
    rationale: str


@dataclass
class FundraisingStrategy:
    """Complete fundraising strategy for a thread."""
    primary_strategy: EmailStrategy
    alternative_strategies: List[EmailStrategy]
    next_steps: List[str]
    red_flags: List[str]
    opportunities: List[str]
    relationship_temperature: str  # hot, warm, cold
    recommended_timeline: str


class FundraisingStrategyGenerator:
    """Generates fundraising-specific strategies and email templates."""
    
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    def generate_strategy(self, analysis: ThreadAnalysis, messages: List[EmailMessage], 
                         company_context: Optional[str] = None) -> FundraisingStrategy:
        """
        Generate comprehensive fundraising strategy based on thread analysis.
        
        Args:
            analysis: AI analysis of the email thread
            messages: Original email messages
            company_context: Optional company context
            
        Returns:
            Complete fundraising strategy with recommendations
        """
        
        # Create context for strategy generation
        thread_summary = self._create_thread_summary(analysis, messages)
        
        # Generate primary strategy
        primary_strategy = self._generate_primary_strategy(analysis, thread_summary, company_context)
        
        # Generate alternative strategies
        alternative_strategies = self._generate_alternative_strategies(analysis, thread_summary, company_context)
        
        # Generate strategic insights
        strategic_insights = self._generate_strategic_insights(analysis, thread_summary)
        
        return FundraisingStrategy(
            primary_strategy=primary_strategy,
            alternative_strategies=alternative_strategies,
            next_steps=strategic_insights["next_steps"],
            red_flags=strategic_insights["red_flags"],
            opportunities=strategic_insights["opportunities"],
            relationship_temperature=self._assess_relationship_temperature(analysis),
            recommended_timeline=strategic_insights["timeline"]
        )
    
    def _generate_primary_strategy(self, analysis: ThreadAnalysis, thread_summary: str, 
                                 company_context: Optional[str] = None) -> EmailStrategy:
        """Generate the primary recommended strategy."""
        
        system_prompt = self._get_strategy_generation_prompt()
        
        user_prompt = f"""
        Generate the PRIMARY email strategy for this fundraising conversation.
        
        THREAD ANALYSIS:
        - Stage: {analysis.conversation_stage}
        - Interest Level: {analysis.investor_interest_level}
        - Sentiment: {analysis.sentiment_score}
        - Urgency: {analysis.urgency_level}
        - Key Topics: {', '.join(analysis.key_topics)}
        - Investment Signals: {', '.join(analysis.investment_signals)}
        - Concerns: {', '.join(analysis.concerns_raised)}
        
        THREAD SUMMARY:
        {thread_summary}
        
        COMPANY CONTEXT:
        {company_context or "No additional context provided"}
        
        Focus on the MOST EFFECTIVE strategy to move this conversation forward. 
        Return JSON in this format:
        {{
            "strategy_type": "follow_up|meeting_request|information_sharing|introduction|due_diligence_response",
            "priority": "high|medium|low",
            "timing": "immediate|within_24h|within_week|next_week",
            "subject_line": "Compelling subject line",
            "email_body": "Professional email body with specific talking points",
            "talking_points": ["point1", "point2", ...],
            "attachments_needed": ["attachment1", "attachment2", ...],
            "success_metrics": ["metric1", "metric2", ...],
            "rationale": "Why this strategy is recommended"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo-16k",  # Use same model as analysis
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4,
                max_tokens=1200  # Reduced for efficiency
            )
            
            strategy_json = json.loads(response.choices[0].message.content)
            
            return EmailStrategy(
                strategy_type=strategy_json.get("strategy_type", "follow_up"),
                priority=strategy_json.get("priority", "medium"),
                timing=strategy_json.get("timing", "within_24h"),
                subject_line=strategy_json.get("subject_line", "Follow-up"),
                email_body=strategy_json.get("email_body", ""),
                talking_points=strategy_json.get("talking_points", []),
                attachments_needed=strategy_json.get("attachments_needed", []),
                success_metrics=strategy_json.get("success_metrics", []),
                rationale=strategy_json.get("rationale", "")
            )
            
        except Exception as e:
            # Fallback strategy
            return self._create_fallback_strategy(analysis)
    
    def _generate_alternative_strategies(self, analysis: ThreadAnalysis, thread_summary: str, 
                                       company_context: Optional[str] = None) -> List[EmailStrategy]:
        """Generate 2-3 alternative strategies."""
        
        system_prompt = """
        You are a fundraising expert generating ALTERNATIVE email strategies.
        Focus on different approaches that could also be effective.
        Keep strategies concise but actionable.
        """
        
        user_prompt = f"""
        Generate 2-3 ALTERNATIVE email strategies for this fundraising conversation.
        These should be different approaches from the primary strategy.
        
        THREAD ANALYSIS:
        - Stage: {analysis.conversation_stage}
        - Interest Level: {analysis.investor_interest_level}
        - Key Topics: {', '.join(analysis.key_topics)}
        
        THREAD SUMMARY:
        {thread_summary}
        
        Return JSON array of strategies:
        [
            {{
                "strategy_type": "type",
                "priority": "priority",
                "timing": "timing",
                "subject_line": "subject",
                "email_body": "body",
                "talking_points": ["point1", "point2"],
                "attachments_needed": [],
                "success_metrics": ["metric1"],
                "rationale": "rationale"
            }}
        ]
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                max_tokens=1000
            )
            
            strategies_json = json.loads(response.choices[0].message.content)
            
            alternatives = []
            for strategy_data in strategies_json:
                alternatives.append(EmailStrategy(
                    strategy_type=strategy_data.get("strategy_type", "follow_up"),
                    priority=strategy_data.get("priority", "medium"),
                    timing=strategy_data.get("timing", "within_week"),
                    subject_line=strategy_data.get("subject_line", ""),
                    email_body=strategy_data.get("email_body", ""),
                    talking_points=strategy_data.get("talking_points", []),
                    attachments_needed=strategy_data.get("attachments_needed", []),
                    success_metrics=strategy_data.get("success_metrics", []),
                    rationale=strategy_data.get("rationale", "")
                ))
            
            return alternatives
            
        except Exception:
            return []
    
    def _generate_strategic_insights(self, analysis: ThreadAnalysis, thread_summary: str) -> Dict[str, Any]:
        """Generate high-level strategic insights."""
        
        system_prompt = """
        You are a senior fundraising advisor providing strategic insights.
        Focus on actionable next steps, potential risks, and opportunities.
        """
        
        user_prompt = f"""
        Provide strategic insights for this fundraising conversation:
        
        ANALYSIS:
        {analysis.summary}
        
        THREAD SUMMARY:
        {thread_summary}
        
        Return JSON:
        {{
            "next_steps": ["step1", "step2", "step3"],
            "red_flags": ["flag1", "flag2"],
            "opportunities": ["opp1", "opp2"],
            "timeline": "suggested timeline for next contact"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=600
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception:
            return {
                "next_steps": ["Review conversation manually", "Plan follow-up"],
                "red_flags": [],
                "opportunities": [],
                "timeline": "within 1 week"
            }
    
    def _create_thread_summary(self, analysis: ThreadAnalysis, messages: List[EmailMessage]) -> str:
        """Create a concise summary of the thread for context."""
        
        recent_messages = messages[-3:] if len(messages) > 3 else messages
        
        summary_parts = [
            f"Conversation stage: {analysis.conversation_stage}",
            f"Interest level: {analysis.investor_interest_level}",
            f"Total messages: {len(messages)}",
            f"Recent activity: {len(recent_messages)} messages"
        ]
        
        if analysis.key_topics:
            summary_parts.append(f"Main topics: {', '.join(analysis.key_topics[:3])}")
        
        if analysis.investment_signals:
            summary_parts.append(f"Investment signals: {', '.join(analysis.investment_signals[:2])}")
        
        return "; ".join(summary_parts)
    
    def _assess_relationship_temperature(self, analysis: ThreadAnalysis) -> str:
        """Assess the relationship temperature based on analysis."""
        
        if analysis.investor_interest_level == "high" and analysis.sentiment_score > 0.3:
            return "hot"
        elif analysis.investor_interest_level == "medium" or analysis.sentiment_score > 0:
            return "warm"
        else:
            return "cold"
    
    def _create_fallback_strategy(self, analysis: ThreadAnalysis) -> EmailStrategy:
        """Create a safe fallback strategy when AI generation fails."""
        
        return EmailStrategy(
            strategy_type="follow_up",
            priority="medium",
            timing="within_24h",
            subject_line="Following up on our conversation",
            email_body="Thank you for your time. I wanted to follow up on our recent conversation and see if you have any additional questions.",
            talking_points=["Express gratitude", "Ask for feedback", "Offer additional information"],
            attachments_needed=[],
            success_metrics=["Response received", "Meeting scheduled"],
            rationale="Safe follow-up approach when analysis is unclear"
        )
    
    def _get_strategy_generation_prompt(self) -> str:
        """Get system prompt for strategy generation."""
        return """
You are an expert fundraising strategist helping startups raise capital effectively.
Your goal is to generate specific, actionable email strategies that move investor conversations forward.

STRATEGY TYPES TO CONSIDER:
- follow_up: Continue conversation momentum
- meeting_request: Request specific meetings (pitch, due diligence, partner intro)
- information_sharing: Share relevant updates, metrics, or materials
- introduction: Request introductions to other investors or advisors
- due_diligence_response: Respond to specific investor questions or requests

TIMING GUIDELINES:
- immediate: Send within 2 hours (high urgency)
- within_24h: Send same or next business day (standard follow-up)
- within_week: Send within 3-5 days (warm follow-up)
- next_week: Schedule for following week (planned approach)

FUNDRAISING BEST PRACTICES:
- Always include specific value propositions
- Reference previous conversation points
- Create clear next steps
- Show momentum and traction
- Address concerns proactively
- Keep emails concise but substantive
- Include relevant social proof
- Create urgency when appropriate

EMAIL TONE:
- Professional but personable
- Confident but not arrogant
- Specific and data-driven
- Forward-looking and optimistic

Focus on strategies that have the highest probability of advancing the fundraising process.
"""


def generate_fundraising_strategy(analysis: ThreadAnalysis, messages: List[EmailMessage], 
                                company_context: Optional[str] = None) -> FundraisingStrategy:
    """
    Convenience function to generate fundraising strategy.
    
    Args:
        analysis: Thread analysis from AI engine
        messages: Original email messages
        company_context: Optional company context
        
    Returns:
        Complete fundraising strategy
    """
    generator = FundraisingStrategyGenerator()
    return generator.generate_strategy(analysis, messages, company_context)