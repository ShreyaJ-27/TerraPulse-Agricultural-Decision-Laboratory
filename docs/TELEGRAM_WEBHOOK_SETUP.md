# TerraPulse Telegram: secure one-tap opt-in and daily alerts

This change adds two Vercel-compatible paths on the existing TerraPulse FastAPI app:

- `POST /api/v1/telegram/webhook` checks Telegram's secret header before reading the update. It commits the command's update ID and any subscription changes together. Repeated IDs get acknowledged without another command or greeting. Keep the polling worker stopped while webhook mode is active.
- `GET /api/v1/telegram/cron` reads persisted C1/C3 evidence and sourced regional profiles. It applies quiet hours, preferences, expiry and deduplication. Vercel Hobby runs native cron on Production deployments. The schedule in `vercel.json` is 03:00 UTC (08:30 IST), with hourly precision.
- `POST /api/v1/telegram/activate-webhook`: one-time authorized server-side registration of the Telegram HTTPS webhook for the environment you're deliberately activating. It refuses protected/unreachable endpoints.

## Settings and activation order

1. Check the database revision using the direct connection. A new database should reach `0010_telegram_browser_reconnect` with `python -m alembic upgrade head`. The existing integration Neon database already has this revision. Revision `0005_farmer_alerts` provides the subscriptions and delivery outbox.
2. Vercel project secrets required: `TELEGRAM_BOT_TOKEN` (existing), `TELEGRAM_WEBHOOK_SECRET` (new, random URL-safe token), `CRON_SECRET` (new, random token), plus `TELEGRAM_BOT_USERNAME=Batyond_bot`. Keep all secrets in Vercel; never commit or print values.
3. Set `TERRAPULSE_TELEGRAM_ENABLED=1` **only in the environment whose webhook will be activated**, after verifying its API deployment, DB migrations, and public route availability. Leave it disabled elsewhere until switching the active bot.
4. The Preview may be protected by Vercel Authentication. Telegram cannot follow an interactive login or share-cookie; the activation endpoint checks whether the webhook can actually be reached without Vercel credentials. A protected Preview **must not** be activated until you have an explicitly approved publicly reachable endpoint.
5. With `CRON_SECRET` available to the authorized operator, call `POST /api/v1/telegram/activate-webhook` with `Authorization: Bearer <CRON_SECRET>` against the selected environment. The endpoint verifies anonymous reachability before registering the webhook. Telegram allows one webhook per bot. If Preview and Production use the same bot, registration switches its webhook to the selected deployment.
6. Complete opt-in: register a **synthetic** farm using a separate browser workspace key, select **Connect Telegram**, open the one-time deep link and press Start in Telegram. Verify the `telegram_subscriptions` row exists, active, with the opted-in chat; verify the Telegram acknowledgment message ID using the Bot API response or logs. Never insert a real user's chat ID or subscription without consent.
7. Verify delivery using a sourced alert and `GET /api/v1/telegram/cron` under the secure cron bearer token; confirm `telegram_deliveries.telegram_message_id`, preferences, ` /stop` suppression, and no duplicate send on retry. Do not seed fabricated agronomic alert evidence merely to make demo messages appear.
8. **Production still needs its authorized Neon DATABASE_URL and migrations.** Do not enable Production or promote a Preview until this is configured and independently verified.

## Security and operational caveats

- In a private chat with an active farm subscription, `/open` issues a one-use link that expires after ten minutes. The browser redeems it to access the existing farm records. `/stop` invalidates unused links and stops alerts. Previously recovered browsers retain their access.
- Set `TERRAPULSE_FARM_ORIGIN` in the webhook's server environment when its saved-farm links should use a specific HTTPS site. The destination must serve the candidate recovery page and use the same database as the webhook. Vercel deployments otherwise use their branch or deployment URL. Check the active webhook environment before enabling this on a hosted site.
- Use an isolated Preview with a disposable database and simulated Telegram to verify a candidate without switching the active bot. The existing pitch allowlist governs illustrative Rainfall Watch sends. Genuine alerts use the cron evidence path.

- Telegram's two update transports (`getUpdates` vs `setWebhook`) are mutually exclusive. Do not run the old worker in polling mode concurrently with the webhook.
- Telegram `sendMessage` has no general idempotency key. A crash after an external send but before outbox acknowledgment can cause a rare duplicate; the app deduplicates on its own side but **cannot guarantee exactly-once external delivery**.
- Hobby daily cron does **not** implement timely severe-weather alerts. Wording must say **daily checks**, and the demonstration should explain that short-latency alerts require a suitable worker/scheduler on an allowed free host or a different plan. Do not advertise more frequent updates.
- Vercel Preview supports a manual scheduler demo through the authorized cron endpoint. For unattended daily runs without a paid service, an existing always-on computer can run Windows Task Scheduler or system cron against the same Preview URL. Pass the Preview bearer secret from the task's private environment as the `Authorization` header. The computer must be online at the scheduled time.
- No paid service, extra database, or extra bot is created. The webhook-admin endpoint is guarded by `CRON_SECRET` and a public reachability probe. Do not rotate secrets or run `setWebhook` on Production during Preview testing.
- This patch is designed for the integration branch `integration/terrapulse-full-20261113`, not for direct changes to `main` or the production alias.
