"""
Email Composer Utilities
Template management, variable substitution, and email drafting
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
import re


@dataclass
class EmailTemplate:
    """Email template with variable substitution support"""

    name: str
    category: str  # cold_intro, follow_up, meeting_request, thank_you, update, custom
    subject_template: str
    body_template: str
    variables: List[str]  # List of variable names used in template
    description: str = ""


def get_default_templates() -> List[EmailTemplate]:
    """
    Get library of pre-built email templates.

    Returns:
        List of EmailTemplate objects
    """
    templates = [
        EmailTemplate(
            name="Cold Introduction",
            category="cold_intro",
            subject_template="Quick intro - {{company_name}}",
            body_template="""<p>Hi {{investor_name}},</p>

<p>I hope this email finds you well. My name is {{sender_name}}, and I'm reaching out from {{company_name}}.</p>

<p>We're building {{company_description}}, and given {{firm}}'s focus on {{investor_focus}}, I thought there might be a good fit.</p>

<p>Would you be open to a brief call next week to discuss this further?</p>

<p>Best regards,<br>
{{sender_name}}<br>
{{sender_title}}<br>
{{company_name}}</p>""",
            variables=["investor_name", "company_name", "sender_name", "company_description", "firm", "investor_focus", "sender_title"],
            description="Initial cold outreach to a new investor"
        ),

        EmailTemplate(
            name="Follow-up (No Response)",
            category="follow_up",
            subject_template="Re: {{previous_subject}}",
            body_template="""<p>Hi {{investor_name}},</p>

<p>I wanted to follow up on my email from {{last_contact_date}} about {{company_name}}.</p>

<p>I understand you're likely busy, but I wanted to make sure this didn't get lost in your inbox. We've made some exciting progress since I last reached out:</p>

<p>{{recent_update}}</p>

<p>Would love to share more if you have 15 minutes in the coming weeks.</p>

<p>Best,<br>
{{sender_name}}</p>""",
            variables=["investor_name", "previous_subject", "last_contact_date", "company_name", "recent_update", "sender_name"],
            description="Follow-up when no response received"
        ),

        EmailTemplate(
            name="Meeting Request",
            category="meeting_request",
            subject_template="Meeting request - {{company_name}}",
            body_template="""<p>Hi {{investor_name}},</p>

<p>Thank you for your interest in {{company_name}}. I'd love to set up a time to walk you through our progress and answer any questions.</p>

<p>I'm available:</p>
<ul>
<li>{{availability_option_1}}</li>
<li>{{availability_option_2}}</li>
<li>{{availability_option_3}}</li>
</ul>

<p>Do any of these times work for you? Happy to find an alternative if not.</p>

<p>Looking forward to connecting,<br>
{{sender_name}}</p>""",
            variables=["investor_name", "company_name", "availability_option_1", "availability_option_2", "availability_option_3", "sender_name"],
            description="Request a meeting with specific time options"
        ),

        EmailTemplate(
            name="Thank You (Post-Meeting)",
            category="thank_you",
            subject_template="Thank you - great conversation!",
            body_template="""<p>Hi {{investor_name}},</p>

<p>Thank you for taking the time to meet with me {{meeting_timeframe}}. I really appreciated your insights on {{key_topic_discussed}}.</p>

<p>As discussed, I'm sending over:</p>
<ul>
{{materials_list}}
</ul>

<p>Please let me know if you have any questions or need additional information. {{next_steps}}</p>

<p>Looking forward to staying in touch,<br>
{{sender_name}}</p>""",
            variables=["investor_name", "meeting_timeframe", "key_topic_discussed", "materials_list", "next_steps", "sender_name"],
            description="Thank you email after a meeting"
        ),

        EmailTemplate(
            name="Due Diligence Materials",
            category="due_diligence",
            subject_template="{{company_name}} - Due diligence materials",
            body_template="""<p>Hi {{investor_name}},</p>

<p>As requested, I'm sharing our due diligence materials for {{company_name}}.</p>

<p>Attached/linked:</p>
<ul>
<li>Updated pitch deck</li>
<li>Financial projections ({{projection_period}})</li>
<li>{{additional_materials}}</li>
</ul>

