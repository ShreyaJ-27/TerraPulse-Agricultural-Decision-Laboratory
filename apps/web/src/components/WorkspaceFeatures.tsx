import { useEffect, useState } from "react";
import { apiClient, Farm } from "../services/apiClient";
import { ConnectedCalendar } from "./ConnectedCalendar";
import { EmptyState, ErrorState, LoadingState, PageContainer } from "./ui";

const features = {
  "crop-planning": { title: "Crop Planning", route: "" },
  calendar: { title: "Calendar", route: "" },
  "future-fold": { title: "Future Fold", route: "/future-fold" },
  "living-field": { title: "Living Field", route: "/observatory" },
  "saved-decisions": { title: "Saved Decisions", route: "/timeline" },
};

export type WorkspaceFeature = keyof typeof features;

export function WorkspaceFeatures({ feature, farmId, navigate }: {
  feature: WorkspaceFeature;
  farmId?: string;
  navigate: (path: string) => void;
}) {
  const [farms, setFarms] = useState<Farm[]>();
  const [error, setError] = useState("");
  const { title, route } = features[feature];
  useEffect(() => {
    let active = true;
    apiClient.listFarms().then((result) => {
      if (active) setFarms(result.farms);
    }).catch((reason: Error) => {
      if (active) setError(reason.message);
    });
    return () => { active = false; };
  }, []);

  if (error) return <PageContainer><ErrorState label={error} /></PageContainer>;
  if (!farms) return <PageContainer><LoadingState label="Loading your farms…" /></PageContainer>;
  if (!farms.length) return <PageContainer><EmptyState title="Register your farm first" description="Add a farm to use this feature."
    action={<button className="primary-button" onClick={() => navigate("/farms/new")}>Register farm</button>} /></PageContainer>;
  const farm = farms.find((item) => item.farmId === farmId) || farms[0];
  const target = `/farms/${farm.farmId}`;
  return <PageContainer>
    <div className="form-panel">
      <label>Farm<select value={farm.farmId} onChange={(event) => navigate(`/${feature}/${event.target.value}`)}>
        {farms.map((item) => <option key={item.farmId} value={item.farmId}>{item.name}</option>)}
      </select></label>
    </div>
    {feature === "calendar" ? <ConnectedCalendar key={farm.farmId} farmId={farm.farmId} /> : <>
      <div className="page-intro">
        <h2>{title}</h2>
        {feature === "crop-planning" && <button className="primary-button" onClick={() => navigate(target + "/plots/new")}>Add crop plot</button>}
      </div>
      {farm.plots.length ? <div className="card-grid">{farm.plots.map((plot, index) =>
        <button className="info-card farm-card" key={plot.plotId}
          onClick={() => navigate(`${target}/plots/${plot.plotId}${route}`)}>
          <h3>{plot.management?.plotName || `Plot ${index + 1}`} · {plot.cropCanonicalName}</h3>
          <p>{plot.areaM2.value} m² · {plot.plantingDate || "Planting date unavailable"}</p>
        </button>)}</div> : <EmptyState title="Add a crop plot to get started" description="Choose a crop and enter the plot area."
          action={<button className="secondary-button" onClick={() => navigate(target + "/plots/new")}>Add crop plot</button>} />}
    </>}
  </PageContainer>;
}
