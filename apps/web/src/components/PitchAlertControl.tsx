import { useEffect, useRef, useState } from "react";
import { ApiError, apiClient } from "../services/apiClient";

type PitchStatus = Awaited<ReturnType<typeof apiClient.getPitchAlertStatus>>;

export function PitchAlertControl({ farmId, onDelivered }: { farmId: string; onDelivered?: () => void }) {
  const [status, setStatus] = useState<PitchStatus>();
  const [statusError, setStatusError] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [countdown, setCountdown] = useState(0);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState("");
  const requestId = useRef<string>(undefined);

  useEffect(() => {
    let active = true;
    apiClient.getPitchAlertStatus(farmId).then((value) => {
      if (!active) return;
      setStatus(value);
      setCountdown(value.cooldownSeconds ?? 0);
      setStatusError(false);
    }).catch(() => { if (active) setStatusError(true); });
    return () => { active = false; };
  }, [farmId, refresh]);

  useEffect(() => {
    if (countdown === 0) return;
    const timer = window.setTimeout(() => setCountdown(countdown - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [countdown]);

  async function send() {
    if (busy || !status?.connected || countdown > 0 || statusError) return;
    setBusy(true);
    setResult("");
    requestId.current ??= crypto.randomUUID();
    try {
      const receipt = await apiClient.sendPitchAlert(farmId, requestId.current);
      requestId.current = undefined;
      if (!receipt.sent) {
        setResult("Telegram delivery was not confirmed.");
        return;
      }
      setResult("Sample rainfall watch delivered to the connected Telegram chat.");
      setCountdown(90);
      onDelivered?.();
    } catch (error) {
      if (error instanceof ApiError && error.status > 0 && error.status < 500) requestId.current = undefined;
      setResult(error instanceof Error ? error.message : "Telegram delivery could not be verified.");
    } finally {
      setBusy(false);
      setRefresh((value) => value + 1);
    }
  }

  return <section className="form-panel rainfall-watch" aria-label="Rainfall Watch">
    <h3>Rainfall Watch</h3>
    <details>
      <summary>Preview a sample alert</summary>
      <p><strong>Illustrative scenario.</strong> Rain is expected in this example. Check field drainage and review planned irrigation before watering.</p>
    </details>
    {!status && !statusError && <p role="status">Checking manual delivery…</p>}
    {statusError && <p role="status">Manual delivery status is unavailable. <button type="button"
      className="secondary-button" onClick={() => setRefresh((value) => value + 1)}>Retry status</button></p>}
    {status?.available && <div className="form-actions">
      <button className="primary-button" type="button" disabled={busy || statusError || !status.connected || countdown > 0}
        onClick={() => void send()}>{busy ? "Sending…" : "Send sample to Telegram"}</button>
      {!status.connected && <p>Connect Telegram for this farm first.</p>}
      {countdown > 0 && <p>Next send available in {countdown}s.</p>}
    </div>}
    {status && !status.available && !statusError && <p>Manual Telegram delivery is unavailable for this farm.</p>}
    {result && <p role="status">{result}</p>}
  </section>;
}
