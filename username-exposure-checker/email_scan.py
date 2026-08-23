"""Email leak detection module.

Scans profile page HTML for publicly exposed email addresses using regex.
"""
from __future__ import annotations

import re
from typing import List, Optional

# A reasonably strict email regex.
# Matches common email patterns while avoiding most false positives.
EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# Common placeholder/obfuscation patterns to ignore.
NOISE_PATTERNS = [
    "example.com",
    "yourdomain.com",
    "domain.com",
    "email.com",
    "sentry.io",
    "noreply",
    "no-reply",
    "donotreply",
    "support@",
    "admin@",
    "info@",
    "contact@",
    "hello@",
    "team@",
    "help@",
    "sales@",
    "marketing@",
    "privacy@",
    "abuse@",
    "feedback@",
    "service@",
    "webmaster@",
]


def extract_emails(html: str) -> List[str]:
    """Extract candidate email addresses from raw HTML.

    Filters out common placeholder/noise addresses.
    """
    if not html:
        return []

    found = EMAIL_REGEX.findall(html)
    # De-duplicate while preserving order.
    seen = set()
    unique: List[str] = []
    for email in found:
        lower = email.lower()
        if lower in seen:
            continue
        seen.add(lower)
        # Skip obvious noise / placeholder addresses.
        if any(noise in lower for noise in NOISE_PATTERNS):
            continue
        unique.append(email)
    return unique


def scan_page_for_email(html: Optional[str]) -> List[str]:
    """Scan a fetched profile page's HTML for exposed emails.

    Args:
        html: Raw HTML content of the profile page, or None if fetch failed.

    Returns:
        List of detected email addresses (may be empty).
    """
    if not html:
        return []
    return extract_emails(html)
