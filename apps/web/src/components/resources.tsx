import { useCallback, useEffect, useState } from "react";
import { Branch, Farm, Resource, WaterLedgerVersion, apiClient } from "../services/apiClient";
import { EmptyState, ErrorState, LoadingState, ReusableCard } from "./ui";

function WaterExample() {
  const [withdrawal, setWithdrawal] = useState(250);
  const opening = 1000;
  return <details className="form-panel">
    <summary>Explore an example water balance</summary>
    <p>Illustrative scenario · A tank starts with {opening.toLocaleString()} L. Assume 80% of the withdrawal reaches the plot.</p>
    <label>Example withdrawal ({withdrawal} L)
      <input type="range" min={0} max={opening} step={50} value={withdrawal} onChange={(event) => setWithdrawal(Number(event.target.value))} />
    </label>
    <p aria-live="polite">{opening - withdrawal} L remains in the tank · {withdrawal * 0.8} L reaches the plot · {withdrawal * 0.2} L conveyance loss</p>
  </details>;
}

export function ResourcePanel({ farm }: { farm: Farm }) {
  const farmId = farm.farmId;
  const [resources, setResources] = useState<Resource[]>();
  const [name, setName] = useState("");
  const [type, setType] = useState("reservoir");
  const [volume, setVolume] = useState("");
  const [plotId, setPlotId] = useState("");
  const [resourceId, setResourceId] = useState("");
  const [branchId, setBranchId] = useState("");
  const [branches, setBranches] = useState<Branch[]>();
  const [version, setVersion] = useState<WaterLedgerVersion>();
  const [ledgerStatus, setLedgerStatus] = useState("");
  const [branchError, setBranchError] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionResult, setActionResult] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoadError(false);
    try {
      const value = await apiClient.listResources(farmId);
      setResources(value.resources);
      setResourceId((current) => value.resources.some((item) => item.resourceId === current)
        ? current : value.resources[0]?.resourceId || "");
    } catch {
      setLoadError(true);
    }
  }, [farmId]);
  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    if (!plotId) return;
    let active = true;
    apiClient.listBranches(farmId, plotId)
      .then((value) => { if (active) setBranches(value.branches); })
      .catch(() => { if (active) setBranchError(true); });
    return () => { active = false; };
  }, [farmId, plotId]);

  useEffect(() => {
    if (!resourceId || !branchId) return;
    let active = true;
    apiClient.listWaterLedgerVersions(farmId, resourceId, branchId).then(({ versions }) => {
      if (!active) return;
      const latest = versions.reduce<WaterLedgerVersion | undefined>((current, item) =>
        !current || item.version > current.version ? item : current, undefined);
      setVersion(latest);
      setLedgerStatus(latest ? "" : "No saved ledger versions for this resource and branch.");
    }).catch(() => { if (active) setLedgerStatus("The saved ledger could not be loaded."); });
    return () => { active = false; };
  }, [farmId, resourceId, branchId]);

  async function save(operation: "resource" | "assignment") {
    if (busy) return;
    setBusy(true);
    setActionError("");
    setActionResult("");
    try {
      if (operation === "resource") {
        await apiClient.createResource(farmId, { name: name.trim(), resourceType: type, openingVolume: volume, unit: "litre" });
        setName("");
        setVolume("");
        setActionResult("Water resource registered.");
        await load();
      } else {
        await apiClient.assignResourcePlot(farmId, resourceId, plotId);
        setActionResult("Plot authorized for this resource.");
      }
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "The update failed.");
    } finally { setBusy(false); }
  }

  return <section className="resource-panel">
    <div className="page-intro"><h2>Water Ledger</h2><p>Manage shared water and review balances for each saved branch.</p></div>
    {loadError ? <><ErrorState label="Water resources could not be loaded." />
      <button className="secondary-button" onClick={() => void load()}>Retry resources</button></>
      : !resources ? <LoadingState label="Loading water resources…" />
      : resources.length === 0 ? <EmptyState title="No shared resources" description="Register a reservoir, tank, pond, or irrigation store." />
      : <div className="card-grid">{resources.map((resource) => <ReusableCard key={resource.resourceId}>
        <h3>{resource.name}</h3><p>{resource.resourceType} · {resource.openingVolume} L opening volume</p>
      </ReusableCard>)}</div>}
    {actionError && <ErrorState label={actionError} />}
    {actionResult && <p role="status">{actionResult}</p>}
    <form className="form-panel" onSubmit={(event) => { event.preventDefault(); void save("resource"); }}>
      <h3>Register water resource</h3>
      <label>Name<input required maxLength={200} value={name} onChange={(event) => setName(event.target.value)} /></label>
      <label>Type<select value={type} onChange={(event) => setType(event.target.value)}>
        <option value="reservoir">Reservoir</option><option value="tank">Tank</option><option value="pond">Pond</option>
        <option value="irrigation store">Irrigation store</option>
      </select></label>
      <label>Opening volume (L)<input required type="number" min="0" step="any" value={volume} onChange={(event) => setVolume(event.target.value)} /></label>
      <button className="primary-button" disabled={!name.trim() || busy}>Register resource</button>
    </form>
    {Boolean(resources?.length) && farm.plots.length > 0 && <section className="form-panel">
      <h3>Plot access and balances</h3>
      <label>Resource<select value={resourceId} onChange={(event) => {
        setResourceId(event.target.value); setVersion(undefined); setLedgerStatus("");
      }}>{resources?.map((resource) => <option key={resource.resourceId} value={resource.resourceId}>{resource.name}</option>)}</select></label>
      <label>Plot<select value={plotId} onChange={(event) => {
        setPlotId(event.target.value); setBranches(undefined); setBranchId(""); setVersion(undefined); setLedgerStatus(""); setBranchError(false);
      }}><option value="">Select plot</option>{farm.plots.map((plot) => <option key={plot.plotId} value={plot.plotId}>
        {plot.management?.plotName || plot.cropCanonicalName} · {plot.plotId.slice(0, 8)}
      </option>)}</select></label>
      <button className="secondary-button" disabled={!resourceId || !plotId || busy} onClick={() => void save("assignment")}>Authorize plot</button>
      {branchError && <ErrorState label="Saved branches could not be loaded." />}
      {plotId && !branches && !branchError && <LoadingState label="Loading saved branches…" />}
      {branches?.length === 0 && <p>Save a decision branch to view its water balance.</p>}
      {Boolean(branches?.length) && <label>Saved branch<select value={branchId} onChange={(event) => {
        setBranchId(event.target.value); setVersion(undefined); setLedgerStatus("");
      }}><option value="">Select branch</option>{branches?.map((branch) => <option key={branch.branchId} value={branch.branchId}>
        {branch.decisionType.replaceAll("_", " ")} · {branch.effectiveDate} · {branch.branchId.slice(0, 6)}
      </option>)}</select></label>}
      {branchId && !version && !ledgerStatus && <LoadingState label="Loading water ledger…" />}
      {ledgerStatus && <p role="status">{ledgerStatus}</p>}
      {version && <div aria-live="polite">
        <h4>Saved balance · Version {version.version}</h4>
        <details><summary>Ledger reference</summary><code className="ledger-reference">{version.ledgerHash}</code></details>
        <p>Opening {version.payload.openingVolume.value} L · Closing {version.payload.closingVolume.value} L · Losses {version.payload.losses.value} L</p>
        {version.payload.plotAllocations.map((allocation) => <p key={allocation.plotId}>
          {farm.plots.find((item) => item.plotId === allocation.plotId)?.cropCanonicalName || "Plot"} · {allocation.withdrawnAmount.value} L withdrawn · {allocation.effectiveAmount.value} L effective
        </p>)}
      </div>}
    </section>}
    <WaterExample />
  </section>;
}