<p>Key highlights since our last conversation:</p>
<p>{{recent_milestones}}</p>

<p>Happy to answer any questions or provide additional information.</p>

<p>Best regards,<br>
{{sender_name}}</p>""",
            variables=["investor_name", "company_name", "projection_period", "additional_materials", "recent_milestones", "sender_name"],
            description="Share due diligence materials"
        ),

        EmailTemplate(
            name="General Update",
            category="update",
            subject_template="{{company_name}} update - {{update_theme}}",
            body_template="""<p>Hi {{investor_name}},</p>

<p>Hope you're doing well! I wanted to share a quick update on {{company_name}}.</p>

<p>{{update_content}}</p>

<p>Key metrics:</p>
<ul>
{{metrics_list}}
</ul>

<p>{{closing_question}}</p>

<p>Best,<br>
{{sender_name}}</p>""",
            variables=["investor_name", "company_name", "update_theme", "update_content", "metrics_list", "closing_question", "sender_name"],
            description="Periodic update to keep investor engaged"
        ),

        EmailTemplate(
            name="Quick Question",
            category="follow_up",
            subject_template="Quick question about {{topic}}",
            body_template="""<p>Hi {{investor_name}},</p>

<p>Hope this email finds you well. I have a quick question about {{topic}}.</p>

<p>{{question_details}}</p>

<p>Would appreciate your thoughts when you have a moment.</p>

<p>Thanks!<br>
{{sender_name}}</p>""",
            variables=["investor_name", "topic", "question_details", "sender_name"],
            description="Ask a specific question to maintain engagement"
        ),
    ]

    return templates


def render_template(template: EmailTemplate, variables: Dict[str, str]) -> Dict[str, str]:
    """
    Render an email template with variable substitution.

    Args:
        template: EmailTemplate object
        variables: Dict mapping variable names to values

    Returns:
        Dict with 'subject' and 'body' keys containing rendered text
    """
    # Make a copy of variables with defaults for missing values
    vars_with_defaults = {
        var: variables.get(var, f"{{{{MISSING: {var}}}}}")
        for var in template.variables
    }

    # Add any extra variables provided
    vars_with_defaults.update(variables)

    # Render subject
    subject = template.subject_template
    for var_name, var_value in vars_with_defaults.items():
        subject = subject.replace(f"{{{{{var_name}}}}}", str(var_value))

    # Render body
    body = template.body_template
    for var_name, var_value in vars_with_defaults.items():
        body = body.replace(f"{{{{{var_name}}}}}", str(var_value))

    return {
        "subject": subject,
        "body": body
    }


def extract_variables_from_investor(investor_record: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract common email variables from an investor CRM record.

    Args:
        investor_record: Investor record from Airtable (with 'fields' dict)

    Returns:
        Dict of variable names to values
    """
    fields = investor_record.get("fields", {})

    variables = {
        "investor_name": fields.get("name", "there"),
        "investor_email": fields.get("email", ""),
        "firm": fields.get("firm", "your firm"),
        "investor_focus": fields.get("interests", "innovation"),
        "last_contact_date": fields.get("last_contact_date", "recently"),
        "investor_stage": fields.get("stage", ""),
    }

    # Format last contact date nicely if it's an ISO date
    if variables["last_contact_date"] and "T" in variables["last_contact_date"]:
        try:
            dt = datetime.fromisoformat(variables["last_contact_date"])
            variables["last_contact_date"] = dt.strftime("%B %d")  # e.g., "January 15"
        except:
            pass

    return variables


