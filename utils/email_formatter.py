"""
Email content processing utilities for cleaner thread display.

This module provides utilities to parse and format email content,
removing quoted text and improving readability.
"""

import re
from typing import Tuple, Optional
from bs4 import BeautifulSoup, Comment
import html


class EmailContentProcessor:
    """Process email content for cleaner display."""

    # Common quoted text patterns - order matters!
    QUOTED_PATTERNS = [
        r"On .+?wrote:.*$",  # "On [date] [name] wrote:" - matches everything after
        r"From:.+?$",  # "From: [email]"
        r"Sent:.+?$",  # "Sent: [date]"
        r"To:.+?$",  # "To: [email]"
        r"Subject:.+?$",  # "Subject: [subject]"
        r"Date:.+?$",  # "Date: [date]"
        r"^\s*>.*$",  # Lines starting with >
        r"^\s*\|.*$",  # Lines starting with |
        r"^_{5,}$",  # Lines with 5+ underscores
        r"^-{5,}$",  # Lines with 5+ dashes
        r"^={5,}$",  # Lines with 5+ equals
        r".*<.+@.+\..+>.*wrote:.*$",  # Email addresses with "wrote:"
    ]

    # Signature patterns
    SIGNATURE_PATTERNS = [
        r"^--\s*$",  # Standard signature delimiter
        r"^Best regards?[,.]?\s*$",
        r"^Thanks?[,.]?\s*$",
        r"^Sincerely[,.]?\s*$",
        r"^Cheers[,.]?\s*$",
        r"^Sent from my .+$",
        r"^Get Outlook for .+$",
    ]

    @staticmethod
    def extract_clean_text_from_html(html_content: str) -> str:
        """Extract clean text from HTML, removing quoted sections."""
        try:
            if not html_content:
                return ""

            # Parse HTML
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                if script:
                    script.decompose()

            # Remove HTML comments
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                if comment:
                    comment.extract()

            # Look for blockquotes (common in email quotes)
            for blockquote in soup.find_all(["blockquote", "div"]):
                # Check if it's likely quoted content
                if (
                    blockquote
                    and hasattr(blockquote, "get")
                    and blockquote.get("class")
                ):
                    classes = " ".join(blockquote.get("class", []))
                    if any(
                        keyword in classes.lower()
                        for keyword in ["quote", "gmail", "outlook"]
                    ):
                        blockquote.decompose()

            # Get text and clean it
            text = soup.get_text() if soup else ""
            return EmailContentProcessor.clean_email_text(text)
        except Exception as e:
            # If anything fails, fall back to basic text extraction
            if html_content:
                soup = BeautifulSoup(html_content, "html.parser")
                return soup.get_text() if soup else ""
            return ""

    @staticmethod
    def clean_email_text(text: str) -> str:
        """Remove quoted content and signatures from plain text."""
        if not text:
            return ""

        # First, try to split on common email thread delimiters
        # Look for patterns that indicate the start of quoted content
        split_patterns = [
            r"On .+?, at .+?, .+ wrote:",  # "On Feb 16, 2024, at 7:16 AM, Name <email> wrote:"
            r"On .+? \d+, \d+ at \d+:\d+ [AP]M .+ wrote:",  # Various date formats
            r"Sent from my iPhone\s*On .+? wrote:",  # iPhone signature + quoted
            r"From: .+?<.+?@.+?\..+?>",  # Email headers
            r"Sent from my \w+",  # Mobile signatures
            r"Get Outlook for \w+",  # Outlook signatures
        ]

        # Try to find the first occurrence of quoted content
        earliest_match = len(text)
        for pattern in split_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                earliest_match = min(earliest_match, match.start())

        # Extract only the content before the first quoted section
        if earliest_match < len(text):
            clean_text = text[:earliest_match].strip()
        else:
            clean_text = text.strip()

        # Clean up the extracted content
        if clean_text:
            # Remove any remaining signatures from the beginning
            lines = clean_text.split("\n")
            clean_lines = []

            for line in lines:
                line_stripped = line.strip()

                # Skip empty lines at the start, keep them in the middle
                if not line_stripped and not clean_lines:
                    continue

                # Check for signature patterns
                is_signature = any(
                    re.match(pattern, line_stripped, re.IGNORECASE)
                    for pattern in EmailContentProcessor.SIGNATURE_PATTERNS
                )
                if is_signature:
                    break

                clean_lines.append(line.rstrip())

            # Join and clean up
            result = "\n".join(clean_lines).strip()

            # Remove multiple consecutive empty lines
            result = re.sub(r"\n\s*\n\s*\n", "\n\n", result)

            return result

        return ""

    @staticmethod
    def format_thread_message(
        subject: str,
        sender: str,
        recipient: str,
        date: str,
        html_content: str,
        text_content: str,
    ) -> dict:
        """Format a single email message for thread display."""

        # Try to extract clean content
        clean_text = ""

        if html_content:
            clean_text = EmailContentProcessor.extract_clean_text_from_html(
                html_content
            )

        if not clean_text and text_content:
            clean_text = EmailContentProcessor.clean_email_text(text_content)

        # If still no clean text, fall back to original but limit length
        if not clean_text:
            if text_content:
                clean_text = (
                    text_content[:1000] + "..."
                    if len(text_content) > 1000
                    else text_content
                )
            elif html_content:
                soup = BeautifulSoup(html_content, "html.parser")
                clean_text = (
                    soup.get_text()[:1000] + "..."
                    if len(soup.get_text()) > 1000
                    else soup.get_text()
                )

        return {
            "subject": subject,
            "sender": sender,
            "recipient": recipient,
            "date": date,
            "content": clean_text,
            "content_length": len(clean_text),
            "has_content": bool(clean_text.strip()),
        }

    @staticmethod
    def get_thread_summary(messages: list) -> dict:
        """Generate a summary of the email thread."""
        if not messages:
            return {"total_messages": 0, "participants": [], "date_range": None}

        participants = set()
        dates = []
        total_chars = 0

        for msg in messages:
            if msg.get("sender"):
                participants.add(msg["sender"])
            if msg.get("recipient"):
                participants.add(msg["recipient"])
            if msg.get("date"):
                dates.append(msg["date"])
            total_chars += msg.get("content_length", 0)

        return {
            "total_messages": len(messages),
            "participants": sorted(list(participants)),
            "date_range": f"{min(dates)} to {max(dates)}" if dates else None,
            "total_content_chars": total_chars,
        }


