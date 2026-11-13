# TerraPulse Telegram: secure one-tap opt-in and daily alerts

This change adds two Vercel-compatible paths on the existing TerraPulse FastAPI app:

- `POST /api/v1/telegram/webhook`: Telegram private-chat updates with validated `X-Telegram-Bot-Api-Secret-Token` header. One-use opt-in links are stored using existing `TelegramLink`/`TelegramSubscription` tables. `setWebhook(max_connections=1)` is used to keep webhook updates sequential; existing DB `telegram_update_cursor` prevents basic replays. Do **not** run the legacy `getUpdates` polling CLI while webhook mode is active.
- `GET /api/v1/telegram/cron`: uses the existing `evaluate_registered_farms` and `deliver_queued` services; reads persisted C1/C3/region profiles, applies quiet hours, preferences, expiry, and dedupe. Vercel Hobby can schedule it **once daily**, not every few minutes. `vercel.json` schedules it for `03:00 UTC` (approximately 08:30 IST, within Vercel's Hobby execution window).
- `POST /api/v1/telegram/activate-webhook`: one-time authorized server-side registration of the Telegram HTTPS webhook for the environment you're deliberately activating. It refuses protected/unreachable endpoints.

## Settings and activation order

1. Merge only after reviewing the branch and running the regression suite. Vercel Preview and Production share the same bot token in this project; **Telegram can have only one active webhook URL per bot**. Do not activate both environments simultaneously.
2. Vercel project secrets required: `TELEGRAM_BOT_TOKEN` (existing), `TELEGRAM_WEBHOOK_SECRET` (new, random URL-safe token), `CRON_SECRET` (new, random token), plus `TELEGRAM_BOT_USERNAME=Batyond_bot`. Keep all secrets in Vercel; never commit or print values.
3. Set `TERRAPULSE_TELEGRAM_ENABLED=1` **only in the environment whose webhook will be activated**, after verifying its API deployment, DB migrations, and public route availability. Leave it disabled elsewhere until switching the active bot.
4. The Preview may be protected by Vercel Authentication. Telegram cannot follow an interactive login or share-cookie; the activation endpoint checks whether the webhook can actually be reached without Vercel credentials. A protected Preview **must not** be activated until you have an explicitly approved publicly reachable endpoint.
5. With `CRON_SECRET` available to the authorized operator, call `POST /api/v1/telegram/activate-webhook` with `Authorization: Bearer <CRON_SECRET>` against the selected environment. Use the host's authenticated deployment testing workflow for protected Previews. The endpoint constructs an HTTPS URL from Vercel's trusted system environment, verifies anonymous reachability, then registers the webhook with Telegram. Do not paste `CRON_SECRET` into chat.
6. Complete opt-in: register a **synthetic** farm using a separate browser workspace key, select **Connect Telegram**, open the one-time deep link and press Start in Telegram. Verify the `telegram_subscriptions` row exists, active, with the opted-in chat; verify the Telegram acknowledgment message ID using the Bot API response or logs. Never insert a real user's chat ID or subscription without consent.
7. Verify delivery using a sourced alert and `GET /api/v1/telegram/cron` under the secure cron bearer token; confirm `telegram_deliveries.telegram_message_id`, preferences, ` /stop` suppression, and no duplicate send on retry. Do not seed fabricated agronomic alert evidence merely to make demo messages appear.
8. **Production still needs its authorized Neon DATABASE_URL and migrations.** Do not enable Production or promote a Preview until this is configured and independently verified.

## Security and operational caveats

- Telegram's two update transports (`getUpdates` vs `setWebhook`) are mutually exclusive. Do not run the old worker in polling mode concurrently with the webhook.
- Telegram `sendMessage` has no general idempotency key. A crash after an external send but before outbox acknowledgment can cause a rare duplicate; the app deduplicates on its own side but **cannot guarantee exactly-once external delivery**.
- Hobby daily cron does **not** implement timely severe-weather alerts. Wording must say **daily checks**, and the demonstration should explain that short-latency alerts require a suitable worker/scheduler on an allowed free host or a different plan. Do not advertise more frequent updates.
- Webhook update cursor assumes Telegram's `max_connections=1` and processing order. High-concurrency production needs a per-update durable inbox claim table to avoid losing out-of-order updates. This patch does not claim general high-scale delivery readiness.
- No paid service, extra database, or extra bot is created. The webhook-admin endpoint is guarded by `CRON_SECRET` and a public reachability probe. Do not rotate secrets or run `setWebhook` on Production during Preview testing.
- This patch is designed for the integration branch `integration/terrapulse-full-20261113`, not for direct changes to `main` or the production alias.
