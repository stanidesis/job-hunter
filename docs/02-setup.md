# Setup Guide

Complete setup from scratch to a running daily email system.

---

## Prerequisites

- **Python 3.11+** installed
- A **[Resend](https://resend.com)** account for sending daily digest emails
- 10 minutes to get API keys

---

## Step 1: Install Python Dependencies

```bash
cd "D:/VSCode/job scraper"
pip install -r requirements.txt
```

Or with explicit Python path (Windows):
```bash
"C:/Users/you/AppData/Local/Programs/Python/Python313/python.exe" -m pip install -r requirements.txt
```

---

## Step 2: Get API Keys

### 2a. RapidAPI Key (for JSearch)

JSearch aggregates LinkedIn + Indeed + Glassdoor. **Free tier: 200 requests/month.**

1. Sign up at **https://rapidapi.com**
2. Subscribe to **JSearch**: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
3. Pick the **Free (Basic)** plan
4. Copy your `X-RapidAPI-Key` from the dashboard

### 2b. Hunter.io (optional — currently not used)

Was used for finding contact emails. Replaced with LinkedIn search URLs.
Key stays in `.env` for future use but can be empty.

### 2c. Resend API Key

Required for sending the daily digest email.

1. Sign up at **https://resend.com**
2. Go to **API Keys** → **Create API Key**
3. Copy the key (starts with `re_`)
4. For the **From** address:
   - **Quick start (free tier):** use `Job Hunter <onboarding@resend.dev>`
   - **Production:** add and verify your own domain under **Domains**, then use e.g. `Job Hunter <digest@yourdomain.com>`
5. For the **To** address (`RESEND_TO`): the inbox that receives the daily digest
   - On the free tier with `onboarding@resend.dev`, you can typically only send **to the email address of your Resend account**

Docs: https://resend.com/docs/send-with-python

---

## Step 3: Create `.env` File

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# JSearch (RapidAPI) — required
RAPIDAPI_KEY=your_rapidapi_key_here

# Hunter.io — optional, not currently used
HUNTER_API_KEY=

# Resend — required for daily email
RESEND_API_KEY=re_xxxxxxxx
RESEND_FROM=Job Hunter <onboarding@resend.dev>
RESEND_TO=you@example.com

# Daily digest timing (IST timezone)
DAILY_EMAIL_HOUR=9
DAILY_JOBS_COUNT=15

# Google Sheets export — optional
GOOGLE_SHEETS_CREDS=credentials.json
GOOGLE_SHEET_ID=
```

**Important:**
- `RESEND_API_KEY` is your Resend secret key (`re_…`)
- `RESEND_FROM` must be a verified sender (or `onboarding@resend.dev` on free tier)
- `RESEND_TO` is where the daily digest is delivered (the job seeker). Profiles can override this via `recipient_email`.

**Migrating from Gmail SMTP:** remove `SENDER_EMAIL`, `SENDER_APP_PASSWORD`, and `RECIPIENT_EMAIL` from `.env` and set the three `RESEND_*` variables above instead.

---

## Step 4: Initialize Database (auto on first run)

Not needed manually — the database auto-initializes when you start the server. Tables created:
- `jobs`
- `companies`
- `outreach`
- `search_queries` (seeded with 6 default queries)
- `email_log`
- `api_usage`

---

## Step 5: Start the Server

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
Scheduled daily digest at 9:00 IST
```

If Resend is not configured:
```
RESEND_API_KEY or RESEND_FROM not set in .env — daily digest disabled
```

---

## Step 6: Open Dashboard

Open browser: **http://127.0.0.1:8000**

You'll see the Jobs page with 0 jobs.

---

## Step 7: First Run — Collect Jobs

Click **"Collect Jobs"** button (top right).

Wait 1-2 minutes. You should see ~500-1000 new jobs appear.

---

## Step 8: Generate Outreach

Navigate to **http://127.0.0.1:8000/outreach**

Click **"Find Contacts for Top Jobs"**. You'll see 15 outreach cards created.

---

## Step 9: Send Test Email

Click **"Send Email Now"** on the outreach page.

Check the `RESEND_TO` inbox (or the profile recipient override). Email should arrive in a few seconds. You can also confirm delivery in the Resend dashboard under **Emails**.

---

## Step 10: Let the Daily Schedule Run

From now on, the system auto-runs every day at 9:00 AM IST:
1. Collects fresh jobs
2. Generates outreach for new top-scoring ones
3. Sends email via Resend

**Just keep the server running.** For 24/7 uptime, deploy to a small VPS (see below).

---

## Running on a Server (Optional)

To keep the daily schedule active, run on a VPS instead of your laptop.

### Option A: DigitalOcean / Hetzner VPS (~$5/mo)

```bash
# On the VPS
git clone <your-repo> job-scraper
cd job-scraper
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys

# Run as a systemd service
sudo cp deploy/job-scraper.service /etc/systemd/system/
sudo systemctl enable --now job-scraper
```

### Option B: Railway / Render (free tier)

Both offer free tier small apps. Create `Procfile`:

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

Add env vars in their dashboard (`RESEND_API_KEY`, `RESEND_FROM`, `RESEND_TO`, etc.).

### Option C: Keep your laptop on

If laptop is always on, leave the server running. Add to startup if needed.

---

## Troubleshooting

### "RESEND_API_KEY or RESEND_FROM not configured"

- Check `.env` has both values
- Restart the server after editing `.env`

### "Recipient email not configured"

- Set `RESEND_TO` in `.env`, **or**
- Set **Recipient Email** on the active profile (Profile page)

### Resend API errors (401 / 403 / validation)

- **401:** API key wrong or revoked — create a new key in the Resend dashboard
- **403 / domain not verified:** `RESEND_FROM` must use a verified domain, or `onboarding@resend.dev` on free tier
- **Free-tier recipient restriction:** with `onboarding@resend.dev`, you can usually only send to the email address on your Resend account. Verify a domain (or set `RESEND_TO` to that account email) for testing

### Email lands in Spam folder

- First email from a new sender often does
- Prefer a verified custom domain for better deliverability
- Tell recipient to mark as "Not Spam" once

### JSearch returns 403 / 429

- Rate limit hit. Free tier = 200/month.
- Check usage: `http://127.0.0.1:8000/api/jsearch/status`
