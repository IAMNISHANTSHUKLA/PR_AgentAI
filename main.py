"""CLI entry point for PR AgentAI — review a PR diff from the command line."""

import sys
import json
import logging
import argparse
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents.orchestrator import Orchestrator


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s │ %(name)-20s │ %(levelname)-7s │ %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(
        description="PR AgentAI — Multi-Agent PR Review System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --diff data/sample_prs/vulnerable_api.diff
  python main.py --diff data/sample_prs/clean_payment.diff --pr-id PR-42
  python main.py --diff data/sample_prs/vulnerable_api.diff --json
        """,
    )
    parser.add_argument("--diff", required=True, help="Path to diff file to review")
    parser.add_argument("--pr-id", default="PR-001", help="PR identifier (default: PR-001)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of formatted")
    parser.add_argument("--log-level", default="INFO", help="Log level (default: INFO)")
    args = parser.parse_args()

    setup_logging(args.log_level)
    console = Console()

    # Read diff
    diff_path = Path(args.diff)
    if not diff_path.exists():
        console.print(f"[red]Error: Diff file not found: {diff_path}[/red]")
        sys.exit(1)

    diff = diff_path.read_text(encoding="utf-8")
    console.print(Panel(f"📋 Reviewing [bold]{diff_path.name}[/bold] ({len(diff)} chars)", style="blue"))

    # Run review
    orchestrator = Orchestrator()
    result = orchestrator.review(diff, pr_id=args.pr_id)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return

    # ── Rich formatted output ──────────────────────────────────────────
    # Overall verdict
    verdict_colors = {
        "approve": "green",
        "comment": "yellow",
        "request_changes": "red",
    }
    color = verdict_colors.get(result.verdict, "white")
    console.print()
    console.print(Panel(
        Markdown(result.overall_summary),
        title=f"🤖 PR Review — {args.pr_id}",
        border_style=color,
        padding=(1, 2),
    ))

    # Per-agent results
    for agent_result in result.results:
        if agent_result.error:
            console.print(Panel(
                f"[red]Error: {agent_result.error}[/red]",
                title=f"❌ {agent_result.agent_name.title()} Agent",
                border_style="red",
            ))
            continue

        # Findings table
        if agent_result.findings:
            table = Table(
                title=f"🔍 {agent_result.agent_name.title()} — Score: {agent_result.score}/100",
                show_lines=True,
                border_style="dim",
            )
            table.add_column("Severity", style="bold", width=10)
            table.add_column("Category", width=20)
            table.add_column("File", width=20)
            table.add_column("Title", width=30)
            table.add_column("Suggestion", width=40)

            severity_colors = {
                "critical": "red bold",
                "high": "red",
                "medium": "yellow",
                "low": "cyan",
                "info": "dim",
            }

            for finding in agent_result.findings:
                sev_style = severity_colors.get(finding.severity, "white")
                location = finding.file
                if finding.line:
                    location += f":{finding.line}"
                table.add_row(
                    f"[{sev_style}]{finding.severity.upper()}[/{sev_style}]",
                    finding.category,
                    location,
                    finding.title,
                    finding.suggestion[:80] + "..." if len(finding.suggestion) > 80 else finding.suggestion,
                )

            console.print(table)
        else:
            console.print(Panel(
                f"[green]No issues found — Score: {agent_result.score}/100[/green]",
                title=f"✅ {agent_result.agent_name.title()} Agent",
                border_style="green",
            ))

    # Timing
    console.print(f"\n⏱️  Total time: [bold]{result.duration_ms:.0f}ms[/bold]")
    for r in result.results:
        console.print(f"   {r.agent_name}: {r.duration_ms:.0f}ms")
    console.print()


if __name__ == "__main__":
    main()
