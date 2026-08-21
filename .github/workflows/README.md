# Graduate Roles Tracker

Deadlines for the graduate and internship schemes I care about open at
different times across the year, and it's easy to miss when one goes live.
This tracks a shortlist of companies' careers pages and pings me on Telegram
the moment a new role appears.

It runs automatically once a day via GitHub Actions — no server, no cost.

## How it works

1. `companies.json` lists the firms to track, their careers page URL, and
   whether the page needs simple HTML scraping or a full browser (for
   JavaScript-heavy sites).
2. `tracker.py` visits each page, extracts the current list of open roles,
   and compares it against what was saved on the previous run
   (`state/<company>.json`).
3. Anything new triggers a Telegram message with the role name and a link.
4. The workflow commits the updated state back to the repo, so the next run
   has something to compare against.

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

**3. All three companies are now configured:**
- **Panmure Liberum** (BambooHR JSON API) and **Stifel** (iCIMS, static HTML)
  are fully verified — real endpoints, real selectors, ready to run.
- **Artemis is a different situation.** Their own careers page confirms
  they don't run direct recruitment or a jobs board at all — entry-level
  roles go through **Investment 2020**, an industry-wide scheme that runs
  one annual application cycle rather than posting individual roles on a
  rolling basis. There's no "new role opened" event to detect here.
  Instead, `tracker.py` watches the Artemis careers page's text for *any
  change* (using a broad heading selector) as a proxy signal — e.g. if the
  wording shifts from "applications closed" toward something about the
  next intake opening. Treat a notification from this one as "something
  changed here, go check manually" rather than "a specific new role
  exists", since it's a fundamentally noisier signal than the other two.

**Finding a fourth company (or replacing Artemis with one that has a
real board):**
If you're stuck copying selectors from Inspect, there's usually a faster
route than reading raw HTML — many finance/professional firms don't build
their own job board, they use a third-party ATS (BambooHR, iCIMS,
Greenhouse, Lever, Workday). These almost always expose either a clean
JSON endpoint or simple, stable HTML — much easier to scrape than a
custom-built page. To find which one a company uses:
1. Go to the company's careers page and click through to wherever the
   actual role listings are (not the marketing "why work here" page).
2. Look at the URL — if it changes to something like
   `*.bamboohr.com/careers`, `*.icims.com`, `boards.greenhouse.io/*`,
   or `jobs.lever.co/*`, you've found the ATS.
3. Come back and paste that URL into a chat with Claude — Claude can
   fetch it directly and identify the right selector or JSON field for
   you, the same way this file was built.

Once you have a selector, test locally with `python tracker.py` and check
the console output before trusting the automation.

**4. Automate it:**
- Push this repo to GitHub
- In the repo settings → **Secrets and variables → Actions**, add
  `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
- The workflow in `.github/workflows/track.yml` runs daily automatically —
  you can also trigger it manually from the **Actions** tab to test it.

## Notes

- First run on any company just saves a baseline — it won't notify you about
  roles that were already open, only new ones from the second run onward.
- If a company redesigns their site, the selector will stop matching and
  that company's scrape will fail gracefully (logged as an error, other
  companies still checked) rather than breaking the whole run.
