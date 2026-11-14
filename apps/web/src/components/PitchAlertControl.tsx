import { useEffect, useState } from "react";
import { apiClient } from "../services/apiClient";

type PitchStatus = { available: boolean; connected?: boolean; cooldownSeconds?: number };

/** Only appears for the explicitly allowed farm; the server authorizes every send. */
export function PitchAlertControl({ farmId }: { farmId: string }) {
  const [status, setStatus] = useState<PitchStatus>();
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState("");

  useEffect(() => {
    let active = true;
    apiClient.getPitchAlertStatus(farmId)
      .then((value) => { if (active) setStatus(value); })
      .catch(() => { if (active) setStatus({ available: false }); });
    return () => { active = false; };
  }, [farmId]);

  if (!status?.available) return null;

  const send = async () => {
    if (busy) return;
    setBusy(true);
    setResult("");
    try {
      const receipt = await apiClient.sendPitchAlert(farmId, crypto.randomUUID());
      if (!receipt.sent) throw new Error("Telegram delivery was not confirmed.");
      setResult("Rainfall watch delivered to your connected Telegram.");
      setStatus({ ...status, cooldownSeconds: 90 });
    } catch (err) {
      setResult(err instanceof Error ? err.message : "The alert could not be delivered.");
    } finally {
      setBusy(false);
    }
  };

  return <section className="form-panel" aria-label="Rainfall watch presentation control">
    <p className="eyebrow">Rainfall watch</p>
    <h3>Send a rainfall watch to Telegram</h3>
    <p>Illustrate how TerraPulse delivers a timely field advisory to an opted-in farmer.</p>
    <button className="primary-button" type="button"
      disabled={busy || !status.connected || (status.cooldownSeconds ?? 0) > 0}
      onClick={send}>
      {busy ? "Sending…" : "Send rainfall watch ↗"}
    </button>
    {!status.connected && <p>Connect Telegram for this farm first.</p>}
    {(status.cooldownSeconds ?? 0) > 0 && <p>Alert sent recently. Reopen this farm after the cooldown to send again.</p>}
    {result && <p role="status">{result}</p>}
    <p style={{ fontSize: "0.875em", opacity: 0.7 }}>
      Scenario illustration · Not a live weather forecast
    </p>
  </section>;
}
