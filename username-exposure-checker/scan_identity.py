"""Identity exposure scanner.

Fetches each sherlock-found profile URL and extracts identity-revealing
information: real names, locations, phone numbers, bios, social cross-links,
profile photos, and other PII patterns.
"""
from __future__ import annotations

import concurrent.futures
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests

sys.path.insert(0, str(Path(__file__).parent))
from email_scan import extract_emails

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
MAX_WORKERS = 6

# --- PII / identity regex patterns ---

# Email (reuse from email_scan)
# Phone numbers (international-ish): +XX, (XXX) XXX-XXXX, etc.
PHONE_REGEX = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?"           # country code
    r"\(?\d{2,4}\)?[\s.-]?"             # area code
    r"\d{3,4}[\s.-]?\d{3,4}"            # local number
    r"(?:\s?(?:ext|x)\.?\s?\d{1,5})?",  # extension
    re.IGNORECASE,
)

# Dates of birth / birthdates: "born on", "DOB", "birthday", date patterns
DOB_REGEX = re.compile(
    r"(?:born(?:\s+on)?|DOB|date\s+of\s+birth|birthday)\s*[:\-]?\s*"
    r"(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4}|\d{4}[/\.\-]\d{1,2}[/\.\-]\d{1,2}|"
    r"\w+\s+\d{1,2},?\s+\d{4})",
    re.IGNORECASE,
)

# Age: "age: 25", "I am 25", "25 years old"
AGE_REGEX = re.compile(
    r"(?:age\s*[:\-]?\s*(\d{2,3})|I\s+am\s+(\d{2,3})|(\d{2,3})\s+years\s+old)",
    re.IGNORECASE,
)

# Postal/ZIP codes (US + generic)
ZIP_REGEX = re.compile(r"\b(\d{5}(?:-\d{4})?)\b")

# Coordinates (lat, long)
COORD_REGEX = re.compile(
    r"-?\d{1,3}\.\d{2,8}\s*,\s*-?\d{1,3}\.\d{2,8}"
)

# Social media handles cross-referenced
SOCIAL_PATTERNS = {
    "twitter": re.compile(r"(?:twitter|x)\.com/([A-Za-z0-9_]{1,15})", re.IGNORECASE),
    "instagram": re.compile(r"instagram\.com/([A-Za-z0-9_.]{1,30})", re.IGNORECASE),
    "facebook": re.compile(r"facebook\.com/([A-Za-z0-9.]{5,50})", re.IGNORECASE),
    "linkedin": re.compile(r"linkedin\.com/in/([A-Za-z0-9\-_]{5,50})", re.IGNORECASE),
    "github": re.compile(r"github\.com/([A-Za-z0-9\-_]{1,39})", re.IGNORECASE),
    "youtube": re.compile(r"youtube\.com/(@[A-Za-z0-9_\-]{1,30}|user/[A-Za-z0-9_\-]{1,30}|channel/[A-Za-z0-9_\-]{1,30})", re.IGNORECASE),
    "telegram": re.compile(r"t\.me/([A-Za-z0-9_]{5,32})", re.IGNORECASE),
    "snapchat": re.compile(r"snapchat\.com/add/([A-Za-z0-9_]{3,15})", re.IGNORECASE),
    "discord": re.compile(r"discord(?:\.gg|\.com/users)/([A-Za-z0-9_]{2,32})", re.IGNORECASE),
    "tiktok": re.compile(r"tiktok\.com/@([A-Za-z0-9_.]{1,24})", re.IGNORECASE),
    "threads": re.compile(r"threads\.net/@([A-Za-z0-9_.]{1,30})", re.IGNORECASE),
    "mastodon": re.compile(r"([A-Za-z0-9_]{2,30})@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})", re.IGNORECASE),
}

# Real-name hints: "name is", "my name", "I'm", profile meta tags
NAME_HINT_REGEX = re.compile(
    r"(?:my\s+name\s+is\s+|I\s+am\s+|I'm\s+|name\s*[:\-]\s*)"
    r"([A-Z][a-z]{2,15}(?:\s+[A-Z][a-z]{2,15}){0,3})",
    re.IGNORECASE,
)

