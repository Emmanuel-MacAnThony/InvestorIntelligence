"""
Report Generator for Fundraising Analysis
Creates downloadable text reports as an alternative to Slack integration
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from .ai_context import ThreadAnalysis
from .strategy_generator import FundraisingStrategy, EmailStrategy


class ReportGenerator:
    """Generates downloadable text reports for fundraising analysis."""
    
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        # Create reports directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_analysis_report(self, analysis_data: Dict[str, Any], 
                               strategy: FundraisingStrategy,
                               thread_url: Optional[str] = None) -> str:
        """
        Generate comprehensive analysis report as text file.
        
        Args:
            analysis_data: Complete analysis data from email analyzer
            strategy: Generated fundraising strategy
            thread_url: Optional link to the email thread
            
        Returns:
            Path to the generated report file
        """
        
        try:
            # Generate report content
            report_content = self._build_text_report(analysis_data, strategy, thread_url)
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            thread_id = analysis_data.get("thread_id", "unknown")
            filename = f"fundraising_analysis_{thread_id}_{timestamp}.txt"
            filepath = os.path.join(self.output_dir, filename)
            
            # Write report to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            print(f"Analysis report generated: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"Error generating analysis report: {e}")
            return ""
    
    def _build_text_report(self, analysis_data: Dict[str, Any], 
                         strategy: FundraisingStrategy,
                         thread_url: Optional[str] = None) -> str:
        """Build comprehensive text report content."""
        
        analysis = analysis_data.get("analysis")
        metadata = analysis_data.get("metadata", {})
        
        # Report header
        report_lines = [
            "=" * 80,
            "FUNDRAISING EMAIL THREAD ANALYSIS REPORT",
            "=" * 80,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Thread ID: {analysis_data.get('thread_id', 'N/A')}",
            ""
        ]
        
        if thread_url:
            report_lines.extend([
                f"Thread URL: {thread_url}",
                ""
            ])
        
        # Executive Summary
        report_lines.extend([
            "EXECUTIVE SUMMARY",
            "-" * 40,
            f"Interest Level: {analysis.investor_interest_level.upper()}",
            f"Conversation Stage: {analysis.conversation_stage.replace('_', ' ').title()}",
            f"Relationship Temperature: {strategy.relationship_temperature.upper()}",
            f"Sentiment Score: {analysis.sentiment_score:.2f} (-1 to +1 scale)",
            f"Urgency Level: {analysis.urgency_level.upper()}",
            "",
            f"Summary: {analysis.summary}",
            ""
        ])
        
        # Thread Statistics
        if metadata:
            report_lines.extend([
                "THREAD STATISTICS",
                "-" * 40,
                f"Total Messages: {metadata.get('total_messages', 0)}",
                f"Team Messages: {metadata.get('team_messages', 0)}",
                f"External Messages: {metadata.get('external_messages', 0)}",
                f"Conversation Span: {metadata.get('conversation_span_days', 0)} days",
                f"Last Sender: {'Team' if metadata.get('last_sender_is_team') else 'External'}",
                f"Team Participants: {', '.join(metadata.get('team_participants', []))}",
                f"External Participants: {', '.join(metadata.get('external_participants', []))}",
                ""
            ])
        
        # Investment Signals
        if analysis.investment_signals:
            report_lines.extend([
                "INVESTMENT SIGNALS DETECTED",
                "-" * 40
            ])
            for signal in analysis.investment_signals:
                report_lines.append(f"• {signal}")
            report_lines.append("")
        
        # Concerns Raised
        if analysis.concerns_raised:
            report_lines.extend([
                "CONCERNS RAISED BY INVESTOR",
                "-" * 40
            ])
            for concern in analysis.concerns_raised:
                report_lines.append(f"• {concern}")
            report_lines.append("")
        
        # Key Topics
        if analysis.key_topics:
            report_lines.extend([
                "KEY DISCUSSION TOPICS",
                "-" * 40
            ])
            for topic in analysis.key_topics:
                report_lines.append(f"• {topic}")
            report_lines.append("")
        
        # Value Propositions Mentioned
        if analysis.value_propositions_mentioned:
            report_lines.extend([
                "VALUE PROPOSITIONS MENTIONED",
                "-" * 40
            ])
            for vp in analysis.value_propositions_mentioned:
                report_lines.append(f"• {vp}")
            report_lines.append("")
        
        # Strategic Analysis
        report_lines.extend([
            "STRATEGIC ANALYSIS",
            "-" * 40,
            f"Recommended Timeline: {strategy.recommended_timeline}",
            ""
        ])
        
        # Opportunities
        if strategy.opportunities:
            report_lines.extend([
                "OPPORTUNITIES IDENTIFIED",
                "-" * 20
            ])
            for opp in strategy.opportunities:
                report_lines.append(f"• {opp}")
            report_lines.append("")
        
        # Red Flags
        if strategy.red_flags:
            report_lines.extend([
                "RED FLAGS / RISKS",
                "-" * 20
            ])
            for flag in strategy.red_flags:
                report_lines.append(f"• {flag}")
            report_lines.append("")
        
        # Next Steps
        if strategy.next_steps:
            report_lines.extend([
                "RECOMMENDED NEXT STEPS",
                "-" * 20
            ])
            for step in strategy.next_steps:
                report_lines.append(f"• {step}")
            report_lines.append("")
        
        # Primary Email Strategy
        report_lines.extend([
            "PRIMARY EMAIL STRATEGY",
            "=" * 40,
            f"Strategy Type: {strategy.primary_strategy.strategy_type.replace('_', ' ').title()}",
            f"Priority: {strategy.primary_strategy.priority.upper()}",
            f"Timing: {strategy.primary_strategy.timing.replace('_', ' ').title()}",
            "",
            f"Subject Line: {strategy.primary_strategy.subject_line}",
            "",
            "Email Body:",
            "-" * 15,
            strategy.primary_strategy.email_body,
            ""
        ])
        
        # Key Talking Points
        if strategy.primary_strategy.talking_points:
            report_lines.extend([
                "KEY TALKING POINTS:",
                "-" * 20
            ])
            for point in strategy.primary_strategy.talking_points:
                report_lines.append(f"• {point}")
            report_lines.append("")
        
        # Attachments Needed
        if strategy.primary_strategy.attachments_needed:
            report_lines.extend([
                "ATTACHMENTS NEEDED:",
                "-" * 20
            ])
            for attachment in strategy.primary_strategy.attachments_needed:
                report_lines.append(f"• {attachment}")
            report_lines.append("")
        
        # Success Metrics
        if strategy.primary_strategy.success_metrics:
            report_lines.extend([
                "SUCCESS METRICS:",
                "-" * 20
            ])
            for metric in strategy.primary_strategy.success_metrics:
                report_lines.append(f"• {metric}")
            report_lines.append("")
        
        # Strategy Rationale
        report_lines.extend([
            "STRATEGY RATIONALE:",
            "-" * 20,
            strategy.primary_strategy.rationale,
            ""
        ])
        
        # Alternative Strategies
        if strategy.alternative_strategies:
            report_lines.extend([
                "ALTERNATIVE STRATEGIES",
                "=" * 40
            ])
            
            for i, alt_strategy in enumerate(strategy.alternative_strategies, 1):
                report_lines.extend([
                    f"Alternative {i}: {alt_strategy.strategy_type.replace('_', ' ').title()}",
                    "-" * 30,
                    f"Priority: {alt_strategy.priority.upper()}",
                    f"Timing: {alt_strategy.timing.replace('_', ' ').title()}",
                    f"Subject: {alt_strategy.subject_line}",
                    "",
                    "Email Body:",
                    alt_strategy.email_body,
                    "",
                    f"Rationale: {alt_strategy.rationale}",
                    ""
                ])
        
        # Footer
        report_lines.extend([
            "=" * 80,
            "End of Fundraising Analysis Report",
            f"Generated by TwoLions Investor Intelligence Platform",
            f"Report ID: {analysis_data.get('thread_id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "=" * 80
        ])
        
        return "\n".join(report_lines)
    
    def generate_quick_summary(self, analysis: ThreadAnalysis) -> str:
        """Generate a quick summary for display purposes."""
        return f"""
📊 QUICK ANALYSIS SUMMARY
Interest: {analysis.investor_interest_level.upper()}
Stage: {analysis.conversation_stage.replace('_', ' ').title()}
Sentiment: {analysis.sentiment_score:.2f}
Urgency: {analysis.urgency_level.upper()}

{analysis.summary}
"""


def generate_fundraising_report(analysis_data: Dict[str, Any], 
                              strategy: FundraisingStrategy,
                              thread_url: Optional[str] = None,
                              output_dir: str = "reports") -> str:
    """
    Convenience function to generate fundraising analysis report.
    
    Args:
        analysis_data: Complete analysis from email analyzer
        strategy: Generated fundraising strategy
        thread_url: Optional thread URL
        output_dir: Directory to save reports
        
    Returns:
        Path to generated report file
    """
    generator = ReportGenerator(output_dir)
    return generator.generate_analysis_report(analysis_data, strategy, thread_url)