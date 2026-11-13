# TerraPulse — Rainfall Watch for Pitch + Sourced Agricultural Alerts

This adds a **single-click Rainfall Watch scenario** to the existing farm workspace and
an authenticated operator fallback. Messages are **not** inserted into real
`farmer_alerts` or `telegram_deliveries` records and cannot be mistaken for real
weather evidence. The text ends with a single unobtrusive disclosure:
`Scenario illustration · Not a live weather forecast`.

## What changes

- Farm workspace: **Send rainfall watch** appears ONLY for the allowlisted pitch farm.
- Source of authorization: existing private workspace bearer credential; never a
  publicly exposed admin secret in browser code.
- Recipient: the first active opted-in Telegram subscriber for this farm. No
  broadcasting, no contact import, no arbitrary chat IDs.
- Rate limits: 90-second cooldown and maximum 4 attempts per rolling 24 hours.
- Send receipt: separate `telegram_pitch_sends` table via migration `0009`.
- Operator fallback: `POST /api/v1/telegram/pitch-send` secured by `CRON_SECRET`,
  allowlisted to the same farm; for test chats created from separate workspaces.
- Optional genuine advisory feed: Preview-enabled daily refresh of up to **2**
  subscribed farm plots from the existing Open-Meteo/SoilGrids service. This
  produces provenance-backed environmental snapshots, not generated warnings.
  Rainfall messages require a real forecast >= 20 mm in the next 3 days; science
  alerts still require a matching actual C3 state. If neither meets the rules,
  **no genuine warning is sent**.

## Activation (Preview only first)

1. Push this patch to `integration/terrapulse-full-20261113`. Do not merge into `main` yet.
2. Apply Alembic revision `0009_pitch_alert_receipts` to **integration Neon only**.
3. In Vercel Preview environment add:
   - `TERRAPULSE_PITCH_ALERTS_ENABLED=1`
   - `TERRAPULSE_PITCH_FARM_ID=<the already opted-in pitch farm UUID>`
   - `TERRAPULSE_PITCH_EXPIRES_AT=<UTC RFC3339 timestamp after the pitch>`
   - `TERRAPULSE_ALERT_REFRESH_ENABLED=1`
   Do not add `CRON_SECRET` or Telegram bot token to the browser bundle.
4. Deploy the exact Git commit to Preview and verify the `GET` status endpoint
   for an owned farm, plus an unauthorized POST yielding 401/404.
5. If the pitch farm was registered with a temporary browser key that's now lost,
   either register and connect a new farm in your normal laptop browser, or use
   the **server-only** operator fallback with the existing Preview `CRON_SECRET`.
6. Trigger once using the farm UI; check Telegram and the stored receipt's
   `telegram_message_id`. A repeat within 90 seconds must return 429 and send nothing.
7. Invoke the existing `GET /api/v1/telegram/cron` using the Preview cron secret
   and verify refresh counts and real alert results. The official Vercel Hobby
   Cron runs only on Production; Preview can be triggered manually.

### Operator fallback (never expose secret to the browser)

POST `/api/v1/telegram/pitch-send` with `Authorization: Bearer <CRON_SECRET>` and
JSON `{ "farmId": "<allowlisted farm UUID>", "requestId": "<new random UUID>" }`.
Only use from a trusted local terminal or approved server operator. The HTTP API
still enforces the same opt-in, allowlist, expiry and rate limits.

### Important limitations

- Telegram already has one active webhook in the integration Preview: preserve it.
  Do **not** call `setWebhook` again or enable polling.
- Sending the scenario is not evidence of weather risk. True weather alerts are
  grounded in retained provider provenance and 20 mm threshold.
- Native daily cron does not support urgent alerts on the free Hobby plan.
- Production database and integration migration must be verified before final
  deployment; keep the stable public alias untouched until acceptance.
- After the presentation, disable the Preview pitch feature or let the explicit
  expiry disable it automatically. Production pitch behavior should be opted in
  only if a scheduled pitch demonstration genuinely needs it.