def format_email_for_display(
    html_content: str, text_content: str, max_length: int = 500
) -> Tuple[str, str]:
    """
    Format email content for clean display.

    Args:
        html_content: Raw HTML content
        text_content: Raw text content
        max_length: Maximum length for preview

    Returns:
        Tuple of (clean_content, content_type)
    """
    try:
        # Try HTML first
        if html_content:
            clean_text = EmailContentProcessor.extract_clean_text_from_html(
                html_content
            )
            if clean_text and clean_text.strip():
                if len(clean_text) > max_length:
                    return clean_text[:max_length] + "...", "html_cleaned"
                return clean_text, "html_cleaned"

        # Fall back to text
        if text_content:
            clean_text = EmailContentProcessor.clean_email_text(text_content)
            if clean_text and clean_text.strip():
                if len(clean_text) > max_length:
                    return clean_text[:max_length] + "...", "text_cleaned"
                return clean_text, "text_cleaned"

        return "No content available", "empty"
    except Exception as e:
        # If processing fails, return basic fallback
        if text_content:
            safe_text = (
                text_content[:max_length] + "..."
                if len(text_content) > max_length
                else text_content
            )
            return safe_text, "fallback_text"
        elif html_content:
            try:
                soup = BeautifulSoup(html_content, "html.parser")
                basic_text = soup.get_text() if soup else ""
                safe_text = (
                    basic_text[:max_length] + "..."
                    if len(basic_text) > max_length
                    else basic_text
                )
                return safe_text, "fallback_html"
            except:
                return "Content processing failed", "error"
        return "No content available", "empty"


def extract_email_preview(html_content: str, text_content: str) -> str:
    """Extract a brief preview of the email content (first 200 chars)."""
    clean_content, _ = format_email_for_display(
        html_content, text_content, max_length=200
    )

    # Remove extra whitespace and newlines for preview
    preview = re.sub(r"\s+", " ", clean_content).strip()
    return preview
