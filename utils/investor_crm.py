"""
Investor CRM Module
Manages investor profiles in Airtable and provides relationship health tracking
"""

import os
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from .airtable_client import get_airtable_client
from .ai_context import ThreadAnalysis
from openai import OpenAI


class InvestorCRM:
    """Manages investor profiles and relationship health tracking"""

    def __init__(self):
        """Initialize Airtable connection"""
        self.client = get_airtable_client()
        self.base_id = os.getenv("campaigns_base_id", "appEwtde6ov22a2TS")

        # Get the Investors table ID by name
        self.table_id = self._get_investors_table_id()

        if not self.table_id:
            raise ValueError("Could not find 'Investors' table in Airtable base")

    def _get_investors_table_id(self) -> Optional[str]:
        """Get Investors table ID from base"""
        try:
            tables = self.client.get_tables(self.base_id)
            for table in tables:
                if table["name"] == "Investors":
                    return table["id"]
            return None
        except:
            return None

    def save_analysis_to_crm(
        self,
        analysis_result: Dict[str, Any],
        thread_data: Dict[str, Any],
        user_email: str
    ) -> Dict[str, Any]:
        """
        Save or update investor profile from thread analysis

        Args:
            analysis_result: Complete analysis from analyze_fundraising_thread
            thread_data: Thread metadata (sender, recipient, subject, etc.)
            user_email: The user's email address

        Returns:
            Dict with 'created', 'updated', 'investor_name', 'investor_email'
        """
        try:
            print(f"[CRM DEBUG] Starting save_analysis_to_crm")
            print(f"[CRM DEBUG] Thread data: {thread_data}")
            print(f"[CRM DEBUG] User email: {user_email}")

            # Extract investor email (the person who is NOT the user)
            investor_email = self._extract_investor_email(thread_data, user_email)
            # Normalize email for consistency
            investor_email = investor_email.lower().strip() if investor_email else None
            print(f"[CRM DEBUG] Extracted investor email: {investor_email}")

            if not investor_email:
                print(f"[CRM DEBUG] ERROR: Could not identify investor email")
                return {"error": "Could not identify investor email"}

            # Extract investor name
            investor_name = self._extract_investor_name(thread_data, investor_email)
            print(f"[CRM DEBUG] Extracted investor name: {investor_name}")

            # Get analysis object
            analysis = analysis_result.get("analysis")
            metadata = analysis_result.get("metadata", {})
            print(f"[CRM DEBUG] Got analysis object: {type(analysis)}")

            # Check if investor already exists
            existing = self.get_investor_by_email(investor_email)
            print(f"[CRM DEBUG] Existing investor check: {existing is not None}")

            if existing:
                # Update existing profile
                print(f"[CRM DEBUG] Updating existing investor: {existing['id']}")
                updated_data = self._build_update_data(
                    existing, analysis, metadata, thread_data
                )
                print(f"[CRM DEBUG] Update data fields: {list(updated_data.keys())}")

                update_result = self.client.update_record(self.base_id, self.table_id, existing['id'], updated_data)
                print(f"[CRM DEBUG] Update result: {update_result}")

                return {
                    "updated": True,
                    "created": False,
                    "investor_name": investor_name,
                    "investor_email": investor_email
                }
            else:
                # Create new profile
                print(f"[CRM DEBUG] Creating new investor profile")
                new_data = self._build_new_profile_data(
                    investor_email, investor_name, analysis, metadata, thread_data
                )
                print(f"[CRM DEBUG] New data fields: {list(new_data.keys())}")
                print(f"[CRM DEBUG] New data values: {new_data}")

                create_result = self.client.create_record(self.base_id, self.table_id, new_data)
                print(f"[CRM DEBUG] Create result: {create_result}")

                return {
                    "created": True,
                    "updated": False,
                    "investor_name": investor_name,
                    "investor_email": investor_email
                }

        except Exception as e:
            print(f"[CRM DEBUG] EXCEPTION: {str(e)}")
            import traceback
            print(f"[CRM DEBUG] Traceback: {traceback.format_exc()}")
            return {"error": f"Failed to save to CRM: {str(e)}"}

    def get_investor_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get investor profile by email (case-insensitive)"""
        try:
            # Normalize email for consistent lookup
            email_normalized = email.lower().strip()

            # Use case-insensitive search
            formula = f"LOWER({{email}})='{email_normalized}'"
            result = self.client.get_records(
                self.base_id,
                self.table_id,
                filter_by_formula=formula
            )

            records = result.get("records", [])
            if records:
                return records[0]
            return None
        except Exception as e:
            return None

    def get_all_investors(self, status: str = "Active") -> List[Dict[str, Any]]:
        """Get all investors, optionally filtered by status"""
        try:
            if status:
                formula = f"{{status}}='{status}'"
            else:
                formula = None

            all_records = []
            offset = None

            # Paginate through all records
            while True:
                result = self.client.get_records(
                    self.base_id,
                    self.table_id,
                    filter_by_formula=formula,
                    offset=offset,
                    page_size=100
                )

                records = result.get("records", [])
                all_records.extend(records)

                offset = result.get("offset")
                if not offset:
                    break

            # Sort by health score descending
            all_records.sort(key=lambda x: x.get('fields', {}).get('health_score', 0), reverse=True)
            return all_records

        except Exception as e:
            return []

    def get_investors_by_health(self, min_score: int, max_score: int) -> List[Dict[str, Any]]:
        """Get investors filtered by health score range"""
        try:
            formula = f"AND({{health_score}}>={min_score}, {{health_score}}<={max_score})"

            all_records = []
            offset = None

            while True:
                result = self.client.get_records(
                    self.base_id,
                    self.table_id,
                    filter_by_formula=formula,
                    offset=offset
                )

                records = result.get("records", [])
                all_records.extend(records)

                offset = result.get("offset")
                if not offset:
                    break

            all_records.sort(key=lambda x: x.get('fields', {}).get('health_score', 0), reverse=True)
            return all_records

        except Exception as e:
            return []

    def get_investors_by_stage(self, stage: str) -> List[Dict[str, Any]]:
        """Get investors filtered by stage"""
        try:
            formula = f"{{stage}}='{stage}'"

            all_records = []
            offset = None

            while True:
                result = self.client.get_records(
                    self.base_id,
                    self.table_id,
                    filter_by_formula=formula,
                    offset=offset
                )

                records = result.get("records", [])
                all_records.extend(records)

                offset = result.get("offset")
                if not offset:
                    break

            all_records.sort(key=lambda x: x.get('fields', {}).get('health_score', 0), reverse=True)
            return all_records

        except Exception as e:
            return []

    def get_needs_attention(self) -> List[Dict[str, Any]]:
        """Get investors that need attention (custom alert logic)"""
        try:
            all_investors = self.get_all_investors()
            needs_attention = []

            for record in all_investors:
                fields = record.get('fields', {})
                alerts = self._generate_alerts_for_investor(fields)

                if alerts:
                    # Add alerts to the record for display
                    record['alerts'] = alerts
                    needs_attention.append(record)

            return needs_attention
        except Exception as e:
            return []

    def calculate_health_score(self, fields: Dict[str, Any]) -> int:
        """
        Calculate health score (0-100) based on investor data
        Uses simple rules, no LLM needed
        """
        score = 50  # Start at neutral

        # 1. Recency (30 points)
        last_contact = fields.get('last_contact_date')
        if last_contact:
            try:
                last_contact_dt = datetime.fromisoformat(last_contact) if isinstance(last_contact, str) else last_contact
                days_since = (datetime.now() - last_contact_dt).days

                if days_since == 0:
                    score += 30
                elif days_since <= 3:
                    score += 20
                elif days_since <= 7:
                    score += 10
                elif days_since <= 14:
                    score += 0
                elif days_since <= 30:
                    score -= 10
                else:
                    score -= 30
            except:
                pass

        # 2. Response rate (20 points)
        reply_rate = fields.get('reply_rate', 0)
        if reply_rate:
            score += int(reply_rate * 20)

        # 3. Response speed (20 points)
        avg_response_hours = fields.get('avg_response_hours', 999)
        if avg_response_hours < 4:
            score += 20
        elif avg_response_hours < 24:
            score += 10
        elif avg_response_hours < 72:
            score += 0
        else:
            score -= 10

        # 4. Sentiment (15 points)
        sentiment_map = {
            'Positive': 15,
            'Neutral': 0,
            'Negative': -15
        }
        score += sentiment_map.get(fields.get('sentiment'), 0)

        # 5. Stage (15 points)
        stage_map = {
            'Cold Outreach': 5,
            'Follow Up': 10,
            'Engaged': 15,
            'Due Diligence': 20,
            'Negotiation': 18,
            'Closed Won': 25,
            'Closed Lost': -20
        }
        score += stage_map.get(fields.get('stage'), 0)

        return max(0, min(100, score))

    def _generate_alerts_for_investor(self, fields: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate alerts for an investor based on their data"""
        alerts = []

        # Alert 1: No reply when normally fast
        avg_response_hours = fields.get('avg_response_hours', 999)
        last_contact = fields.get('last_contact_date')

        if last_contact and avg_response_hours < 24:
            try:
                last_contact_dt = datetime.fromisoformat(last_contact) if isinstance(last_contact, str) else last_contact
                days_since = (datetime.now() - last_contact_dt).days

                if days_since > 7:
                    alerts.append({
                        'type': 'no_reply',
                        'priority': 'high',
                        'message': f"No reply in {days_since} days (usually {avg_response_hours:.0f}h)"
                    })
            except:
                pass

        # Alert 2: Sentiment dropped
        sentiment = fields.get('sentiment')
        if sentiment == 'Negative':
            alerts.append({
                'type': 'sentiment_drop',
                'priority': 'medium',
                'message': 'Sentiment is negative - relationship at risk'
            })

        # Alert 3: Getting hot (opportunity!)
        health_score = fields.get('health_score', 0)
        trending = fields.get('trending')

        if health_score > 80 and trending == 'Up':
            alerts.append({
                'type': 'hot_lead',
                'priority': 'high',
                'message': f"Score jumped to {health_score} - strike now!"
            })

        # Alert 4: Going cold
        if health_score < 40 and fields.get('status') == 'Active':
            alerts.append({
                'type': 'going_cold',
                'priority': 'medium',
                'message': f"Score dropped to {health_score} - relationship at risk"
            })

        # Alert 5: Long silence
        if last_contact:
            try:
                last_contact_dt = datetime.fromisoformat(last_contact) if isinstance(last_contact, str) else last_contact
                days_since = (datetime.now() - last_contact_dt).days

                if days_since > 14 and fields.get('status') == 'Active':
                    alerts.append({
                        'type': 'long_silence',
                        'priority': 'medium',
                        'message': f"{days_since} days since last contact"
                    })
            except:
                pass

        return alerts

    def _extract_investor_email(self, thread_data: Dict[str, Any], user_email: str) -> Optional[str]:
        """Extract investor email from thread data"""
        sender = thread_data.get('sender', '')
        recipient = thread_data.get('recipient', '')

        # Clean emails
        sender_clean = self._clean_email_address(sender)
        user_clean = self._clean_email_address(user_email)

        # If sender is user, investor is recipient
        if sender_clean.lower() == user_clean.lower():
            return self._clean_email_address(recipient)
        else:
            return sender_clean

    def _extract_investor_name(self, thread_data: Dict[str, Any], investor_email: str) -> str:
        """Extract investor name from thread data"""
        sender = thread_data.get('sender', '')
        recipient = thread_data.get('recipient', '')

        # Find which one contains the investor email and extract name
        if investor_email.lower() in sender.lower():
            return self._extract_name_from_email_field(sender)
        elif investor_email.lower() in recipient.lower():
            return self._extract_name_from_email_field(recipient)

        # Fallback: use email prefix
        return investor_email.split('@')[0].replace('.', ' ').title()

    def _extract_name_from_email_field(self, email_field: str) -> str:
        """Extract name from 'Name <email>' format"""
        # Match "Name <email@domain.com>"
        match = re.search(r'^([^<]+)<', email_field)
        if match:
            return match.group(1).strip()

        # Fallback
        email = self._clean_email_address(email_field)
        return email.split('@')[0].replace('.', ' ').title()

    def _clean_email_address(self, email_str: str) -> str:
        """Extract clean email address from header string"""
        match = re.search(r'<([^>]+)>', email_str)
        if match:
            return match.group(1)

        match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', email_str)
        if match:
            return match.group(1)

        return email_str

    def _build_new_profile_data(
        self,
        email: str,
        name: str,
        analysis: Any,
        metadata: Dict[str, Any],
        thread_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build data for new investor profile"""

        # Calculate metrics
        total_emails_sent = metadata.get('team_messages', 0)
        total_replies = metadata.get('external_messages', 0)
        reply_rate = (total_replies / total_emails_sent) if total_emails_sent > 0 else 0

        # Format dates for Airtable (Date fields need YYYY-MM-DD format only, no time)
        first_contact = metadata.get('first_message_date')
        last_contact = metadata.get('last_message_date')

        # Convert ISO datetime strings to date-only strings
        if first_contact:
            try:
                if isinstance(first_contact, str):
                    first_contact = datetime.fromisoformat(first_contact.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                elif isinstance(first_contact, datetime):
                    first_contact = first_contact.strftime('%Y-%m-%d')
            except:
                first_contact = None

        if last_contact:
            try:
                if isinstance(last_contact, str):
                    last_contact = datetime.fromisoformat(last_contact.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                elif isinstance(last_contact, datetime):
                    last_contact = last_contact.strftime('%Y-%m-%d')
            except:
                last_contact = None

        # Build profile data
        profile = {
            'email': email,
            'name': name,
            'stage': self._map_stage(analysis.conversation_stage) if analysis else 'Follow Up',
            'sentiment': self._map_sentiment(analysis.sentiment_score) if analysis else 'Neutral',
            'total_emails_sent': total_emails_sent,
            'total_replies_received': total_replies,
            'reply_rate': reply_rate,
            'interests': '\n'.join(analysis.key_topics) if analysis and analysis.key_topics else '',
            'concerns': '\n'.join(analysis.concerns_raised) if analysis and analysis.concerns_raised else '',
            'conversation_summary': analysis.summary if analysis else '',
            'next_action': '\n'.join(analysis.next_actions) if analysis and analysis.next_actions else '',
            'thread_ids': thread_data.get('thread_id', ''),  # Store as plain string, not list format
            'status': 'Active',
            'trending': 'Stable'
        }

        # Add date fields only if they have valid values
        if first_contact:
            profile['first_contact_date'] = first_contact
        if last_contact:
            profile['last_contact_date'] = last_contact

        # last_analyzed_date should be date only too
        profile['last_analyzed_date'] = datetime.now().strftime('%Y-%m-%d')

        # Calculate health score
        profile['health_score'] = self.calculate_health_score(profile)

        return profile

    def _build_update_data(
        self,
        existing: Dict[str, Any],
        analysis: Any,
        metadata: Dict[str, Any],
        thread_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build data for updating existing investor profile"""

        existing_fields = existing.get('fields', {})

        # Get previous health score for trending
        previous_health = existing_fields.get('health_score', 50)

        # Format last contact date for Airtable (YYYY-MM-DD format only)
        last_contact = metadata.get('last_message_date')
        if last_contact:
            try:
                if isinstance(last_contact, str):
                    last_contact = datetime.fromisoformat(last_contact.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                elif isinstance(last_contact, datetime):
                    last_contact = last_contact.strftime('%Y-%m-%d')
            except:
                last_contact = None

        # Handle thread IDs - append new ones to existing
        new_thread_id = thread_data.get('thread_id', '')
        existing_thread_ids = existing_fields.get('thread_ids', '')

        # Parse existing thread IDs
        if existing_thread_ids:
            # Clean up any bracket/quote formatting
            cleaned = existing_thread_ids.replace("[", "").replace("]", "").replace("'", "").replace('"', '')
            existing_ids = [tid.strip() for tid in cleaned.split(",") if tid.strip()]
        else:
            existing_ids = []

        # Add new thread ID if not already present
        if new_thread_id and new_thread_id not in existing_ids:
            existing_ids.append(new_thread_id)

        # Store as comma-separated string
        updated_thread_ids = ','.join(existing_ids)

        # Update data
        update = {
            'stage': self._map_stage(analysis.conversation_stage) if analysis else existing_fields.get('stage'),
            'sentiment': self._map_sentiment(analysis.sentiment_score) if analysis else existing_fields.get('sentiment'),
            'last_analyzed_date': datetime.now().strftime('%Y-%m-%d'),
            'total_emails_sent': metadata.get('team_messages', existing_fields.get('total_emails_sent', 0)),
            'total_replies_received': metadata.get('external_messages', existing_fields.get('total_replies_received', 0)),
            'interests': '\n'.join(analysis.key_topics) if analysis and analysis.key_topics else existing_fields.get('interests', ''),
            'concerns': '\n'.join(analysis.concerns_raised) if analysis and analysis.concerns_raised else existing_fields.get('concerns', ''),
            'conversation_summary': analysis.summary if analysis else existing_fields.get('conversation_summary', ''),
            'next_action': '\n'.join(analysis.next_actions) if analysis and analysis.next_actions else existing_fields.get('next_action', ''),
            'thread_ids': updated_thread_ids,  # Add updated thread IDs
        }

        # Add last_contact_date only if valid
        if last_contact:
            update['last_contact_date'] = last_contact

        # Recalculate reply rate
        if update['total_emails_sent'] > 0:
            update['reply_rate'] = update['total_replies_received'] / update['total_emails_sent']

        # Recalculate health score
        merged_data = {**existing_fields, **update}
        new_health = self.calculate_health_score(merged_data)
        update['health_score'] = new_health

        # Determine trending
        if new_health > previous_health + 5:
            update['trending'] = 'Up'
        elif new_health < previous_health - 5:
            update['trending'] = 'Down'
        else:
            update['trending'] = 'Stable'

        return update

    def _map_stage(self, conversation_stage: str) -> str:
        """Map analysis stage to CRM stage"""
        stage_map = {
            'cold_outreach': 'Cold Outreach',
            'follow_up': 'Follow Up',
            'due_diligence': 'Due Diligence',
            'negotiation': 'Negotiation',
            'closed': 'Closed Won'
        }
        return stage_map.get(conversation_stage, 'Follow Up')

    def _map_sentiment(self, sentiment_score: float) -> str:
        """Map sentiment score to CRM sentiment"""
        if sentiment_score > 0.3:
            return 'Positive'
        elif sentiment_score < -0.3:
            return 'Negative'
        else:
            return 'Neutral'

    def generate_monthly_intelligence_report(
        self,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        include_all_time: bool = False,
        company_context: str = ""
    ) -> Dict[str, Any]:
        """
        Generate comprehensive monthly pipeline intelligence report

        Args:
            date_range: Optional tuple of (start_date, end_date) for filtering
            include_all_time: If True, includes all investors regardless of date
            company_context: Context about the company for AI analysis

        Returns:
            Dict with 'report' (markdown), 'metrics' (dict), 'visualizations' (dict)
        """
        try:
            print("[MONTHLY REPORT] Starting report generation...")

            # Get all active investors
            all_investors = self.get_all_investors(status=None)  # Get all statuses

            if not all_investors:
                return {
                    "error": "No investors found in CRM",
                    "report": "# Monthly Intelligence Report\n\nNo investor data available.",
                    "metrics": {},
                    "visualizations": {}
                }

            # Filter by date range if specified
            if date_range and not include_all_time:
                start_date, end_date = date_range
                filtered_investors = []
                for inv in all_investors:
                    last_contact = inv.get('fields', {}).get('last_contact_date')
                    if last_contact:
                        try:
                            contact_dt = datetime.fromisoformat(last_contact) if isinstance(last_contact, str) else last_contact
                            if start_date <= contact_dt <= end_date:
                                filtered_investors.append(inv)
                        except:
                            continue
                investors = filtered_investors if filtered_investors else all_investors
            else:
                investors = all_investors

            print(f"[MONTHLY REPORT] Analyzing {len(investors)} investors...")

            # Calculate comprehensive metrics
            metrics = self._calculate_pipeline_metrics(investors)

            # Generate visualizations data
            visualizations = self._prepare_visualization_data(investors)

            # Generate AI-powered insights and recommendations
            ai_insights = self._generate_ai_insights(investors, metrics, company_context)

            # Build the comprehensive report
            report_markdown = self._build_intelligence_report_markdown(
                metrics,
                visualizations,
                ai_insights,
                date_range
            )

            print("[MONTHLY REPORT] Report generation complete!")

            return {
                "report": report_markdown,
                "metrics": metrics,
                "visualizations": visualizations,
                "ai_insights": ai_insights,
                "success": True
            }

        except Exception as e:
            print(f"[MONTHLY REPORT] Error: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return {
                "error": f"Failed to generate report: {str(e)}",
                "report": f"# Monthly Intelligence Report\n\n**Error:** {str(e)}",
                "metrics": {},
                "visualizations": {},
                "success": False
            }

    def _calculate_pipeline_metrics(self, investors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive pipeline metrics"""

        total_count = len(investors)

        # Health score distribution
        hot_leads = [i for i in investors if i.get('fields', {}).get('health_score', 0) >= 70]
        warm_leads = [i for i in investors if 40 <= i.get('fields', {}).get('health_score', 0) < 70]
        cold_leads = [i for i in investors if i.get('fields', {}).get('health_score', 0) < 40]

        # Trending analysis
        trending_up = [i for i in investors if i.get('fields', {}).get('trending') == 'Up']
        trending_down = [i for i in investors if i.get('fields', {}).get('trending') == 'Down']

        # Stage distribution
        stage_breakdown = {}
        for inv in investors:
            stage = inv.get('fields', {}).get('stage', 'Unknown')
            stage_breakdown[stage] = stage_breakdown.get(stage, 0) + 1

        # Sentiment analysis
        positive_sentiment = [i for i in investors if i.get('fields', {}).get('sentiment') == 'Positive']
        neutral_sentiment = [i for i in investors if i.get('fields', {}).get('sentiment') == 'Neutral']
        negative_sentiment = [i for i in investors if i.get('fields', {}).get('sentiment') == 'Negative']

        # Engagement metrics
        total_emails_sent = sum(i.get('fields', {}).get('total_emails_sent', 0) for i in investors)
        total_replies = sum(i.get('fields', {}).get('total_replies_received', 0) for i in investors)
        overall_reply_rate = (total_replies / total_emails_sent) if total_emails_sent > 0 else 0

        # Average response time
        response_times = [i.get('fields', {}).get('avg_response_hours', 0) for i in investors if i.get('fields', {}).get('avg_response_hours', 0) > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        # Activity metrics
        active_count = len([i for i in investors if i.get('fields', {}).get('status') == 'Active'])
        paused_count = len([i for i in investors if i.get('fields', {}).get('status') == 'Paused'])
        closed_count = len([i for i in investors if i.get('fields', {}).get('status') == 'Closed'])

        # Top performers (high health, high engagement)
        top_performers = sorted(
            [i for i in investors if i.get('fields', {}).get('health_score', 0) >= 70],
            key=lambda x: (
                x.get('fields', {}).get('health_score', 0),
                x.get('fields', {}).get('reply_rate', 0)
            ),
            reverse=True
        )[:10]

        # At-risk relationships (declining health, long silence)
        at_risk = []
        for inv in investors:
            fields = inv.get('fields', {})
            health = fields.get('health_score', 0)
            trending = fields.get('trending')
            last_contact = fields.get('last_contact_date')

            is_at_risk = False
            risk_reasons = []

            if health < 40:
                is_at_risk = True
                risk_reasons.append(f"Low health score ({health})")

            if trending == 'Down':
                is_at_risk = True
                risk_reasons.append("Health declining")

            if last_contact:
                try:
                    last_dt = datetime.fromisoformat(last_contact) if isinstance(last_contact, str) else last_contact
                    days_since = (datetime.now() - last_dt).days
                    if days_since > 14:
                        is_at_risk = True
                        risk_reasons.append(f"{days_since} days silence")
                except:
                    pass

            if is_at_risk:
                at_risk.append({
                    'investor': inv,
                    'risk_reasons': risk_reasons
                })

        # Sort by health score (lowest first for at-risk)
        at_risk.sort(key=lambda x: x['investor'].get('fields', {}).get('health_score', 0))

        return {
            'total_investors': total_count,
            'hot_leads_count': len(hot_leads),
            'warm_leads_count': len(warm_leads),
            'cold_leads_count': len(cold_leads),
            'trending_up_count': len(trending_up),
            'trending_down_count': len(trending_down),
            'stage_breakdown': stage_breakdown,
            'positive_sentiment_count': len(positive_sentiment),
            'neutral_sentiment_count': len(neutral_sentiment),
            'negative_sentiment_count': len(negative_sentiment),
            'total_emails_sent': total_emails_sent,
            'total_replies_received': total_replies,
            'overall_reply_rate': overall_reply_rate,
            'avg_response_time_hours': avg_response_time,
            'active_count': active_count,
            'paused_count': paused_count,
            'closed_count': closed_count,
            'top_performers': top_performers,
            'at_risk_investors': at_risk,
            'hot_leads': hot_leads,
            'trending_up': trending_up,
            'trending_down': trending_down
        }

    def _prepare_visualization_data(self, investors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare data for visualizations"""

        # Health score distribution histogram data
        health_scores = [i.get('fields', {}).get('health_score', 0) for i in investors]

        # Stage funnel data
        stage_order = ['Cold Outreach', 'Follow Up', 'Engaged', 'Due Diligence', 'Negotiation', 'Closed Won']
        stage_counts = {}
        for stage in stage_order:
            stage_counts[stage] = len([i for i in investors if i.get('fields', {}).get('stage') == stage])

        # Sentiment pie chart data
        sentiment_counts = {
            'Positive': len([i for i in investors if i.get('fields', {}).get('sentiment') == 'Positive']),
            'Neutral': len([i for i in investors if i.get('fields', {}).get('sentiment') == 'Neutral']),
            'Negative': len([i for i in investors if i.get('fields', {}).get('sentiment') == 'Negative'])
        }

        # Reply rate distribution
        reply_rates = [i.get('fields', {}).get('reply_rate', 0) for i in investors if i.get('fields', {}).get('reply_rate') is not None]

        return {
            'health_scores': health_scores,
            'stage_funnel': stage_counts,
            'sentiment_distribution': sentiment_counts,
            'reply_rates': reply_rates
        }

    def _generate_ai_insights(
        self,
        investors: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        company_context: str
    ) -> Dict[str, Any]:
        """Use AI to generate strategic insights and recommendations"""

        try:
            openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            # Prepare investor summaries for AI
            investor_summaries = []
            for inv in investors[:50]:  # Limit to top 50 to avoid token limits
                fields = inv.get('fields', {})
                investor_summaries.append({
                    'name': fields.get('name', 'Unknown'),
                    'firm': fields.get('firm', ''),
                    'stage': fields.get('stage', 'Unknown'),
                    'health_score': fields.get('health_score', 0),
                    'sentiment': fields.get('sentiment', 'Unknown'),
                    'trending': fields.get('trending', 'Stable'),
                    'reply_rate': fields.get('reply_rate', 0),
                    'interests': fields.get('interests', ''),
                    'concerns': fields.get('concerns', ''),
                    'last_contact': fields.get('last_contact_date', 'Unknown')
                })

            prompt = f"""
            CRITICAL: Generate a HIGHLY SPECIFIC, CONTEXT-AWARE pipeline intelligence report using ACTUAL investor data.
            DO NOT provide generic fundraising advice - reference SPECIFIC investors by name and their actual situations.

            Company Context: {company_context}

            PIPELINE METRICS:
            - Total Investors: {metrics['total_investors']}
            - Hot Leads (70-100): {metrics['hot_leads_count']}
            - Warm Leads (40-69): {metrics['warm_leads_count']}
            - Cold Leads (0-39): {metrics['cold_leads_count']}
            - Trending Up: {metrics['trending_up_count']}
            - Trending Down: {metrics['trending_down_count']}
            - Overall Reply Rate: {metrics['overall_reply_rate']:.1%}
            - Avg Response Time: {metrics['avg_response_time_hours']:.1f} hours

            STAGE BREAKDOWN:
            {json.dumps(metrics['stage_breakdown'], indent=2)}

            SENTIMENT DISTRIBUTION:
            - Positive: {metrics['positive_sentiment_count']}
            - Neutral: {metrics['neutral_sentiment_count']}
            - Negative: {metrics['negative_sentiment_count']}

            ACTUAL INVESTOR DATA (reference these specific investors in your analysis):
            {json.dumps(investor_summaries[:20], indent=2)}

            INSTRUCTIONS:
            1. Reference SPECIFIC investors by NAME when discussing patterns
            2. Use ACTUAL health scores, stages, and trends from the data above
            3. Identify patterns based on THIS data, not generic assumptions
            4. Provide actionable recommendations for SPECIFIC investors
            5. When mentioning concerns, reference which specific investors have those concerns

            Generate comprehensive analysis in JSON format:
            {{
                "executive_summary": "2-3 sentence overview using actual metrics and naming 2-3 specific investors by name",
                "key_wins": ["Specific investor name at Firm showing positive trend because...", "Another named investor engaged because..."],
                "areas_of_concern": ["Specific investor name - reason based on their actual data", "Named investor - specific issue from their profile"],
                "pipeline_bottlenecks": ["Stage X has Y investors stuck - name 2-3 examples and their specific situation"],
                "success_patterns": ["What specific named investors did that worked", "Actual interest patterns from the data"],
                "failure_patterns": ["Which named investors aren't responding and why (based on their data)", "Specific patterns in cold leads"],
                "top_10_priorities": [
                    {{"investor": "ACTUAL investor name from list", "action": "specific action based on their stage/interests/concerns", "timing": "when based on last contact", "rationale": "why now based on their actual data"}},
                    ...
                ],
                "strategic_recommendations": [
                    {{"recommendation": "specific action for named investor(s)", "expected_impact": "what metric will improve", "priority": "high/medium/low"}},
                    ...
                ],
                "risk_mitigation": ["Specific named investor needs X by date Y because..."],
                "next_30_days_plan": [
                    {{"action": "what", "who": "specific named investors", "when": "specific timing", "success_metric": "measurable outcome"}}
                ]
            }}

            REQUIREMENTS:
            - Name at least 5-10 specific investors throughout the analysis
            - Use actual health scores and metrics from the data
            - Reference actual stages and trends for each named investor
            - Base recommendations on real interests/concerns from the investor profiles
            - No generic advice - everything should be specific to this actual pipeline

            EXAMPLES of what to DO:
            - "John Smith at Acme VC (health: 85, trending up) is highly engaged" (GOOD - specific)
            - "Jane Doe at Beta Fund (health: 25, 14 days silence) needs immediate follow-up" (GOOD - actual data)
            - "Investors in engaged stage need attention" (BAD - generic, no names)
            - "Follow up with warm leads" (BAD - not specific)
            """

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2500,
                temperature=0.5,
                timeout=30.0
            )

            result_text = response.choices[0].message.content.strip()

            # Extract JSON from response
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"error": "Failed to parse AI insights"}

        except Exception as e:
            print(f"[AI INSIGHTS] Error: {str(e)}")
            return {
                "error": f"Failed to generate AI insights: {str(e)}",
                "executive_summary": "AI analysis unavailable",
                "key_wins": [],
                "areas_of_concern": [],
                "top_10_priorities": [],
                "strategic_recommendations": []
            }

    def _build_intelligence_report_markdown(
        self,
        metrics: Dict[str, Any],
        visualizations: Dict[str, Any],
        ai_insights: Dict[str, Any],
        date_range: Optional[Tuple[datetime, datetime]]
    ) -> str:
        """Build comprehensive markdown report"""

        # Header
        report_date = datetime.now().strftime("%B %Y")
        if date_range:
            start, end = date_range
            report_date = f"{start.strftime('%B %d')} - {end.strftime('%B %d, %Y')}"

        markdown = f"""# 📊 Monthly Pipeline Intelligence Report
**Generated:** {datetime.now().strftime("%B %d, %Y at %I:%M %p")}
**Period:** {report_date}

---

## 🎯 Executive Summary

{ai_insights.get('executive_summary', 'Analysis in progress...')}

**Pipeline Health at a Glance:**
- 🔥 **Hot Leads:** {metrics['hot_leads_count']} investors (70-100 health score)
- ⚡ **Warm Leads:** {metrics['warm_leads_count']} investors (40-69 health score)
- ❄️ **Cold Leads:** {metrics['cold_leads_count']} investors (0-39 health score)
- 📈 **Trending Up:** {metrics['trending_up_count']} investors gaining momentum
- 📉 **Trending Down:** {metrics['trending_down_count']} investors losing momentum

---

## 📈 Key Metrics

### Engagement Performance
- **Total Investors Tracked:** {metrics['total_investors']}
- **Active Conversations:** {metrics['active_count']}
- **Overall Reply Rate:** {metrics['overall_reply_rate']:.1%}
- **Average Response Time:** {metrics['avg_response_time_hours']:.1f} hours
- **Total Emails Sent:** {metrics['total_emails_sent']}
- **Total Replies Received:** {metrics['total_replies_received']}

### Sentiment Analysis
- 😊 **Positive:** {metrics['positive_sentiment_count']} ({metrics['positive_sentiment_count']/metrics['total_investors']*100:.0f}%)
- 😐 **Neutral:** {metrics['neutral_sentiment_count']} ({metrics['neutral_sentiment_count']/metrics['total_investors']*100:.0f}%)
- 😔 **Negative:** {metrics['negative_sentiment_count']} ({metrics['negative_sentiment_count']/metrics['total_investors']*100:.0f}%)

### Stage Distribution
"""

        # Add stage breakdown
        for stage, count in metrics['stage_breakdown'].items():
            pct = (count / metrics['total_investors'] * 100) if metrics['total_investors'] > 0 else 0
            markdown += f"- **{stage}:** {count} ({pct:.0f}%)\n"

        markdown += """
---

## 🏆 Top 10 Performers (Hot Leads to Strike Now)

"""

        # Add top performers
        for i, inv in enumerate(metrics['top_performers'][:10], 1):
            fields = inv.get('fields', {})
            name = fields.get('name', 'Unknown')
            firm = fields.get('firm', '')
            health = fields.get('health_score', 0)
            stage = fields.get('stage', 'Unknown')
            trending = fields.get('trending', 'Stable')

            trending_emoji = "📈" if trending == "Up" else "📉" if trending == "Down" else "➡️"

            markdown += f"""### {i}. {name} {trending_emoji}
- **Firm:** {firm}
- **Health Score:** {health}/100
- **Stage:** {stage}
- **Reply Rate:** {fields.get('reply_rate', 0):.0%}
- **Last Contact:** {fields.get('last_contact_date', 'Unknown')}

"""

        markdown += """---

## ⚠️ At-Risk Relationships (Need Immediate Attention)

"""

        # Add at-risk investors
        for i, risk_data in enumerate(metrics['at_risk_investors'][:10], 1):
            inv = risk_data['investor']
            reasons = risk_data['risk_reasons']
            fields = inv.get('fields', {})
            name = fields.get('name', 'Unknown')
            health = fields.get('health_score', 0)

            markdown += f"""### {i}. {name} (Health: {health}/100)
**Risk Factors:**
"""
            for reason in reasons:
                markdown += f"- ⚠️ {reason}\n"

            markdown += f"**Last Contact:** {fields.get('last_contact_date', 'Unknown')}\n\n"

        markdown += """---

## 💡 Strategic Insights

### ✅ What's Working
"""

        for win in ai_insights.get('key_wins', ['Analysis in progress...']):
            markdown += f"- ✅ {win}\n"

        markdown += """
### ⚠️ Areas of Concern
"""

        for concern in ai_insights.get('areas_of_concern', ['Analysis in progress...']):
            markdown += f"- ⚠️ {concern}\n"

        markdown += """
### 🎯 Success Patterns
"""

        for pattern in ai_insights.get('success_patterns', ['Analysis in progress...']):
            markdown += f"- {pattern}\n"

        markdown += """
### 🚫 Failure Patterns
"""

        for pattern in ai_insights.get('failure_patterns', ['Analysis in progress...']):
            markdown += f"- {pattern}\n"

        markdown += """
---

## 🎯 Top 10 Action Priorities

"""

        # Add top priorities
        for i, priority in enumerate(ai_insights.get('top_10_priorities', [])[:10], 1):
            markdown += f"""### {i}. {priority.get('investor', 'Unknown')}
- **Action:** {priority.get('action', 'TBD')}
- **Timing:** {priority.get('timing', 'TBD')}
- **Rationale:** {priority.get('rationale', 'TBD')}

"""

        markdown += """---

## 📋 Strategic Recommendations

"""

        for i, rec in enumerate(ai_insights.get('strategic_recommendations', []), 1):
            priority = rec.get('priority', 'medium').upper()
            priority_emoji = "🔴" if priority == "HIGH" else "🟡" if priority == "MEDIUM" else "🟢"

            markdown += f"""### {i}. {priority_emoji} {rec.get('recommendation', 'TBD')}
- **Expected Impact:** {rec.get('expected_impact', 'TBD')}
- **Priority:** {priority}

"""

        markdown += """---

## 📅 Next 30 Days Action Plan

"""

        for i, action in enumerate(ai_insights.get('next_30_days_plan', []), 1):
            markdown += f"""### Week {(i-1)//2 + 1} Action {i}
- **What:** {action.get('action', 'TBD')}
- **Who:** {action.get('who', 'TBD')}
- **When:** {action.get('when', 'TBD')}
- **Success Metric:** {action.get('success_metric', 'TBD')}

"""

        markdown += """---

## 📊 Data Insights & Benchmarks

### Pipeline Health Indicators
"""

        # Calculate some benchmarks
        healthy_rate = (metrics['hot_leads_count'] / metrics['total_investors'] * 100) if metrics['total_investors'] > 0 else 0
        positive_sentiment_rate = (metrics['positive_sentiment_count'] / metrics['total_investors'] * 100) if metrics['total_investors'] > 0 else 0

        markdown += f"""- **Healthy Pipeline Rate:** {healthy_rate:.1f}% (Target: >30%)
- **Positive Sentiment Rate:** {positive_sentiment_rate:.1f}% (Target: >50%)
- **Reply Rate:** {metrics['overall_reply_rate']:.1%} (Target: >40%)
- **Response Time:** {metrics['avg_response_time_hours']:.1f}h (Target: <48h)

"""

        markdown += """---

*Report generated by Investor Intelligence AI. Data reflects current state of CRM records.*
"""

        return markdown

    def log_sent_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Log a sent email and update investor CRM.

        Args:
            email_data: Dict with investor_email, subject, body, sent_at, message_id, etc.

        Returns:
            Dict with 'success' bool and any error messages
        """
        try:
            investor_email = email_data.get("investor_email", "").lower().strip()

            if not investor_email:
                return {"error": "No investor email provided"}

            # Update investor record if exists
            investor = self.get_investor_by_email(investor_email)

            if investor:
                fields = investor.get("fields", {})

                # Increment email count
                current_sent = fields.get("total_emails_sent", 0)

                # Update last contact date
                update_data = {
                    "total_emails_sent": current_sent + 1,
                    "last_contact_date": email_data.get("sent_at", datetime.now().isoformat())
                }

                # Recalculate health score
                updated_fields = fields.copy()
                updated_fields.update(update_data)
                new_health_score = self.calculate_health_score(updated_fields)
                update_data["health_score"] = new_health_score

                # Update record
                result = self.client.update_record(
                    self.base_id,
                    self.table_id,
                    investor["id"],
                    update_data
                )

                if "error" in result:
                    return {"error": f"Failed to update investor: {result['error']}"}

                return {
                    "success": True,
                    "investor_updated": True,
                    "email_logged": True,
                    "new_health_score": new_health_score
                }
            else:
                # Investor doesn't exist in CRM yet - just log success
                return {
                    "success": True,
                    "investor_updated": False,
                    "email_logged": True,
                    "note": "Investor not in CRM yet"
                }

        except Exception as e:
            return {
                "error": f"Failed to log email: {str(e)}"
            }

    def update_investor_field(
        self,
        investor_email: str,
        field_name: str,
        value: Any
    ) -> Dict[str, Any]:
        """
        Update a single field for an investor.

        Args:
            investor_email: Investor email address
            field_name: Name of field to update
            value: New value for the field

        Returns:
            Dict with 'success' bool and result
        """
        try:
            investor = self.get_investor_by_email(investor_email)

            if not investor:
                return {"error": "Investor not found"}

            update_data = {field_name: value}

            result = self.client.update_record(
                self.base_id,
                self.table_id,
                investor["id"],
                update_data
            )

            if "error" in result:
                return {"error": result["error"]}

            return {
                "success": True,
                "updated_field": field_name,
                "record_id": investor["id"]
            }

        except Exception as e:
            return {"error": f"Failed to update field: {str(e)}"}

    def add_note(self, investor_email: str, note: str) -> Dict[str, Any]:
        """
        Add a timestamped note to an investor's record.

        Args:
            investor_email: Investor email address
            note: Note text

        Returns:
            Dict with 'success' bool
        """
        try:
            investor = self.get_investor_by_email(investor_email)

            if not investor:
                return {"error": "Investor not found"}

            # Get existing notes
            fields = investor.get("fields", {})
            existing_notes = fields.get("notes", "")

            # Add timestamp and new note
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_note = f"[{timestamp}] {note}"

            if existing_notes:
                updated_notes = f"{existing_notes}\n\n{new_note}"
            else:
                updated_notes = new_note

            # Update record
            update_data = {"notes": updated_notes}

            result = self.client.update_record(
                self.base_id,
                self.table_id,
                investor["id"],
                update_data
            )

            if "error" in result:
                return {"error": result["error"]}

            return {
                "success": True,
                "note_added": True
            }

        except Exception as e:
            return {"error": f"Failed to add note: {str(e)}"}


# Convenience function
def save_analysis_to_crm(
    analysis_result: Dict[str, Any],
    thread_data: Dict[str, Any],
    user_email: str
) -> Dict[str, Any]:
    """Save thread analysis to investor CRM"""
    crm = InvestorCRM()
    return crm.save_analysis_to_crm(analysis_result, thread_data, user_email)
