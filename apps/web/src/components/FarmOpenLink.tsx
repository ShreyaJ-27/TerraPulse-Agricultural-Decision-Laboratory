import { useEffect, useRef, useState } from "react";
import { apiClient } from "../services/apiClient";
import { ErrorState, PageContainer } from "./ui";

type Props = { navigate: (route: string) => void };

/** Complete the one-tap Telegram link without putting its bearer token in HTTP URLs. */
export function FarmOpenLink({ navigate }: Props) {
  const [state, setState] = useState<"opening" | "error">("opening");
  const promiseRef = useRef<ReturnType<typeof apiClient.redeemFarmOpenLink> | null>(null);
  const initialToken = useRef<string | null>(null);
  if (initialToken.current === null) {
    initialToken.current = new URLSearchParams(window.location.hash.replace(/^#/, "")).get("open") || "";
  }
  useEffect(() => {
    const token = initialToken.current || "";
    // Remove secret immediately from the address bar/history before any request.
    window.history.replaceState({}, "", "/recover");
    if (!/^[A-Za-z0-9_-]{40,64}$/.test(token)) {
      setState("error");
      return;
    }
    let active = true;
    if (!promiseRef.current) promiseRef.current = apiClient.redeemFarmOpenLink(token);
    promiseRef.current
      .then(({ farmIds }) => {
        if (active) {
          if (farmIds.length === 1) navigate(`/farms/${farmIds[0]}`);
          else if (farmIds.length > 1) navigate("/farms");
          else setState("error");
        }
      })
      .catch(() => { if (active) setState("error"); });
    return () => { active = false; };
  }, [navigate]);

  return <PageContainer>
    <div className="page-intro">
      <p className="eyebrow">Saved farm workspace</p>
      <h2>{state === "opening" ? "Opening your farms…" : "That link is no longer available"}</h2>
      <p>{state === "opening"
        ? "Retrieving the farms and plots you already registered."
        : "In your connected TerraPulse Telegram chat, send /open and tap the new link."}</p>
    </div>
    {state === "error" && <ErrorState label="This one-time link may have expired or already been used." />}
    {state === "error" && <button className="secondary-button" onClick={() => navigate("/farms")}>Back to farms</button>}
  </PageContainer>;
}
