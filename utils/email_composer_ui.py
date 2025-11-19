"""
Email Composer UI Component
Streamlit component for composing and sending emails
"""

import streamlit as st
from typing import Dict, Optional, Any
from datetime import datetime

from utils.email_composer import (
    get_default_templates,
    render_template,
    extract_variables_from_investor,
    get_ai_draft_from_strategy,
    merge_variables,
    validate_email_content,
    get_common_variables
)
from utils.gmail_client import GmailClient
from utils.investor_crm import InvestorCRM


def show_email_composer(
    recipient_email: str,
    investor_record: Optional[Dict[str, Any]] = None,
    mailbox: Optional[str] = None,
    pre_filled_subject: Optional[str] = None,
    pre_filled_body: Optional[str] = None
) -> bool:
    """
    Display simple email composer UI in Streamlit.

    Args:
        recipient_email: Email address of recipient
        investor_record: Optional investor CRM record for variable extraction
        mailbox: Sending mailbox (if None, uses session state)
        pre_filled_subject: Pre-fill subject line (optional)
        pre_filled_body: Pre-fill email body (optional)

    Returns:
        True if email was sent successfully, False otherwise
    """
    st.subheader("✉️ Compose Email")

    # Get mailbox - try multiple sources
    if not mailbox:
        mailbox = st.session_state.get("selected_mailbox")

    # If still no mailbox, try to get from environment
    if not mailbox:
        import os
        allowed_env = os.getenv("ALLOWED_MAILBOXES", "")
        mailboxes_list = [m.strip() for m in allowed_env.split(",") if m.strip()]

        if mailboxes_list:
            # Use the first authenticated mailbox
            mailbox = mailboxes_list[0]
            st.info(f"📧 Using mailbox: {mailbox}")

    if not mailbox:
        st.error("No mailbox configured. Please authenticate a mailbox first.")
        if st.button("📬 Go to Mailboxes", key="composer_goto_mailboxes"):
            st.switch_page("pages/Mailboxes.py")
        return False

    # Initialize session state for composer
    if "composer_subject" not in st.session_state:
        st.session_state["composer_subject"] = pre_filled_subject or ""
    if "composer_body" not in st.session_state:
        st.session_state["composer_body"] = pre_filled_body or ""
    if "composer_template_selected" not in st.session_state:
        st.session_state["composer_template_selected"] = None

    # Simple template selection (collapsed by default)
    with st.expander("📋 Use Email Template (Optional)"):
        templates = get_default_templates()
        template_options = ["-- No Template --"] + [t.name for t in templates]

        selected_template_name = st.selectbox(
            "Choose template:",
            options=template_options,
            help="Optional: Start with a pre-built template"
        )

        # Handle template selection
        if selected_template_name != "-- No Template --" and selected_template_name != st.session_state.get("composer_template_selected"):
            # User selected a new template
            template = next((t for t in templates if t.name == selected_template_name), None)

            if template:
                # Extract variables from investor record
                investor_vars = {}
                if investor_record:
                    investor_vars = extract_variables_from_investor(investor_record)

                # Merge with common variables
                all_vars = merge_variables(investor_vars, get_common_variables())

                # Render template
                rendered = render_template(template, all_vars)

                # Update session state
                st.session_state["composer_subject"] = rendered["subject"]
                st.session_state["composer_body"] = rendered["body"]
                st.session_state["composer_template_selected"] = selected_template_name

                st.success(f"✅ Template loaded!")
                st.rerun()

    # AI Email Generation
    st.markdown("---")

    if st.button("🤖 Generate AI Email", type="primary", use_container_width=True):
        with st.spinner("Generating personalized email using conversation context..."):
            try:
                from openai import OpenAI
                import os

                openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                # Build context from investor record
                investor_fields = investor_record.get("fields", {}) if investor_record else {}

                # Get conversation context
                conversation_summary = investor_fields.get("conversation_summary", "No previous conversation")
                interests = investor_fields.get("interests", "Unknown")
                concerns = investor_fields.get("concerns", "None")
                stage = investor_fields.get("stage", "Unknown")
                sentiment = investor_fields.get("sentiment", "Unknown")
                last_contact = investor_fields.get("last_contact_date", "Unknown")
                first_contact = investor_fields.get("first_contact_date", "Unknown")
                total_emails = investor_fields.get("total_emails_sent", 0)
                reply_rate = investor_fields.get("reply_rate", 0)

                # Calculate days since last contact
                days_since_contact = "Unknown"
                if last_contact and last_contact != "Unknown" and last_contact != "Never":
                    try:
                        from datetime import datetime
                        if "T" in last_contact:
                            last_dt = datetime.fromisoformat(last_contact)
                        else:
                            last_dt = datetime.strptime(last_contact, "%Y-%m-%d")
                        days_since_contact = (datetime.now() - last_dt).days
                    except:
                        pass

                # Build prompt with rich context
                context_prompt = f"""You are a professional fundraising expert writing a direct, concise email to an investor.

CRITICAL: Keep email SHORT and PROFESSIONAL - maximum 3 short paragraphs. Be direct, not chatty.

INVESTOR CONTEXT:
- Name: {investor_fields.get('name', 'there')}
- Firm: {investor_fields.get('firm', 'Unknown')}
- Current Stage: {stage}
- Sentiment: {sentiment}
- Last Contact: {last_contact} ({days_since_contact} days ago if numeric)
- First Contact: {first_contact}
- Total Emails Exchanged: {total_emails}
- Reply Rate: {reply_rate:.0%}

CONVERSATION HISTORY:
{conversation_summary}

THEIR INTERESTS:
{interests if interests else 'Not yet identified - this is likely a cold outreach'}

THEIR CONCERNS:
{concerns if concerns else 'None raised yet'}

YOUR TASK:
Write a PROFESSIONAL, DIRECT, CONCISE email (maximum 3 short paragraphs) that:
1. References where the conversation left off (use the last contact date and conversation summary)
2. If they asked questions - answer them directly
3. If they raised concerns - address them
4. Has ONE clear call-to-action
5. Is professional and to-the-point (not chatty, no fluff)
6. Uses their name if available

STYLE GUIDELINES:
- Professional and direct (like a busy executive would write)
- Maximum 3 paragraphs, each 2-3 sentences
- No unnecessary pleasantries or filler
- Get to the point quickly
- One specific ask or next step

EXAMPLES OF GOOD vs BAD:
BAD (too chatty): "I hope this email finds you well! I wanted to reach out and see how things are going..."
GOOD (professional): "Following up on our conversation from {days_since_contact} days ago about [specific topic]."

If cold outreach: 1 paragraph intro, 1 paragraph value prop, 1 paragraph ask.
If follow-up: Reference last conversation, provide update or answer, clear next step.

Format: Return ONLY the email body in plain text (no subject line).
Do NOT use placeholder text - be specific or omit.
"""

                response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a senior executive who writes brief, professional, direct emails. No fluff, no pleasantries, just clear communication."},
                        {"role": "user", "content": context_prompt}
                    ],
                    temperature=0.6,
                    max_tokens=300
                )

                generated_body = response.choices[0].message.content.strip()

                # Generate subject line
                subject_prompt = f"""Write a professional, direct subject line (max 6 words) for this email.

Relationship stage: {stage}
Last contacted: {days_since_contact} days ago
Email preview: {generated_body[:150]}...

Subject should be specific and action-oriented. No generic phrases.

Examples:
- "Quick update on Series A timeline"
- "Following up: metrics question"
- "Deck + Q3 financials attached"

Return ONLY the subject line, no quotes."""

                subject_response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": subject_prompt}],
                    temperature=0.7,
                    max_tokens=20
                )

                generated_subject = subject_response.choices[0].message.content.strip().replace('"', '')

                # Update composer
                st.session_state["composer_subject"] = generated_subject
                st.session_state["composer_body"] = generated_body

                st.success("✅ AI email generated using conversation context!")
                st.rerun()

            except Exception as e:
                st.error(f"Failed to generate email: {str(e)}")

    # Email form
    st.markdown("---")

    # Recipient (read-only)
    st.text_input("📧 To:", value=recipient_email, disabled=True)

    # From (read-only)
    st.text_input("📤 From:", value=mailbox, disabled=True)

    # Subject
    subject = st.text_input(
        "✍️ Subject:",
        value=st.session_state["composer_subject"],
        placeholder="Enter email subject...",
        key="email_subject_input"
    )
    st.session_state["composer_subject"] = subject

    # Body
    body = st.text_area(
        "📝 Message:",
        value=st.session_state["composer_body"],
        height=400,
        placeholder="Enter your message here...\n\nYou can use HTML tags for formatting.",
        key="email_body_input"
    )
    st.session_state["composer_body"] = body

    # Validation
    validation = validate_email_content(subject, body)

    if not validation["valid"]:
        st.warning("⚠️ " + " | ".join(validation["errors"]))

    # Simple action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        send_button = st.button(
            "📤 Send Email",
            type="primary",
            use_container_width=True,
            disabled=not validation["valid"]
        )

    with col2:
        draft_button = st.button(
            "💾 Save as Draft",
            use_container_width=True,
            disabled=not validation["valid"]
        )

    with col3:
        cancel_button = st.button("❌ Close", use_container_width=True)

    # Handle actions
    if send_button:
        # Confirmation dialog
        st.warning("🚨 **Are you sure you want to send this email?**")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Yes, Send It!", type="primary", use_container_width=True, key="confirm_send"):
                with st.spinner("📤 Sending email..."):
                    try:
                        gmail_client = GmailClient()

                        # Send email
                        result = gmail_client.send_email(
                            mailbox=mailbox,
                            to=recipient_email,
                            subject=subject,
                            body_html=body
                        )

                        if result.get("success"):
                            st.success(f"✅ Email sent successfully! Message ID: {result.get('id')}")

                            # Log to CRM
                            try:
                                crm = InvestorCRM()
                                crm.log_sent_email({
                                    "investor_email": recipient_email,
                                    "subject": subject,
                                    "body": body,
                                    "sent_at": datetime.now().isoformat(),
                                    "message_id": result.get("id"),
                                    "thread_id": result.get("threadId"),
                                    "mailbox": mailbox
                                })
                                st.info("📊 Email activity logged to CRM")
                            except Exception as log_error:
                                st.warning(f"Email sent but logging failed: {log_error}")

                            # Clear composer
                            st.session_state["composer_subject"] = ""
                            st.session_state["composer_body"] = ""
                            st.session_state["show_email_composer"] = False

                            # Small delay to show success message
                            import time
                            time.sleep(2)

                            st.rerun()
                            return True
                        else:
                            st.error(f"❌ Failed to send email: {result.get('error', 'Unknown error')}")
                            if "details" in result:
                                with st.expander("Error Details"):
                                    st.code(result["details"])

                    except Exception as e:
                        st.error(f"❌ Error sending email: {str(e)}")
                        import traceback
                        with st.expander("Error Details"):
                            st.code(traceback.format_exc())

        with col2:
            if st.button("❌ Cancel", use_container_width=True, key="cancel_send"):
                st.info("Send cancelled")
                st.rerun()

    if draft_button:
        with st.spinner("💾 Saving draft..."):
            try:
                gmail_client = GmailClient()

                # Create draft
                result = gmail_client.create_draft(
                    mailbox=mailbox,
                    to=recipient_email,
                    subject=subject,
                    body_html=body
                )

                if result.get("success"):
                    st.success(f"✅ Draft saved! Draft ID: {result.get('id')}")
                else:
                    st.error(f"❌ Failed to save draft: {result.get('error', 'Unknown error')}")

            except Exception as e:
                st.error(f"❌ Error saving draft: {str(e)}")

    if cancel_button:
        st.session_state["show_email_composer"] = False
        st.session_state["composer_subject"] = ""
        st.session_state["composer_body"] = ""
        st.rerun()

    return False


def show_quick_email_button(recipient_email: str, investor_record: Optional[Dict] = None):
    """
    Show a quick email composer button that opens a modal/expander.

    Args:
        recipient_email: Email address of recipient
        investor_record: Optional investor record
    """
    if st.button("✉️ Compose Email", type="primary"):
        st.session_state["show_email_composer"] = True
        st.session_state["compose_email_for"] = recipient_email
        if investor_record:
            st.session_state["compose_email_investor"] = investor_record

    # Show composer if triggered
    if st.session_state.get("show_email_composer") and st.session_state.get("compose_email_for") == recipient_email:
        with st.expander("✉️ Email Composer", expanded=True):
            show_email_composer(
                recipient_email=recipient_email,
                investor_record=st.session_state.get("compose_email_investor"),
                ai_draft_available="email_draft_template" in st.session_state
            )
