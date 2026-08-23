"""Core username checking logic.

Wraps sherlock-project to scan a username across supported sites,
optionally fetches each found profile page, and scans it for exposed emails.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

import requests

from email_scan import scan_page_for_email


@dataclass
class SiteResult:
    """Result of checking a username on a single site."""

    site: str
    username: str
    found: bool
    url: Optional[str] = None
    emails: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class ScanReport:
    """Aggregated report for a single username scan."""

    username: str
    results: List[SiteResult] = field(default_factory=list)

    @property
    def total_checked(self) -> int:
        return len(self.results)

    @property
    def total_found(self) -> int:
        return sum(1 for r in self.results if r.found)

    @property
    def total_with_email(self) -> int:
        return sum(1 for r in self.results if r.found and r.emails)

    @property
    def risk_level(self) -> str:
        """Classify exposure risk based on number of found profiles."""
        found = self.total_found
        if found == 0:
            return "Low"
        if found <= 5:
            return "Low"
        if found <= 15:
            return "Medium"
        return "High"

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "summary": {
                "total_checked": self.total_checked,
                "total_found": self.total_found,
                "total_with_email": self.total_with_email,
                "risk_level": self.risk_level,
            },
            "results": [asdict(r) for r in self.results],
        }


def _run_sherlock(
    username: str,
    timeout: int,
) -> Dict[str, dict]:
    """Run sherlock for a single username and return parsed results.

    Uses the sherlock-project v0.16.0 API:
        sherlock(username, site_data, query_notify, timeout=...) -> dict

    Returns a dict mapping site name -> {"found": bool, "url": str|None}.
    """
    try:
        from sherlock_project.sherlock import sherlock
        from sherlock_project.sites import SitesInformation
        from sherlock_project.notify import QueryNotify
    except ImportError:
        try:
            from sherlock import sherlock
            from sherlock.sites import SitesInformation
            from sherlock.notify import QueryNotify
        except ImportError:
            print(
                "ERROR: sherlock-project is not installed. "
                "Run `pip install -r requirements.txt`.",
                file=sys.stderr,
            )
            sys.exit(1)

    site_results: Dict[str, dict] = {}

    try:
        # Load the built-in site list.
        sites_info = SitesInformation()
        # sherlock() expects a dict of {site_name: site_info_dict}.
        # Each SiteInformation object stores the dict in `.information`.
        site_data = {
            name: site.information for name, site in sites_info.sites.items()
        }

        # QueryNotify prints progress to stdout; use a silent variant.
        query_notify = QueryNotify(result=None)

        results = sherlock(
            username,
            site_data,
            query_notify,
            timeout=timeout,
        )

        # results is a dict: {site_name: QueryResult}
        for site_name, query_result in results.items():
            status = getattr(query_result, "status", None)
            url = getattr(query_result, "site_url_user", None)

            # "Claimed" means the username was found on that site.
            found = "Claimed" in str(status) if status else False

            site_results[site_name] = {
                "found": found,
                "url": url,
            }
    except Exception as exc:
        print(f"WARNING: sherlock scan error: {exc}", file=sys.stderr)

    return site_results


def _fetch_page(url: str, timeout: int) -> Optional[str]:
    """Fetch a URL and return its HTML text, or None on failure."""
    if not url:
        return None
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; UsernameExposureChecker/1.0; "
                "+https://github.com/your-repo/username-exposure-checker)"
            )
        }
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            return resp.text
    except requests.RequestException:
        return None
    return None


def check_username(
    username: str,
    timeout: int = 10,
    scan_emails: bool = True,
) -> ScanReport:
    """Check a single username across all sherlock-supported sites.

    Args:
        username: The username to search for.
        timeout: Per-site request timeout in seconds.
        scan_emails: If True, fetch found profile pages and scan for emails.

    Returns:
        A ScanReport with all results.
    """
    site_results = _run_sherlock(username, timeout)

    report = ScanReport(username=username)

    for site_name, data in site_results.items():
        found = data.get("found", False)
        url = data.get("url")

        emails: List[str] = []
        if found and scan_emails and url:
            html = _fetch_page(url, timeout)
            emails = scan_page_for_email(html)

        report.results.append(
            SiteResult(
                site=site_name,
                username=username,
                found=found,
                url=url,
                emails=emails,
            )
        )

    return report


def check_usernames(
    usernames: List[str],
    timeout: int = 10,
    scan_emails: bool = True,
) -> List[ScanReport]:
    """Check multiple usernames sequentially.

    Args:
        usernames: List of usernames to check.
        timeout: Per-site request timeout in seconds.
        scan_emails: If True, scan found profile pages for emails.

    Returns:
        List of ScanReport objects, one per username.
    """
    reports: List[ScanReport] = []
    for name in usernames:
        report = check_username(name, timeout=timeout, scan_emails=scan_emails)
        reports.append(report)
    return reports


def export_json(reports: List[ScanReport], filepath: str) -> None:
    """Export scan reports to a JSON file."""
    data = [r.to_dict() for r in reports]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def export_csv(reports: List[ScanReport], filepath: str) -> None:
    """Export scan reports to a CSV file (one row per site result)."""
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["username", "site", "found", "url", "emails", "error"]
        )
        for report in reports:
            for r in report.results:
                writer.writerow(
                    [
                        r.username,
                        r.site,
                        r.found,
                        r.url or "",
                        ";".join(r.emails),
                        r.error or "",
                    ]
                )
