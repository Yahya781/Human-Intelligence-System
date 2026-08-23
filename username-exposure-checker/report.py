"""Rich terminal output and summary report rendering."""
from __future__ import annotations

from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from checker import ScanReport

console = Console()


def render_report_table(report: ScanReport, only_found: bool = False) -> None:
    """Render a single username's results as a rich table.

    Args:
        report: The ScanReport to render.
        only_found: If True, only show rows where the username was found.
    """
    title = f"Scan results for: {report.username}"

    table = Table(title=title, show_lines=True, expand=True)
    table.add_column("Site", style="cyan", no_wrap=True)
    table.add_column("Found", justify="center")
    table.add_column("URL", style="blue", overflow="fold")
    table.add_column("Emails Detected", style="yellow", overflow="fold")

    rows_added = 0
    for r in report.results:
        if only_found and not r.found:
            continue
        found_text = Text("YES", style="bold green") if r.found else Text("no", style="dim")
        emails_text = ", ".join(r.emails) if r.emails else Text("—", style="dim")
        url_text = r.url or Text("—", style="dim")
        table.add_row(r.site, found_text, url_text, emails_text)
        rows_added += 1

    if rows_added == 0:
        console.print(
            f"[dim]No results to display for '{report.username}' "
            "(no matches found).[/dim]"
        )
        return

    console.print(table)


def render_summary(report: ScanReport) -> None:
    """Render the summary panel for a single username scan."""
    risk = report.risk_level
    risk_style = {
        "Low": "green",
        "Medium": "yellow",
        "High": "bold red",
    }.get(risk, "white")

    summary_text = (
        f"[bold]Username:[/bold] {report.username}\n"
        f"[bold]Total sites checked:[/bold] {report.total_checked}\n"
        f"[bold]Sites where username found:[/bold] {report.total_found}\n"
        f"[bold]Sites with public email detected:[/bold] {report.total_with_email}\n"
        f"[bold]Risk level:[/bold] [{risk_style}]{risk}[/{risk_style}]"
    )

    console.print(Panel(summary_text, title="Summary", border_style="blue"))


def render_all(
    reports: List[ScanReport],
    only_found: bool = False,
) -> None:
    """Render all reports (tables + summaries) to the terminal."""
    for report in reports:
        render_report_table(report, only_found=only_found)
        render_summary(report)
        console.print()
