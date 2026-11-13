import type { CropPlan } from "../farmerPlan";
import { dateLabel, validDate } from "../farmerPlan";

export function FarmCalendar({
  plots,
  today,
}: {
  plots: CropPlan[];
  today: string;
}) {
  const end = new Date(today + "T00:00:00Z");
  end.setUTCDate(end.getUTCDate() + 31);
  const endDate = end.toISOString().slice(0, 10);

  const dated = plots
    .filter((plot) => validDate(plot.date))
    .sort((a, b) => a.date.localeCompare(b.date));

  const upcoming = dated.filter(
    (plot) =>
      !plot.harvested &&
      plot.date >= today &&
      plot.date <= endDate
  );

  const undated = plots.filter(
    (plot) => !plot.harvested && !validDate(plot.date)
  );

  return <div className="fp-section">
    <header className="fp-intro">
      <div>
        <h1>Agricultural calendar</h1>
        <p>
          Recorded planting dates, planned activities and crop history.
          Dates are not inferred from unsupported crop-stage assumptions.
        </p>
      </div>
    </header>

    <section className="fp-panel fp-section">
      <h2>Next 31 days</h2>
      {upcoming.length ? upcoming.map((plot) =>
        <article key={plot.id} className="fp-section">
          <h3>{dateLabel(plot.date)} - {plot.crop}</h3>
          <p>{plot.plot} - Planned sowing - {plot.certainty}</p>
          <p>
            Check field readiness and confirm the planting date.
          </p>
          <p className="fp-muted">
            Source: {plot.example
              ? "Illustrative example"
              : "Your saved farm plan"}
          </p>
        </article>
      ) : <p>No upcoming recorded sowing dates in this period.</p>}
    </section>

    <section className="fp-panel fp-section">
      <h2>Crop planting records</h2>
      {dated.map((plot) =>
        <p key={plot.id}>
          <strong>{plot.crop} - {plot.plot}</strong>
          {" - "}{dateLabel(plot.date)}
          {" - "}{plot.certainty}
          {plot.example ? " - Example" : ""}
          {plot.harvested ? " - Harvested" : ""}
        </p>
      )}
      {undated.map((plot) =>
        <p key={plot.id}>
          <strong>{plot.crop} - {plot.plot}</strong>
          {" - Planting date not recorded"}
        </p>
      )}
      {!plots.length && <p>No crop plans recorded yet.</p>}
    </section>

    <section className="fp-panel fp-section">
      <h2>Regional agricultural guidance</h2>
      <p>
        This browser calendar uses your saved planting dates.
        Scientific milestones require verified regional profiles
        and a connected farm database. Unknown dates remain unknown.
      </p>
      <a href="/farms" className="fp-text">
        Open connected farm workspace
      </a>
    </section>
  </div>;
}
