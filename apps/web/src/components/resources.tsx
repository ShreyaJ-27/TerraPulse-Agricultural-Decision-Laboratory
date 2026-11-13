import { useCallback, useEffect, useState } from "react";
import { Farm, Resource, apiClient } from "../services/apiClient";
import { EmptyState, ErrorState, ReusableCard } from "./ui";

export function ResourcePanel({ farm }: { farm: Farm }) {
  const [resources, setResources] = useState<Resource[]>([]);
  const [name, setName] = useState("");
  const [type, setType] = useState("reservoir");
  const [volume, setVolume] = useState("");
  const [plotId, setPlotId] = useState("");
  const [resourceId, setResourceId] = useState("");
  const [error, setError] = useState("");
  const load = useCallback(() => apiClient.listResources(farm.farmId).then((value) => {
    setResources(value.resources);
    setResourceId((current) => current || value.resources[0]?.resourceId || "");
  }).catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to load water resources.")), [farm.farmId]);
  useEffect(() => { void load(); }, [load]);
  const create = async () => {
    setError("");
    try {
      await apiClient.createResource(farm.farmId, { name, resourceType: type, openingVolume: Number(volume), unit: "litre" });
      setName(""); setVolume(""); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to register water resource."); }
  };
  const assign = async () => {
    if (!resourceId || !plotId) return;
    setError("");
    try { await apiClient.assignResourcePlot(farm.farmId, resourceId, plotId); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to authorize plot."); }
  };
  return <section className="resource-panel">
    <div className="page-intro"><p className="eyebrow">Shared water</p><h2>Resource ledger inputs</h2><p>Volumes are persisted in litres and allocations remain isolated by branch.</p></div>
    {error && <ErrorState label={error} />}
    {resources.length === 0 ? <EmptyState title="No shared resources" description="Register a reservoir, tank, pond, or irrigation store." /> : <div className="card-grid">{resources.map((resource) => <ReusableCard key={resource.resourceId}><h3>{resource.name}</h3><p>{resource.resourceType} · {resource.openingVolume} litre opening volume</p><small>{resource.resourceId}</small></ReusableCard>)}</div>}
    <div className="form-panel"><h3>Register water resource</h3><label>Name<input value={name} onChange={(event) => setName(event.target.value)} /></label><label>Type<input value={type} onChange={(event) => setType(event.target.value)} /></label><label>Opening volume (litre)<input type="number" min="0" value={volume} onChange={(event) => setVolume(event.target.value)} /></label><button className="primary-button" disabled={!name.trim() || !volume} onClick={create}>Register resource</button></div>
    {resources.length > 0 && farm.plots.length > 0 && <div className="form-panel"><h3>Authorize a plot</h3><label>Resource<select value={resourceId} onChange={(event) => setResourceId(event.target.value)}>{resources.map((resource) => <option key={resource.resourceId} value={resource.resourceId}>{resource.name}</option>)}</select></label><label>Plot<select value={plotId} onChange={(event) => setPlotId(event.target.value)}><option value="">Select plot</option>{farm.plots.map((plot) => <option key={plot.plotId} value={plot.plotId}>{plot.cropCanonicalName} · {plot.plotId.slice(0, 8)}</option>)}</select></label><button className="secondary-button" disabled={!plotId} onClick={assign}>Authorize plot</button></div>}
  </section>;
}
