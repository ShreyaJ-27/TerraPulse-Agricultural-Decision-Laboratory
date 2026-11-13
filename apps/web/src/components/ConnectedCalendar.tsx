import { useEffect, useState } from "react";
import { apiClient, CalendarPlot } from "../services/apiClient";
import { ErrorState, LoadingState } from "./ui";

export function ConnectedCalendar({ farmId }: { farmId: string }) {
  const [data, setData] = useState<{ plots: CalendarPlot[]; asOfDate: string }>();
  const [error, setError] = useState("");
  const [crop, setCrop] = useState("");
  const [plot, setPlot] = useState("");
  useEffect(() => {
    let active = true;
    apiClient.getCalendar(farmId).then((result) => {
      if (active) setData(result);
    }).catch((reason: Error) => {
      if (active) setError(reason.message);
    });
    return () => { active = false; };
  }, [farmId]);

  if (error) return <ErrorState label={error} />;
  if (!data) return <LoadingState label="Loading calendar…" />;

  const crops = [...new Set(data.plots.map((row) => row.cropName))];
  const cropPlots = data.plots.filter((row) => !crop || crop === row.cropName);
  const shown = cropPlots.filter((row) => !plot || plot === row.plotId);
  const activities = shown.flatMap((row) => row.next31Days.map((activity) => ({ row, activity })))
    .sort((a, b) => a.activity.date.localeCompare(b.activity.date));
  return <>
    <div className="page-intro">
      <h2>Agricultural calendar</h2>
      <p>Activities for the next 31 days, starting {data.asOfDate} in your farm’s time zone.</p>
    </div>
    <div className="form-panel">
      <label>Crop<select value={crop} onChange={(event) => { setCrop(event.target.value); setPlot(""); }}>
        <option value="">All crops</option>
        {crops.map((name) => <option key={name}>{name}</option>)}
      </select></label>
      <label>Plot<select value={plot} onChange={(event) => setPlot(event.target.value)}>
        <option value="">All plots</option>
        {cropPlots.map((row) => <option key={row.plotId} value={row.plotId}>{row.plotName}</option>)}
      </select></label>
    </div>
    <section className="results-table">
      <h3>Dated activities</h3>
      {activities.length === 0 && <p>No activities with dates in this period.</p>}
      {activities.map(({ row, activity }) => <article key={`${row.plotId}:${activity.date}:${activity.title}:${activity.source}`}>
        <h4><time dateTime={activity.date}>{activity.date}</time> · {activity.title}</h4>
        <p>{row.plotName} · {activity.certainty}</p>
        <p>{activity.action}</p>
        <small>{activity.source}{activity.sourceVersion && ` · ${activity.sourceVersion}`}</small>
      </article>)}
    </section>
    <section className="results-table">
      <h3>Planting records and regional guidance</h3>
      {shown.length === 0 && <p>Add a crop plot to see its calendar.</p>}
      {shown.map((row) => <article key={row.plotId}>
        <h4>{row.plotName} · {row.cropName}</h4>
        <p>{row.plantingDate ? `${row.plantingDate} · ${row.plantingCertainty}` : "Planting date unavailable"}</p>
        {row.regionalGuidanceAvailable ? <>
          <p>{row.plantingWindowNote}</p>
          {row.regionalSource && <p>{row.regionalSource} · {row.regionalSourceVersion}</p>}
          {row.regionalSourceUrl && <p><a href={row.regionalSourceUrl} target="_blank" rel="noreferrer">Read regional source</a></p>}
          {row.undatedActivities.map((activity) => <div key={activity.title}>
            <strong>{activity.title} · Date unavailable</strong>
            <p>{activity.guidance}</p>
            <small>{activity.source} · {activity.sourceVersion}</small>
          </div>)}
        </> : <p>Regional calendar guidance is unavailable for this crop and region.</p>}
      </article>)}
    </section>
  </>;
}
