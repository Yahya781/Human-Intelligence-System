"""Scan all 44 sherlock-found profile URLs for exposed email addresses.

Reads the sherlock .txt output (one URL per line), fetches each page,
and extracts any email addresses found in the HTML.
"""
from __future__ import annotations

import concurrent.futures
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List

import requests

# Reuse the email extraction logic from the project.
sys.path.insert(0, str(Path(__file__).parent))
from email_scan import extract_emails

# Browser-like headers to avoid basic bot blocks.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT = 20
MAX_WORKERS = 8

# The 44 profile URLs found by sherlock (from --nsfw --ignore-exclusions scan).
PROFILE_URLS: List[str] = [
    "https://www.7cups.com/@alinaa.shah54",
    "https://admireme.vip/alinaa.shah54",
    "https://www.airliners.net/user/alinaa.shah54/profile/photos",
    "https://developer.apple.com/forums/profile/alinaa.shah54",
    "https://discussions.apple.com/profile/alinaa.shah54",
    "https://archive.org/details/@alinaa.shah54",
    "https://www.bandcamp.com/alinaa.shah54",
    "https://boardgamegeek.com/user/alinaa.shah54",
    "https://bugcrowd.com/alinaa.shah54",
    "https://discords.com/api-v2/bio/details/alinaa.shah54",
    "https://forums.envato.com/u/alinaa.shah54",
    "https://auth.geeksforgeeks.org/user/alinaa.shah54",
    "https://hashnode.com/@alinaa.shah54",
    "https://hubski.com/user/alinaa.shah54",
    "https://www.lesswrong.com/users/alinaa.shah54",
    "https://odysee.com/@alinaa.shah54",
    "https://forums.pcgamer.com/members/?username=alinaa.shah54",
    "https://rarible.com/marketplace/api/v4/urls/alinaa.shah54",
    "https://www.reddit.com/user/alinaa.shah54",
    "https://www.realmeye.com/player/alinaa.shah54",
    "https://replit.com/@alinaa.shah54",
    "https://www.rockettube.com/alinaa.shah54",
    "https://www.scribd.com/alinaa.shah54",
    "https://www.shelf.im/alinaa.shah54",
    "https://slideshare.net/alinaa.shah54",
    "https://splice.com/alinaa.shah54",
    "https://open.spotify.com/user/alinaa.shah54",
    "https://www.tiktok.com/@alinaa.shah54",
    "https://tryhackme.com/p/alinaa.shah54",
    "https://forum.velomania.ru/member.php?username=alinaa.shah54",
    "https://vero.co/alinaa.shah54",
    "https://hosted.weblate.org/user/alinaa.shah54/",
    "https://music.yandex/users/alinaa.shah54/playlists",
    "http://www.authorstream.com/alinaa.shah54/",
    "https://www.dailykos.com/user/alinaa.shah54",
    "http://forum.igromania.ru/member.php?username=alinaa.shah54",
    "https://www.interpals.net/alinaa.shah54",
    "https://www.mercadolivre.com.br/perfil/alinaa.shah54",
    "https://alinaa.shah54.omg.lol",
    "https://www.opennet.ru/~alinaa.shah54",
    "https://php.ru/forum/members/?username=alinaa.shah54",
    "https://www.svidbook.ru/user/alinaa.shah54",
    "https://www.threads.net/@alinaa.shah54",
    "https://www.baby.ru/u/alinaa.shah54",
]


def fetch_url(url: str) -> Dict:
    """Fetch a single URL and extract emails from the response."""
    result = {
        "url": url,
        "status": None,
        "emails": [],
        "error": None,
        "page_length": 0,
        "elapsed_ms": 0,
    }
    start = time.monotonic()
    try:
        resp = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        result["status"] = resp.status_code
        result["page_length"] = len(resp.text)
        result["emails"] = extract_emails(resp.text)
    except requests.exceptions.Timeout:
        result["error"] = "Timeout"
    except requests.exceptions.ConnectionError as exc:
        result["error"] = f"ConnectionError: {exc.__class__.__name__}"
    except requests.exceptions.RequestException as exc:
        result["error"] = f"{exc.__class__.__name__}: {exc}"
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"{exc.__class__.__name__}: {exc}"
    result["elapsed_ms"] = round((time.monotonic() - start) * 1000, 1)
    return result


def main() -> None:
    print(f"[*] Scanning {len(PROFILE_URLS)} profile URLs for exposed emails...")
    print(f"[*] Concurrency: {MAX_WORKERS} workers | Timeout: {TIMEOUT}s")
    print("-" * 70)

    results: List[Dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_map = {pool.submit(fetch_url, url): url for url in PROFILE_URLS}
        for future in concurrent.futures.as_completed(future_map):
            url = future_map[future]
            try:
                res = future.result()
            except Exception as exc:  # noqa: BLE001
                res = {"url": url, "status": None, "emails": [], "error": str(exc)}
            results.append(res)

            status_icon = "✉" if res["emails"] else ("✓" if res["status"] else "✗")
            email_str = ", ".join(res["emails"]) if res["emails"] else "—"
            err_str = f" [{res['error']}]" if res["error"] else ""
            print(
                f"  {status_icon} [{res['status']}] {url}\n"
                f"      emails: {email_str}{err_str}"
            )

    # Sort results: emails first, then by URL.
    results.sort(key=lambda r: (not r["emails"], r["url"]))

    # Summary
    print("-" * 70)
    total = len(results)
    with_emails = [r for r in results if r["emails"]]
    errors = [r for r in results if r["error"]]
    print(f"[*] Scan complete: {total} URLs checked")
    print(f"[*] URLs with exposed emails: {len(with_emails)}")
    print(f"[*] URLs with errors: {len(errors)}")

    all_emails = set()
    for r in with_emails:
        all_emails.update(r["emails"])
    if all_emails:
        print(f"\n[!!!] EXPOSED EMAIL ADDRESSES FOUND:")
        for email in sorted(all_emails):
            print(f"  • {email}")
        print(f"\n[*] These emails appeared on public profile pages.")
    else:
        print("\n[*] No email addresses found on any profile page.")

    # Save full report to JSON.
    out_path = Path(__file__).parent / "email_scan_results.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "username": "alinaa.shah54",
                "total_urls_scanned": total,
                "urls_with_emails": len(with_emails),
                "urls_with_errors": len(errors),
                "all_exposed_emails": sorted(all_emails),
                "results": results,
            },
            fh,
            indent=2,
            ensure_ascii=False,
        )
    print(f"\n[*] Full report saved to: {out_path}")


if __name__ == "__main__":
    main()
