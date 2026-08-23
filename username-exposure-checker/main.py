"""Username Exposure Checker — CLI entry point.

Usage examples:
    python main.py check johndoe
    python main.py check johndoe --only-found --timeout 15
    python main.py check johndoe --output results.json
    python main.py check-file usernames.txt --output results.csv
    python main.py check johndoe --no-email-scan
"""
from __future__ import annotations

import os
import sys
from typing import List, Optional

import click
from rich.console import Console

from checker import (
    ScanReport,
    check_username,
    check_usernames,
    export_csv,
    export_json,
)
from report import render_all, render_summary, render_report_table

console = Console()


def _resolve_output_format(filepath: str) -> str:
    """Determine output format from file extension."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".json":
        return "json"
    if ext == ".csv":
        return "csv"
    raise click.BadParameter(
        f"Unsupported output format '{ext}'. Use .json or .csv"
    )


def _read_usernames_file(path: str) -> List[str]:
    """Read usernames from a file, one per line. Skips blanks and comments."""
    if not os.path.isfile(path):
        raise click.BadParameter(f"File not found: {path}")
    usernames: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            name = line.strip()
            if name and not name.startswith("#"):
                usernames.append(name)
    if not usernames:
        raise click.BadParameter(f"No usernames found in file: {path}")
    return usernames


def _export(reports: List[ScanReport], output: str) -> None:
    """Export reports to the specified file based on its extension."""
    fmt = _resolve_output_format(output)
    if fmt == "json":
        export_json(reports, output)
    else:
        export_csv(reports, output)
    console.print(f"[green]Results exported to:[/green] {output}")


@click.group()
@click.version_option(version="1.0.0", prog_name="username-exposure-checker")
def cli() -> None:
    """Username Exposure Checker — audit your digital footprint.

    Checks where a username is registered across 300+ sites and optionally
    scans found profiles for publicly exposed email addresses.

    [bold red]Privacy notice:[/bold red] For checking your own accounts only.
    Do not use to investigate others.
    """


@cli.command()
@click.argument("username")
@click.option(
    "--only-found",
    is_flag=True,
    default=False,
    help="Show only sites where the username was found.",
)
@click.option(
    "--timeout",
    default=10,
    show_default=True,
    type=int,
    help="Per-site request timeout in seconds.",
)
@click.option(
    "--output",
    "-o",
    "output",
    default=None,
    help="Export results to a file (.json or .csv).",
)
@click.option(
    "--no-email-scan",
    is_flag=True,
    default=False,
    help="Skip fetching profile pages to scan for exposed emails.",
)
def check(
    username: str,
    only_found: bool,
    timeout: int,
    output: Optional[str],
    no_email_scan: bool,
) -> None:
    """Check a single USERNAME across all supported sites."""
    console.print(f"[bold cyan]Scanning username:[/bold cyan] {username}")
    console.print(f"[dim]Timeout: {timeout}s | Email scan: {not no_email_scan}[/dim]\n")

    report = check_username(
        username,
        timeout=timeout,
        scan_emails=not no_email_scan,
    )

    if output:
        _export([report], output)
    else:
        render_report_table(report, only_found=only_found)
        render_summary(report)


@cli.command(name="check-file")
@click.argument("filepath")
@click.option(
    "--only-found",
    is_flag=True,
    default=False,
    help="Show only sites where the username was found.",
)
@click.option(
    "--timeout",
    default=10,
    show_default=True,
    type=int,
    help="Per-site request timeout in seconds.",
)
@click.option(
    "--output",
    "-o",
    "output",
    default=None,
    help="Export results to a file (.json or .csv).",
)
@click.option(
    "--no-email-scan",
    is_flag=True,
    default=False,
    help="Skip fetching profile pages to scan for exposed emails.",
)
def check_file(
    filepath: str,
    only_found: bool,
    timeout: int,
    output: Optional[str],
    no_email_scan: bool,
) -> None:
    """Bulk check usernames listed in a FILEPATH (one per line)."""
    usernames = _read_usernames_file(filepath)
    console.print(f"[bold cyan]Bulk scanning {len(usernames)} username(s)...[/bold cyan]\n")

    reports = check_usernames(
        usernames,
        timeout=timeout,
        scan_emails=not no_email_scan,
    )

    if output:
        _export(reports, output)
    else:
        render_all(reports, only_found=only_found)


if __name__ == "__main__":
    cli()
