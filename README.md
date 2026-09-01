# Graduate Roles Tracker

I'm a second-year Business Economics student at Exeter, and after a
conversation with the Lead AI Business Analyst at Peel Hunt about building
practical AI projects worth putting on a CV, I built this: a tool that
solves a problem I actually have.

Graduate and internship schemes for the firms I'm targeting open at
different times across the year — some on fixed autumn windows, some
rolling, some with no announced date at all — and it's easy to miss when
one goes live. This tracks a shortlist of companies' careers pages and
pings me on Telegram the moment a new role appears, so I don't have to
manually check a dozen sites every week.

It runs automatically once a day via GitHub Actions — no server, no cost.

## How it works

1. `companies.json` lists the firms to track, each with a `method` telling
   the script how to read that company's job board:
   - **`json_api`** — the company's applicant tracking system (BambooHR,
     Greenhouse, SmartRecruiters, etc.) exposes a clean, public JSON
     endpoint. No HTML scraping, nothing to break on a redesign. Best case.
   - **`workday`** — Workday-hosted boards don't expose roles in the page
     HTML at all; the script POSTs to Workday's internal jobs API instead.
   - **`static`** — plain HTML, scraped with a CSS selector.
   - **`dynamic`** — the page needs a real (headless) browser via
     Playwright, for sites that render roles with JavaScript or block
     plain HTTP requests.
2. `tracker.py` visits each company using the right method, extracts the
   current list of open roles, and compares it against what was saved on
   the previous run (`state/<company>.json`).
3. Anything new triggers a Telegram message with the role name and a link.
4. The workflow commits the updated state back to the repo, so the next
   run has something to compare against.

## Companies currently tracked

| Company | Method | Notes |
|---|---|---|
| Panmure Liberum | `json_api` (BambooHR) | Currently 2 standing "Expression of Interest" postings |
| Stifel | `static` (iCIMS) | Global board, not just Europe/London |
| Artemis Investment Management | `static` (text-change proxy) | No real jobs board — see below |
| Glencore UK | `json_api` (Greenhouse) | 2 live 2026/27 grad roles as of writing |
| Evercore (UK) | `json_api` (SmartRecruiters) | 7 live London roles as of writing |
| Quilter Cheviot | `static` (programme-type proxy) | Fixed programme list, not rolling postings |
| Jupiter Asset Management | `workday` | Investment 20/20 traineeships, rolling |

**Artemis and Quilter Cheviot are proxy signals, not precise ones.**
Artemis doesn't run its own recruitment — they source through Investment
20/20's annual cycle — so the tracker watches their careers page for any
text change as a "go check manually" nudge. Quilter Cheviot's public page
lists fixed programme types rather than individual rolling vacancies, so
it flags if a new programme type appears. Treat notifications from these
two differently from the others.

## Setup

**1. Install dependencies locally (to test before automating):**
```bash
pip install -r requirements.txt
playwright install chromium
```

**2. Create a Telegram bot for notifications:**
- Message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`,
  follow the prompts — you'll get a bot token.
- Message your new bot anything (so it can message you back), then visit
  `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser to find
  your `chat_id` in the response.

**3. Add secrets and automate:**
- Push this repo to GitHub
- In repo **Settings → Secrets and variables → Actions**, add
  `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
- The workflow in `.github/workflows/track.yml` runs daily automatically —
  trigger it manually from the **Actions** tab to test.

**4. Adding another company:**
Most finance/professional firms outsource their job board to a
third-party ATS (BambooHR, iCIMS, Greenhouse, SmartRecruiters, Workday,
Lever) rather than building their own. These almost always expose either
a clean JSON endpoint or simple, stable HTML — much easier to track than
a custom-built page. To add one:
1. Go to the company's careers page and click through to wherever the
   actual role listings are (not the marketing "why work here" page).
2. Check the URL it lands on for a recognisable ATS domain.
3. Add an entry to `companies.json` with that URL and the right `method`.

Test locally with `python tracker.py` and check the console output before
trusting the automation.

## Notes

- First run on any company just saves a baseline — it won't notify about
  roles that were already open, only new ones from the second run onward.
- If a company redesigns their site or changes ATS, that company's scrape
  fails gracefully (logged as an error, other companies still checked)
  rather than breaking the whole run.