def get_ai_draft_from_strategy(strategy: Any) -> Optional[Dict[str, str]]:
    """
    Convert an AI-generated campaign strategy to email format.

    Args:
        strategy: CampaignStrategy object from ThreadAnalysis

    Returns:
        Dict with 'subject' and 'body', or None if unavailable
    """
    try:
        if not hasattr(strategy, 'email_draft') or not strategy.email_draft:
            return None

        # Extract subject from email draft if present
        email_text = strategy.email_draft

        # Try to find subject line (usually first line or marked as "Subject:")
        subject_match = re.search(r'Subject:\s*(.+?)(?:\n|$)', email_text, re.IGNORECASE)
        if subject_match:
            subject = subject_match.group(1).strip()
            # Remove subject line from body
            body = re.sub(r'Subject:\s*.+?(?:\n|$)', '', email_text, flags=re.IGNORECASE).strip()
        else:
            # Default subject based on strategy type
            strategy_type = getattr(strategy, 'strategy_type', 'follow_up')
            subject_map = {
                'cold_intro': 'Introduction',
                'follow_up': 'Following up',
                'meeting_request': 'Meeting request',
                'value_add': 'Quick thought',
                'milestone_update': 'Exciting update'
            }
            subject = subject_map.get(strategy_type, 'Following up')
            body = email_text

        # Convert plain text to HTML (simple paragraph wrapping)
        if not body.startswith('<'):
            # Convert line breaks to paragraph tags
            paragraphs = body.split('\n\n')
            html_body = ''.join([f'<p>{p.strip()}</p>' for p in paragraphs if p.strip()])
        else:
            html_body = body

        return {
            "subject": subject,
            "body": html_body
        }
    except Exception as e:
        print(f"Error extracting AI draft: {e}")
        return None


def get_common_variables() -> Dict[str, str]:
    """
    Get common variables that are used across templates.
    Provides default/placeholder values.

    Returns:
        Dict of common variable names to placeholder values
    """
    return {
        "company_name": "[Your Company]",
        "sender_name": "[Your Name]",
        "sender_title": "[Your Title]",
        "company_description": "[Brief company description]",
        "recent_update": "[Recent milestone or update]",
        "next_steps": "[What happens next]",
        "meeting_timeframe": "earlier this week",
        "key_topic_discussed": "[Topic discussed]",
        "materials_list": "<li>[Material 1]</li><li>[Material 2]</li>",
        "projection_period": "2024-2026",
        "additional_materials": "[Additional docs]",
        "recent_milestones": "[Key achievements]",
        "update_theme": "[Update theme]",
        "update_content": "[Update details]",
        "metrics_list": "<li>[Metric 1]</li><li>[Metric 2]</li>",
        "closing_question": "Let me know if you'd like to discuss further!",
        "topic": "[Topic]",
        "question_details": "[Question details]",
        "availability_option_1": "[Time option 1]",
        "availability_option_2": "[Time option 2]",
        "availability_option_3": "[Time option 3]",
        "previous_subject": "[Previous email subject]",
    }


def merge_variables(investor_vars: Dict[str, str], custom_vars: Dict[str, str]) -> Dict[str, str]:
    """
    Merge investor variables with custom variables, with custom taking precedence.

    Args:
        investor_vars: Variables extracted from investor record
        custom_vars: User-provided custom variables

    Returns:
        Merged dictionary
    """
    common_vars = get_common_variables()

    # Start with common defaults
    merged = common_vars.copy()

    # Override with investor-specific data
    merged.update(investor_vars)

    # Override with user custom values
    merged.update(custom_vars)

    return merged


def validate_email_content(subject: str, body: str) -> Dict[str, Any]:
    """
    Validate email content before sending.

    Args:
        subject: Email subject
        body: Email body (HTML)

    Returns:
        Dict with 'valid' (bool) and 'errors' (list of error messages)
    """
    errors = []

    # Check for empty subject
    if not subject or not subject.strip():
        errors.append("Subject cannot be empty")

    # Check for empty body
    if not body or not body.strip():
        errors.append("Email body cannot be empty")

    # Check for unreplaced variables
    missing_vars = re.findall(r'\{\{([^}]+)\}\}', subject + body)
    if missing_vars:
        errors.append(f"Missing variables: {', '.join(set(missing_vars))}")

    # Check for placeholder text that wasn't replaced
    placeholders = re.findall(r'\[([^\]]+)\]', subject + body)
    if placeholders:
        # Filter out intentional brackets like email addresses
        intentional = ['Company', 'Your Name', 'Your Title', 'Brief company description',
                      'Recent milestone', 'What happens next', 'Topic discussed']
        problematic = [p for p in set(placeholders) if any(x in p for x in intentional)]
        if problematic:
            errors.append(f"Placeholder text detected: {', '.join(problematic[:3])}")

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }
