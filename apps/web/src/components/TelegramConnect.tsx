/** One-time Telegram connection immediately after successful farm registration.
 *  TerraPulse does not ask the farmer to issue commands for every notification.
 *  Use the telegramConnectUrl returned by POST /api/v1/farms.
 */
export function TelegramConnect({ url }: { url?: string | null }) {
  if (!url) return null; // Telegram is optional: don't block onboarding.
  if (!/^https:\/\/t\.me\/[A-Za-z0-9_]+\?start=[A-Za-z0-9_-]{16,64}$/.test(url)) {
    return null; // Don't render an arbitrary URL from API payloads.
  }
  return (
    <section aria-label="Receive farm updates on Telegram">
      <p><strong>Get farm reminders automatically</strong></p>
      <p>Connect Telegram once. TerraPulse will send helpful crop and weather updates when relevant.</p>
      <a href={url} target="_blank" rel="noopener noreferrer">
        Connect Telegram
      </a>
      <p style={{ fontSize: "0.875em", opacity: 0.75 }}>
        Telegram asks you to press Start once to connect. You can stop alerts anytime.
      </p>
    </section>
  );
}
