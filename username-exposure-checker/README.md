# Username Exposure Checker

A Python CLI tool that checks where a given username is registered across the internet. It helps you audit your own digital footprint and verify whether your username could lead back to your email or identity.

> **⚠️ Privacy Disclaimer:** For checking your own accounts only. Do not use to investigate others.

---

## What the tool does

- Scans a username across **300+ sites** using [`sherlock-project`](https://github.com/sherlock-project/sherlock)
- Optionally fetches each found profile page and **scans the HTML for publicly exposed email addresses** (regex-based)
- Produces a **summary report** with a risk-level classification
- Supports **single** and **bulk** username scans
- Exports results to **JSON** or **CSV**

---

## Install

```bash
cd username-exposure-checker
pip install -r requirements.txt
```

### Requirements

- Python 3.10+
- `sherlock-project` — username lookup across 300+ sites
- `rich` — formatted terminal output
- `click` — CLI argument parsing
- `requests` — HTTP requests for email scanning

---

## Usage

### Single username scan

```bash
python main.py check johndoe
```

### Single scan — only show found sites, custom timeout

```bash
python main.py check johndoe --only-found --timeout 15
```

### Export results to JSON

```bash
python main.py check johndoe --output results.json
```

### Export results to CSV

```bash
python main.py check johndoe --output results.csv
```

### Bulk scan from a file

Create a text file with one username per line (`usernames.txt`):

```text
johndoe
janedoe
user123
```

Then run:

```bash
python main.py check-file usernames.txt
```

### Bulk scan with export and filtering

```bash
python main.py check-file usernames.txt --only-found --output results.json
```

### Skip email scanning (faster)

```bash
python main.py check johndoe --no-email-scan
```

---

## CLI options

| Option | Description |
|---|---|
| `check <username>` | Scan a single username |
| `check-file <filepath>` | Bulk scan usernames from a file (one per line) |
| `--only-found` | Show only sites where the username exists |
| `--timeout <seconds>` | Per-site request timeout (default: 10) |
| `--output <file>` | Export to `.json` or `.csv` |
| `--no-email-scan` | Skip fetching profile pages to scan for emails |

---

## Summary report

At the end of each scan, the tool prints a summary panel:

```
┌────────────────────────── Summary ───────────────────────────┐
│ Username: johndoe                                             │
│ Total sites checked: 312                                      │
│ Sites where username found: 18                                │
│ Sites with public email detected: 3                          │
│ Risk level: Medium                                            │
└──────────────────────────────────────────────────────────────┘
```

---

## How to interpret risk levels

| Risk level | Found profiles | Interpretation |
|---|---|---|
| **Low** | 0–5 | Your username has a minimal footprint. Low risk of being correlated back to your identity. |
| **Medium** | 6–15 | Your username appears on several platforms. Consider reducing your footprint or using different usernames. |
| **High** | 16+ | Your username is widely registered. High risk of cross-platform correlation and identity exposure. Review exposed emails carefully. |

### Tips to reduce exposure

- Use **different usernames** across platforms to prevent correlation.
- Avoid listing your email publicly on profile pages.
- Regularly audit which sites still hold your old accounts.
- Delete or anonymize accounts you no longer use.

---

## Project structure

```
username-exposure-checker/
├── main.py            # CLI entry point (click commands)
├── checker.py         # Core scanning logic (sherlock wrapper + email scan)
├── email_scan.py      # Email leak detection (regex-based HTML scan)
├── report.py          # Rich terminal output and summary rendering
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

---

## Privacy disclaimer

> **For checking your own accounts only. Do not use to investigate others.**

This tool is intended for personal digital-footprint auditing. Using it to investigate, stalk, or harass other individuals is unethical and may be illegal in your jurisdiction. The authors are not responsible for misuse of this tool.

---

## License

MIT
