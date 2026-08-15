"""web10 — test pages and sites against the Web 1.0 Specification (2026)."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from .checker import check_targets, make_fetcher
from .fetcher import LocalFetcher
from .grading import is_pass
from .report import to_html, to_json, to_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="web10",
        description=(
            "Test pages and sites against the Web 1.0 Specification "
            "(2026 Edition): no scripts, no third parties, no cookies, no bloat."
        ),
    )
    parser.add_argument(
        "targets", nargs="+",
        help="URLs to check, or local paths (a directory implies index.html)",
    )
    parser.add_argument("--spider", action="store_true",
                        help="follow same-site links from the targets")
    parser.add_argument("--max-pages", type=int, default=25,
                        help="page limit when spidering (default 25)")
    parser.add_argument("--format", choices=("text", "json", "html"),
                        default="text", help="report format (default text)")
    parser.add_argument("-o", "--output", help="write the report to a file")
    parser.add_argument("--user-agent", help="override the User-Agent header")
    parser.add_argument("--timeout", type=float, default=20.0,
                        help="per-request timeout in seconds (default 20)")
    args = parser.parse_args(argv)

    fetcher = make_fetcher(args.targets[0], user_agent=args.user_agent,
                           timeout=args.timeout)
    targets = args.targets
    if isinstance(fetcher, LocalFetcher):
        targets = [fetcher.resolve_target(t) for t in targets]

    site = check_targets(fetcher, targets, spider=args.spider,
                         max_pages=args.max_pages)
    site.checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    report = {"text": to_text, "json": to_json, "html": to_html}[args.format](site)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(report)
    else:
        print(report)

    if site.grade is None:
        return 2
    return 0 if is_pass(site.grade) else 1


if __name__ == "__main__":
    sys.exit(main())