# og:title / profile name from meta tags
OG_TITLE_REGEX = re.compile(
    r'<meta\s+(?:property|name)=["\']og:title["\']\s+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
OG_DESC_REGEX = re.compile(
    r'<meta\s+(?:property|name)=["\']og:description["\']\s+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
PROFILE_NAME_REGEX = re.compile(
    r'<meta\s+(?:property|name)=["\']profile:(?:first|last)_name["\']\s+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
TWITTER_CARD_TITLE = re.compile(
    r'<meta\s+name=["\']twitter:title["\']\s+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)

# Location hints
LOCATION_HINT_REGEX = re.compile(
    r"(?:location|city|country|hometown|lives?\s+in|based\s+in|from)\s*[:\-]?\s*"
    r"([A-Z][a-z]{2,20}(?:,\s*[A-Z][a-z]{2,20})?(?:,\s*[A-Z][a-z]{2,20})?)",
    re.IGNORECASE,
)

# Occupation / employer
OCCUPATION_REGEX = re.compile(
    r"(?:occupation|job|title|employer|works?\s+at|company)\s*[:\-]?\s*"
    r"([A-Z][A-Za-z0-9\s&.,]{2,40})",
    re.IGNORECASE,
)

# Profile image URLs
IMG_REGEX = re.compile(
    r'<meta\s+(?:property|name)=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)

# Bio / about text
BIO_REGEX = re.compile(
    r'<meta\s+(?:property|name)=["\']description["\']\s+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def _clean(text: str) -> str:
    """Strip HTML entities and whitespace."""
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#39;", "'", text)
    text = re.sub(r"&nbsp;", " ", text)
    return text.strip()


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def extract_identity(html: str, url: str) -> Dict:
    """Extract identity-revealing signals from page HTML."""
    identity: Dict = {
        "emails": [],
        "phones": [],
        "real_name_hints": [],
        "og_title": None,
        "og_description": None,
        "twitter_card_title": None,
        "profile_names": [],
        "location_hints": [],
        "occupation_hints": [],
        "age_hints": [],
        "dob_hints": [],
        "social_links": {},
        "profile_image": None,
        "bio": None,
        "coordinates": [],
    }

    if not html:
        return identity

    # Emails
    identity["emails"] = extract_emails(html)

    # Phones (filter out very short / obvious non-phone numbers)
    raw_phones = PHONE_REGEX.findall(html)
    phones = []
    for p in raw_phones:
        digits = re.sub(r"\D", "", p)
        if 7 <= len(digits) <= 15:
            phones.append(p.strip())
    identity["phones"] = _dedupe(phones)[:10]

    # Meta-tag based (most reliable for profile pages)
    m = OG_TITLE_REGEX.search(html)
    if m:
        identity["og_title"] = _clean(m.group(1))
    m = OG_DESC_REGEX.search(html)
    if m:
        identity["og_description"] = _clean(m.group(1))
    m = TWITTER_CARD_TITLE.search(html)
    if m:
        identity["twitter_card_title"] = _clean(m.group(1))
    for m in PROFILE_NAME_REGEX.finditer(html):
        identity["profile_names"].append(_clean(m.group(1)))
    identity["profile_names"] = _dedupe(identity["profile_names"])

    # Bio / description meta
    m = BIO_REGEX.search(html)
    if m:
        identity["bio"] = _clean(m.group(1))

    # Profile image
    m = IMG_REGEX.search(html)
    if m:
        identity["profile_image"] = _clean(m.group(1))

    # Real-name hints from body text
    for m in NAME_HINT_REGEX.finditer(html):
        identity["real_name_hints"].append(_clean(m.group(1)))
    identity["real_name_hints"] = _dedupe(identity["real_name_hints"])[:10]

    # Location hints
    for m in LOCATION_HINT_REGEX.finditer(html):
        identity["location_hints"].append(_clean(m.group(1)))
    identity["location_hints"] = _dedupe(identity["location_hints"])[:10]

    # Occupation hints
    for m in OCCUPATION_REGEX.finditer(html):
        identity["occupation_hints"].append(_clean(m.group(1)))
    identity["occupation_hints"] = _dedupe(identity["occupation_hints"])[:10]

    # Age
    for m in AGE_REGEX.finditer(html):
        for g in m.groups():
            if g and g.isdigit():
                identity["age_hints"].append(g)
    identity["age_hints"] = _dedupe(identity["age_hints"])[:5]

    # DOB
    for m in DOB_REGEX.finditer(html):
        identity["dob_hints"].append(_clean(m.group(1)))
    identity["dob_hints"] = _dedupe(identity["dob_hints"])[:5]

    # Coordinates
    identity["coordinates"] = _dedupe(COORD_REGEX.findall(html))[:5]

    # Social cross-links
    for platform, pattern in SOCIAL_PATTERNS.items():
        matches = pattern.findall(html)
        if matches:
            if isinstance(matches[0], tuple):
                # e.g. mastodon returns (user, host)
                cleaned = [f"{m[0]}@{m[1]}" for m in matches]
            else:
                cleaned = [str(m) for m in matches]
            identity["social_links"][platform] = _dedupe(cleaned)[:10]

    return identity


def fetch_and_scan(url: str) -> Dict:
    """Fetch a URL and run identity extraction."""
    result = {
        "url": url,
        "status": None,
        "error": None,
        "page_length": 0,
        "elapsed_ms": 0,
        "identity": {},
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
        result["identity"] = extract_identity(resp.text, url)
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


def _has_identity_signal(ident: Dict) -> bool:
    """Check if identity dict has any non-empty signal."""
    keys_to_check = [
        "emails", "phones", "real_name_hints", "og_title", "og_description",
        "twitter_card_title", "profile_names", "location_hints",
        "occupation_hints", "age_hints", "dob_hints", "bio",
        "profile_image", "coordinates",
    ]
    for key in keys_to_check:
        val = ident.get(key)
        if val:
            return True
    if ident.get("social_links"):
        return True
    return False


def main() -> None:
    print(f"[*] Identity scan: {len(PROFILE_URLS)} profile URLs")
    print(f"[*] Concurrency: {MAX_WORKERS} workers | Timeout: {TIMEOUT}s")
    print("=" * 72)

    results: List[Dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_map = {pool.submit(fetch_and_scan, url): url for url in PROFILE_URLS}
        for future in concurrent.futures.as_completed(future_map):
            url = future_map[future]
            try:
                res = future.result()
            except Exception as exc:  # noqa: BLE001
                res = {"url": url, "status": None, "error": str(exc), "identity": {}}
            results.append(res)

            ident = res.get("identity", {})
            has_signal = _has_identity_signal(ident)
            icon = "★" if has_signal else ("✓" if res.get("status") else "✗")
            print(f"  {icon} [{res.get('status')}] {url}")
            if has_signal:
                if ident.get("og_title"):
                    print(f"      og:title  : {ident['og_title']}")
                if ident.get("twitter_card_title"):
                    print(f"      tw:title  : {ident['twitter_card_title']}")
                if ident.get("profile_names"):
                    print(f"      names     : {ident['profile_names']}")
                if ident.get("real_name_hints"):
                    print(f"      name hints: {ident['real_name_hints']}")
                if ident.get("bio"):
                    print(f"      bio       : {ident['bio'][:150]}")
                if ident.get("location_hints"):
                    print(f"      location  : {ident['location_hints']}")
                if ident.get("occupation_hints"):
                    print(f"      occupation: {ident['occupation_hints']}")
                if ident.get("age_hints"):
                    print(f"      age       : {ident['age_hints']}")
                if ident.get("dob_hints"):
                    print(f"      dob       : {ident['dob_hints']}")
                if ident.get("emails"):
                    print(f"      emails    : {ident['emails']}")
                if ident.get("phones"):
                    print(f"      phones    : {ident['phones']}")
                if ident.get("profile_image"):
                    print(f"      photo     : {ident['profile_image'][:120]}")
                if ident.get("social_links"):
                    for plat, handles in ident["social_links"].items():
                        print(f"      {plat:10}: {handles}")
                if ident.get("coordinates"):
                    print(f"      coords    : {ident['coordinates']}")

    # Sort: signal-rich results first
    results.sort(key=lambda r: (not _has_identity_signal(r.get("identity", {})), r["url"]))

    # Aggregate all unique signals
    print("=" * 72)
    all_emails = set()
    all_phones = set()
    all_names = set()
    all_locations = set()
    all_occupations = set()
    all_ages = set()
    all_dobs = set()
    all_social = {}
    all_images = set()
    all_bios = set()
    all_og_titles = set()

    for r in results:
        ident = r.get("identity", {})
        all_emails.update(ident.get("emails", []))
        all_phones.update(ident.get("phones", []))
        all_names.update(ident.get("profile_names", []))
        all_names.update(ident.get("real_name_hints", []))
        all_locations.update(ident.get("location_hints", []))
        all_occupations.update(ident.get("occupation_hints", []))
        all_ages.update(ident.get("age_hints", []))
        all_dobs.update(ident.get("dob_hints", []))
        if ident.get("profile_image"):
            all_images.add(ident["profile_image"])
        if ident.get("bio"):
            all_bios.add(ident["bio"])
        if ident.get("og_title"):
            all_og_titles.add(ident["og_title"])
        for plat, handles in ident.get("social_links", {}).items():
            all_social.setdefault(plat, set()).update(handles)

    print("\n" + "=" * 72)
    print("[*] AGGREGATED IDENTITY EVIDENCE")
    print("=" * 72)

    def _print_set(label: str, items) -> None:
        if items:
            print(f"\n[{label}]")
            for item in sorted(items):
                print(f"  • {item}")

    _print_set("OG TITLES (profile page titles)", all_og_titles)
    _print_set("POSSIBLE REAL NAMES", all_names)
    _print_set("LOCATIONS", all_locations)
    _print_set("OCCUPATIONS / EMPLOYERS", all_occupations)
    _print_set("AGES", all_ages)
    _print_set("DATES OF BIRTH", all_dobs)
    _print_set("EMAILS", all_emails)
    _print_set("PHONE NUMBERS", all_phones)
    _print_set("PROFILE PHOTOS", all_images)
    _print_set("BIOS / DESCRIPTIONS", all_bios)

    if all_social:
        print("\n[CROSS-LINKED SOCIAL ACCOUNTS]")
        for plat, handles in sorted(all_social.items()):
            for h in sorted(handles):
                print(f"  • {plat}: {h}")

    if not (all_emails or all_phones or all_names or all_locations
            or all_occupations or all_ages or all_dobs or all_social or all_images):
        print("\n[*] No direct identity-revealing evidence found on public pages.")
        print("[*] Most profiles likely render via JavaScript (client-side) which")
        print("    plain HTTP scraping cannot capture. Consider manual inspection.")

    # Save full report
    out_path = Path(__file__).parent / "identity_scan_results.json"
    # Convert sets to sorted lists for JSON
    serializable = {
        "username": "alinaa.shah54",
        "total_urls_scanned": len(results),
        "aggregated": {
            "og_titles": sorted(all_og_titles),
            "possible_real_names": sorted(all_names),
            "locations": sorted(all_locations),
            "occupations": sorted(all_occupations),
            "ages": sorted(all_ages),
            "dates_of_birth": sorted(all_dobs),
            "emails": sorted(all_emails),
            "phones": sorted(all_phones),
            "profile_photos": sorted(all_images),
            "bios": sorted(all_bios),
            "social_links": {k: sorted(v) for k, v in all_social.items()},
        },
        "results": results,
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(serializable, fh, indent=2, ensure_ascii=False)
    print(f"\n[*] Full report saved to: {out_path}")


if __name__ == "__main__":
    main()
