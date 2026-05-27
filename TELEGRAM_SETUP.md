# Telegram Integration Setup Guide

## Overview

This OSINT platform uses **Telethon** to monitor public Telegram channels in real-time. Messages are automatically translated from Arabic to Hebrew, geo-located, classified, and pushed live to the map.

---

## Step 1: Get your Telegram API credentials

1. Go to [https://my.telegram.org](https://my.telegram.org) and sign in with your Telegram account.
2. Click **API development tools**.
3. Fill in the form (app name can be anything, e.g. "OSINT Platform").
4. Copy your **API ID** (a number) and **API Hash** (a long hex string).

These credentials identify your application to Telegram. **Keep them secret.**

---

## Step 2: Set the environment secrets in Replit

In the Replit sidebar, open **Secrets** (padlock icon) and add:

| Secret name       | Value                            |
|-------------------|----------------------------------|
| `TELEGRAM_API_ID`  | Your API ID from my.telegram.org |
| `TELEGRAM_API_HASH` | Your API Hash from my.telegram.org |

Restart the API server workflow after setting these.

---

## Step 3: Authenticate your Telegram account

Go to the **Telegram** page in the OSINT platform and follow the 3-step wizard:

1. **Configure** — the platform confirms your API credentials are loaded.
2. **Request Code** — enter your phone number (international format, e.g. `+972501234567`). Telegram will send a code to your Telegram app.
3. **Verify Code** — enter the 6-digit code. If you have 2-factor authentication enabled, also enter your 2FA password.

The session is saved to `artifacts/api-server/data/telegram.session`. You only need to authenticate once; the session persists across restarts.

---

## Step 4: Add channels to monitor

On the **Telegram** admin page, click **Add Channel** and enter a channel username, for example:

- `@BreakingNewsAR`
- `t.me/QudsNewsN`
- `@gazawar_official`

The platform will begin monitoring those channels immediately. Every new message is:
1. Translated from Arabic to Hebrew
2. Classified (military / political / humanitarian / crime / accident / other)
3. Geo-located using place-name extraction
4. Stored in SQLite and pushed live to the map via SSE

---

## Notes and limits

- You must use a **real Telegram account** (a phone number that owns a Telegram account). Bot tokens do not work with Telethon for channel monitoring.
- The account must be a **member** of any private channel it wants to monitor. Public channels work without membership.
- Telegram enforces rate limits. Monitoring more than ~20 channels simultaneously is not recommended.
- The `telegram.session` file contains your active Telegram session. **Do not share it.**

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Telegram is not configured" | Set `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` in Replit Secrets and restart the server |
| "PhoneNumberInvalidError" | Use international format: `+countrycode number` |
| "SessionPasswordNeededError" | Enter your 2FA password in the verification step |
| Messages not appearing | Check that the account is a member of the channel; confirm channel username is correct |
| "FloodWaitError" | Telegram rate-limited the account; wait the indicated time and retry |
