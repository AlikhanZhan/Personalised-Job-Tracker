"""
Graduate Roles Tracker
-----------------------
Checks a list of companies' careers pages for open roles, compares against
what was seen last run, and sends a Telegram message for anything new.

Run manually:      python tracker.py
Run automatically:  see .github/workflows/track.yml
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

STATE_DIR = Path("state")
STATE_DIR.mkdir(exist_ok=True)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load_companies() -> list[dict]:
    with open("companies.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["companies"]


def scrape_static(url: str, selector: str) -> list[str]:
    """For plain-HTML pages. Returns a list of role title strings."""
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    elements = soup.select(selector)
    roles = [el.get_text(strip=True) for el in elements if el.get_text(strip=True)]
    return roles


def scrape_dynamic(url: str, selector: str) -> list[str]:
    """For JS-heavy pages. Requires Playwright + browsers installed."""
    from playwright.sync_api import sync_playwright

    roles = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle")
        elements = page.query_selector_all(selector)
        roles = [el.inner_text().strip() for el in elements if el.inner_text().strip()]
        browser.close()
    return roles


def scrape_json_api(url: str, role_field: str) -> list[str]:
    """For ATS platforms (like BambooHR) that expose a clean JSON endpoint.
    This is far more reliable than HTML scraping — no selectors to break."""
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    # BambooHR wraps the list in {"result": [...]}. Other ATSs vary —
    # adjust this line if you add a company with a different JSON shape.
    items = data.get("result", data if isinstance(data, list) else [])
    return [item.get(role_field, "").strip() for item in items if item.get(role_field)]


def scrape_company(company: dict) -> list[str]:
    if company["method"] == "json_api":
        return scrape_json_api(company["url"], company["role_field"])
    if company["method"] == "dynamic":
        return scrape_dynamic(company["url"], company["selector"])
    return scrape_static(company["url"], company["selector"])


def load_previous_state(slug: str) -> list[str]:
    path = STATE_DIR / f"{slug}.json"
    if not path.exists():
        return None  # None = never scraped before, distinct from []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(slug: str, roles: list[str]) -> None:
    path = STATE_DIR / f"{slug}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(roles, f, indent=2)


def send_telegram(message: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[warn] Telegram not configured — skipping notification.")
        print(message)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    })
    if not resp.ok:
        print(f"[error] Telegram send failed: {resp.status_code} {resp.text}")


def main():
    companies = load_companies()
    all_new = []
    errors = []

    for company in companies:
        name = company["name"]
        slug = slugify(name)
        print(f"Checking {name}...")

        try:
            current_roles = scrape_company(company)
        except Exception as e:
            print(f"[error] Failed to scrape {name}: {e}")
            errors.append(f"{name}: {e}")
            continue

        previous_roles = load_previous_state(slug)

        if previous_roles is None:
            print(f"  First run for {name} — saving baseline of {len(current_roles)} roles.")
        else:
            new_roles = [r for r in current_roles if r not in previous_roles]
            if new_roles:
                print(f"  {len(new_roles)} new role(s) found at {name}!")
                all_new.append((name, company["url"], new_roles))
            else:
                print(f"  No change ({len(current_roles)} roles, same as before).")

        save_state(slug, current_roles)

    if all_new:
        lines = ["🎓 <b>New graduate roles found!</b>", ""]
        for name, url, roles in all_new:
            lines.append(f"<b>{name}</b>")
            for r in roles:
                lines.append(f"  • {r}")
            lines.append(f"  {url}")
            lines.append("")
        send_telegram("\n".join(lines))
    else:
        print("No new roles this run.")

    if errors:
        print("\nErrors encountered:")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    main()
