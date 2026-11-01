# Setup: Telegram → Google Sheets Finance Agent

This agent receives Telegram messages, parses them with Google Gemini 3.6-flash,
and appends a row to the **Log** sheet in your Google Sheet.

## Step 1 — Your Gemini API key

Your key starting with `AQ.` is valid — it works. No action needed.

## Step 2 — Your Google Sheet

Your Sheet ID is: `1ilVtoeiti2V4ksGGydc_wK-x-Re3dsNga5wot7uBYFU`
(From: https://docs.google.com/spreadsheets/d/1ilVtoeiti2V4ksGGydc_wK-x-Re3dsNga5wot7uBYFU/edit)

No action needed — I have it.

## Step 3 — Create a Google Service Account

1. Go to https://console.cloud.google.com
2. Create a project (or use an existing one)
3. Enable the **Google Sheets API** (APIs & Services → Library → search "Google Sheets API" → Enable)
4. Go to **APIs & Services → Credentials** → **Create Credentials → Service account**
5. Name it (e.g. `finance-agent`), create
6. Click the new service account → **Keys** tab → **Add key → Create new key**
7. Choose **JSON** → **Create**
8. A `.json` file downloads. **Keep it safe** — it contains the key.
9. Copy the service account **email** (looks like `name@project.iam.gserviceaccount.com`) and give it to me.

## Step 4 — Share the sheet with the service account

1. In your Google Sheet, click **Share** (top right)
2. Paste the service account email from Step 3
3. Set permission to **Editor** (or at least "Viewer" + allow write)
4. Click **Send**

## Step 5 — Deploy on Render

1. Go to https://render.com → sign up (free)
2. **New → Web Service**
3. Connect your GitHub repo (or drag the `finance-agent/` folder)
4. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn -w 2 -b 0.0.0.0:8080 app:app`
   - **Environment:** `python 3.12`
5. Add these **Environment Variables**:
   - `TELEGRAM_BOT_TOKEN` = your bot token
   - `GEMINI_API_KEY` = your new Gemini key
   - `GOOGLE_SHEET_ID` = the Sheet ID from Step 2
   - `GOOGLE_SERVICE_ACCOUNT_JSON` = the **full contents** of the service account JSON file from Step 3
6. Click **Create Web Service**
7. Copy the deployed URL (e.g. `https://finance-agent.onrender.com`)

## Step 6 — Set the Telegram webhook

In BotFather (or via Telegram), run:

```
/setwebhook
```

Then paste: `<your-render-url>/webhook`

Example: `https://finance-agent.onrender.com/webhook`

## Step 7 — Test

Send a Telegram message to your bot:

```
I paid the monthly internet bill, 1000.
```

You should get a reply like:

```
Logged: 01/11/2026 | Outcome | 1000 | Monthly Bills | Internet Bill
```

Then open your Google Sheet → **Log** tab → a new row should appear.

## Troubleshooting

- **"Invalid API key"** from Gemini → your key doesn't start with `AIza`. Get a new one.
- **"Permission denied"** on the sheet → re-share it with the service account email as Editor.
- **No row appears** → check the service account JSON is pasted correctly into the env var (no line breaks lost).
- **Bot doesn't reply** → verify the webhook URL in BotFather matches your Render URL exactly.