import { useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { localeLabels } from "./i18n";
import type { Locale } from "./i18n";
import {
  advisoryKinds, advisoryUrl, cropNames, dateLabel, farmToday, foldUrl, generateAdvisories,
  localFarmAdapter, messageCopy, newCrop, validDate, visiblePlots,
} from "./farmerPlan";
import type { Advisory, Channel, CropName, CropPlan, Draft, FarmPlan, Preferences } from "./farmerPlan";
import "./farmer.css";

type Navigate = (path: string) => void;
type Update = (fn: (current: FarmPlan) => FarmPlan) => void;
const icons: Record<CropName, string> = { Rice: "🌾", Maize: "🌽", Turmeric: "🌿", Millet: "🌾", Groundnut: "🥜", Tomato: "🍅" };
const localizedCrops: Record<Locale, string[]> = {
  en: [...cropNames],
  hi: ["धान", "मक्का", "हल्दी", "मोटा अनाज", "मूंगफली", "टमाटर"],
  kn: ["ಭತ್ತ", "ಮೆಕ್ಕೆಜೋಳ", "ಅರಿಶಿನ", "ಸಿರಿಧಾನ್ಯ", "ಕಡಲೆಕಾಯಿ", "ಟೊಮೇಟೊ"],
};

function Link({ to, navigate, children, className = "fp-secondary", current }: { to: string; navigate: Navigate; children: ReactNode; className?: string; current?: boolean }) {
  return <a className={className} href={to} aria-current={current ? "page" : undefined} onClick={(event) => {
    if (event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(to);
  }}>{children}</a>;
}
function Tag({ children, tone = "" }: { children: ReactNode; tone?: string }) {
  return <span className={"fp-tag " + tone}>{children}</span>;
}
function Intro({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return <header className="fp-intro"><div><h1>{title}</h1>{children && <p>{children}</p>}</div>{action}</header>;
}
function PreferencesForm({ value, change }: { value: Preferences; change: (value: Preferences) => void }) {
  const labels: Record<Channel, string> = { inApp: "In-app notifications", whatsapp: "WhatsApp preference", sms: "SMS preference" };
  return <fieldset className="fp-fieldset"><legend>Notification consent</legend>
    <p className="fp-muted">Choose which channels you opt into. WhatsApp and SMS are preview only.</p>
    <div className="fp-choices">{(Object.keys(labels) as Channel[]).map((channel) => <label className="fp-check" key={channel}>
      <input type="checkbox" checked={value[channel]} onChange={(event) => change({ ...value, [channel]: event.target.checked })} />{labels[channel]}
    </label>)}</div>
  </fieldset>;
}
function PlantingFields({ date, certainty, change }: { date: string; certainty: CropPlan["certainty"]; change: (date: string, certainty: CropPlan["certainty"]) => void }) {
  return <div className="fp-form-grid">
    <label>Planting date <small>Optional</small><input type="date" min="1900-01-01" max="2100-12-31" value={date} onChange={(event) => change(event.target.value, certainty)} /></label>
    <label>Date status<select value={certainty} disabled={!date} onChange={(event) => change(date, event.target.value as CropPlan["certainty"])}><option value="estimated">Estimated</option><option value="confirmed">Confirmed</option></select></label>
  </div>;
}
function Registration({ draft, change, save, navigate }: { draft: Draft; change: (draft: Draft) => void; save: () => void; navigate: Navigate }) {
  const [error, setError] = useState("");
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!draft.name.trim() || !draft.district.trim() || !draft.crops.length) {
      setError("Enter your name and district, then select at least one crop.");
      return;
    }
    if (draft.date && !validDate(draft.date)) {
      setError("Enter a valid planting date.");
      return;
    }
    save();
  }
  return <div className="fp-registration">
    <aside className="fp-registration-cover"><span className="fp-cover-label">TerraPulse</span><h1>Plan your<br />next season.</h1><p>Keep your crops, field checks and decisions in one place.</p></aside>
    <form className="fp-panel fp-form" onSubmit={submit}>
      <h2>Set up your farm</h2><p className="fp-muted">Your profile and draft are saved in this browser.</p>
      <div className="fp-form-grid">
        <label>Display name<input autoComplete="name" placeholder="e.g. Asha" maxLength={80} required value={draft.name} onChange={(event) => change({ ...draft, name: event.target.value })} /></label>
        <label>District / location<input autoComplete="address-level2" placeholder="e.g. Mysuru" maxLength={100} required value={draft.district} onChange={(event) => change({ ...draft, district: event.target.value })} /></label>
      </div>
      <label>Preferred language<select value={draft.language} onChange={(event) => change({ ...draft, language: event.target.value as Locale })}>{Object.entries(localeLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <fieldset className="fp-fieldset"><legend>What are you growing?</legend><div className="fp-choices">{cropNames.map((crop) => <label className="fp-check" key={crop}>
        <input type="checkbox" checked={draft.crops.includes(crop)} onChange={(event) => change({ ...draft, crops: event.target.checked ? [...draft.crops, crop] : draft.crops.filter((item) => item !== crop) })} />
        <span aria-hidden="true">{icons[crop]}</span> {crop}
      </label>)}</div></fieldset>
      <p className="fp-muted">Optional starting date for selected crops. You can edit each plot later.</p>
      <PlantingFields date={draft.date} certainty={draft.certainty} change={(date, certainty) => change({ ...draft, date, certainty })} />
      <PreferencesForm value={draft.preferences} change={(preferences) => change({ ...draft, preferences })} />
      {error && <p className="fp-error" role="alert">{error}</p>}
      <div className="fp-actions"><button className="fp-primary">Open my dashboard →</button><Link to="/" navigate={navigate} className="fp-text">Back to dashboard</Link></div>
    </form>
  </div>;
}
function CropCard({ plot, navigate, manage }: { plot: CropPlan; navigate: Navigate; manage?: boolean }) {
  return <article className="fp-panel fp-crop">
    <div className="fp-card-top"><span className="fp-crop-icon" aria-hidden="true">{icons[plot.crop]}</span><Tag tone={plot.harvested ? "" : "fp-green"}>{plot.harvested ? "Harvested" : "Active"}{plot.example ? " · Example" : ""}</Tag></div>
    <h3>{plot.crop}</h3><p>{plot.plot} · Cycle {plot.cycle}</p>
    <div className="fp-crop-date"><span>{plot.harvested ? "Harvested" : "Planting date"}</span><strong>{plot.harvested ? dateLabel(plot.harvested) : plot.date ? dateLabel(plot.date) + " · " + plot.certainty : "To be set"}</strong></div>
    {manage && !plot.example
      ? <Link to={"/farm/" + plot.id} navigate={navigate} className="fp-text">{plot.harvested ? "Start next cycle →" : "Manage crop →"}</Link>
      : <Link to={foldUrl(plot)} navigate={navigate} className="fp-text">Explore options →</Link>}
  </article>;
}
function Dashboard({ plan, plots, cards, navigate }: { plan: FarmPlan; plots: CropPlan[]; cards: Advisory[]; navigate: Navigate }) {
  const active = plots.filter((plot) => !plot.harvested);
  const first = cards[0];
  return <>
    <section className="fp-hero"><div className="fp-hero-copy">
      <span className="fp-cover-label">{plan.profile ? plan.profile.district : "Example farm · Mysuru"}</span>
      <h1>{plan.profile ? "Welcome, " + plan.profile.name + "." : "Your farm, in focus."}</h1>
      <p>{plan.profile ? "See what’s growing and decide what needs your attention next." : "Explore an example farm or set up your own crop plan."}</p>
      <Link to={plan.profile ? "/farm" : "/register"} navigate={navigate} className="fp-primary">{plan.profile ? "Manage my farm" : "Register my farm"} →</Link>
    </div></section>
    <div className="fp-overview">
      <section className="fp-panel fp-priority"><div className="fp-card-top"><span className="fp-kicker">Next decision</span><Tag tone="fp-amber">{cards.length} open {cards.length === 1 ? "advisory" : "advisories"}</Tag></div>
        {first ? <><h2>{first.kind}</h2><p>{first.crop.crop} · {first.crop.plot}{first.crop.example ? " · Example" : ""}</p><p>{first.action}</p><Link to={advisoryUrl(first)} navigate={navigate} className="fp-text">View advisory →</Link></> : <><h2>You’re up to date</h2><p>Check your farm plan for the next planting or harvest.</p><Link to="/farm" navigate={navigate} className="fp-text">Open farm →</Link></>}
      </section>
      <section className="fp-panel fp-weather"><div className="fp-card-top"><span className="fp-kicker">Weather context</span><Tag>Example forecast</Tag></div>
        <h2><span aria-hidden="true">☁</span> {plan.forecastRevision ? "Shower moved later" : "Clouds building"}</h2><p>{plan.forecastRevision ? "The example shower shifts from tomorrow to the following day." : "This example assumes a possible shower tomorrow."}</p><Link to="/advisories" navigate={navigate} className="fp-text">See farm advisories →</Link>
      </section>
    </div>
    <section className="fp-section"><div className="fp-section-title"><h2>Active crops <small>{active.length}</small></h2><Link to="/farm" navigate={navigate} className="fp-text">Open farm →</Link></div>
      {active.length ? <div className="fp-card-grid">{active.map((plot) => <CropCard key={plot.id} plot={plot} navigate={navigate} />)}</div> : <p className="fp-panel">Add a crop or start a new cultivation cycle to see it here.</p>}
    </section>
    <div className="fp-overview fp-workspaces">
      <Link className="fp-panel fp-workspace" to="/future-fold" navigate={navigate}><span aria-hidden="true">↗</span><div><h3>Future Fold</h3><p>Compare two ways to approach your next decision.</p></div></Link>
      <Link className="fp-panel fp-workspace" to="/living-field" navigate={navigate}><span aria-hidden="true">▧</span><div><h3>Living Field</h3><p>See plots and crop stages together.</p></div></Link>
    </div>
  </>;
}
function CropEditor({ initial, save, harvest, navigate }: { initial?: CropPlan; save: (crop: CropPlan) => void; harvest: () => void; navigate: Navigate }) {
  const [crop, setCrop] = useState<CropName>(initial?.crop || "Rice");
  const [plot, setPlot] = useState(initial?.plot || "");
  const [date, setDate] = useState(initial?.harvested ? "" : initial?.date || "");
  const [certainty, setCertainty] = useState<CropPlan["certainty"]>(initial?.harvested ? "estimated" : initial?.certainty || "estimated");
  const [error, setError] = useState("");
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!plot.trim() || (date && !validDate(date))) {
      setError("Enter a plot name and a valid date if you know it.");
      return;
    }
    if (!initial || initial.harvested) {
      const next = newCrop(crop, plot.trim(), date, certainty);
      save(initial ? { ...next, cycle: initial.cycle + 1 } : next);
      return;
    }
    save({ ...initial, crop, plot: plot.trim(), date, certainty });
  }
  return <>
    <Intro title={initial?.harvested ? "Start next cycle" : initial ? "Manage crop" : "Add a crop"} action={<Link to="/farm" navigate={navigate}>Back to farm</Link>} />
    <form className="fp-panel fp-form fp-narrow" onSubmit={submit}>
      <div className="fp-form-grid"><label>Crop<select value={crop} onChange={(event) => setCrop(event.target.value as CropName)}>{cropNames.map((name) => <option key={name}>{name}</option>)}</select></label>
      <label>Plot name<input value={plot} onChange={(event) => setPlot(event.target.value)} placeholder="e.g. North plot" required maxLength={80} /></label></div>
      <PlantingFields date={date} certainty={certainty} change={(nextDate, nextCertainty) => { setDate(nextDate); setCertainty(nextCertainty); }} />
      {error && <p className="fp-error" role="alert">{error}</p>}
      <div className="fp-actions"><button className="fp-primary">{initial?.harvested ? "Start cycle" : "Save crop"}</button>{initial && !initial.harvested && <button type="button" className="fp-secondary" onClick={harvest}>Mark harvested</button>}</div>
    </form>
  </>;
}
function Farm({ plan, plots, segment, update, navigate, today }: { plan: FarmPlan; plots: CropPlan[]; segment?: string; update: Update; navigate: Navigate; today: string }) {
  const selected = plan.plots.find((plot) => plot.id === segment);
  if (plan.profile && (segment === "new" || selected)) return <CropEditor key={segment} initial={selected} navigate={navigate} save={(crop) => {
    update((current) => ({ ...current, plots: current.plots.some((plot) => plot.id === crop.id) ? current.plots.map((plot) => plot.id === crop.id ? crop : plot) : [...current.plots, crop] }));
    navigate("/farm");
  }} harvest={() => {
    update((current) => ({ ...current, plots: current.plots.map((plot) => plot.id === segment ? { ...plot, harvested: today } : plot) }));
    navigate("/farm");
  }} />;
  const active = plots.filter((plot) => !plot.harvested);
  const harvested = plots.filter((plot) => plot.harvested);
  return <>
    <Intro title="My farm" action={<Link className="fp-primary" to={plan.profile ? "/farm/new" : "/register"} navigate={navigate}>{plan.profile ? "+ Add crop" : "Register my farm"}</Link>}>{plan.profile?.district || "Example farm · Mysuru"}</Intro>
    {segment && <p className="fp-panel">That crop is unavailable. Choose a plot below.</p>}
    <div className="fp-card-grid">{active.map((plot) => <CropCard key={plot.id} plot={plot} navigate={navigate} manage />)}</div>
    {!active.length && <p className="fp-panel">No active crops. Add a crop or start a new cycle from your harvest history.</p>}
    {!!harvested.length && <section className="fp-section"><h2>Harvest history</h2><div className="fp-card-grid">{harvested.map((plot) => <CropCard key={plot.id} plot={plot} navigate={navigate} manage />)}</div></section>}
    <div className="fp-section"><Link to="/farms" navigate={navigate} className="fp-text">Open connected science workspace ↗</Link></div>
  </>;
}

function AdvisoryCenter({ cards, id, marks, mark, revised, revise, navigate }: { cards: Advisory[]; id?: string; marks: FarmPlan["marks"]; mark: (id: string, value: FarmPlan["marks"][string]) => void; revised: boolean; revise: () => void; navigate: Navigate }) {
  const [status, setStatus] = useState("open");
  const [category, setCategory] = useState("all");
  useEffect(() => {
    if (id && cards.some((card) => card.id === id) && marks[id] !== "dismissed" && marks[id] !== "read") mark(id, "read");
  }, [cards, id, mark, marks]);
  const shown = cards.filter((card) => {
    if (id) return card.id === id;
    const state = marks[card.id] || "unread";
    return (status === "open" ? state !== "dismissed" : state === status) && (category === "all" || card.kind === category);
  });
  return <>
    <Intro title={id ? "Crop advisory" : "Advisory center"} action={id ? <Link to="/advisories" navigate={navigate}>All advisories</Link> : <button className="fp-secondary" type="button" onClick={revise}>{revised ? "Reset example forecast" : "Apply example forecast change"}</button>}>Decisions prompted by your crop plan and labelled examples.</Intro>
    {!id && <div className="fp-filters">
      <label>Status<select value={status} onChange={(event) => setStatus(event.target.value)}><option value="open">Open</option><option value="unread">Unread</option><option value="read">Read</option><option value="dismissed">Dismissed</option></select></label>
      <label>Category<select value={category} onChange={(event) => setCategory(event.target.value)}><option value="all">All categories</option>{advisoryKinds.map((kind) => <option key={kind}>{kind}</option>)}</select></label>
      <span aria-live="polite">{shown.length} {shown.length === 1 ? "advisory" : "advisories"}</span>
    </div>}
    <div className="fp-advisory-grid">{shown.map((card) => {
      const state = marks[card.id] || "unread";
      return <article className="fp-panel fp-advisory" key={card.id}>
        <div className="fp-card-top"><Tag tone={card.urgency === "Review soon" ? "fp-amber" : "fp-green"}>{card.urgency}</Tag><span className="fp-read">{state === "unread" && "● "}{state}</span></div>
        <h2>{card.kind}</h2><p className="fp-kicker">{card.crop.crop} · {card.crop.plot}{card.crop.example ? " · Example" : ""}</p>
        <p>{card.reason}</p><p><strong>Next step</strong> {card.action}</p>
        <p className="fp-advisory-source">{card.source} · <time dateTime={card.date}>{dateLabel(card.date)}</time></p>
        <div className="fp-actions">
          <Link to={foldUrl(card.crop, card.kind, card.topic)} navigate={navigate} className="fp-primary">Explore options →</Link>
          <Link to={card.crop.example ? "/farm" : "/farm/" + card.crop.id} navigate={navigate}>View plot</Link>
          {state === "dismissed" ? <button className="fp-text" onClick={() => mark(card.id, "unread")}>Restore</button> : <>
            {!id && <button className="fp-text" onClick={() => mark(card.id, state === "read" ? "unread" : "read")}>Mark {state === "read" ? "unread" : "read"}</button>}
            <button className="fp-text" onClick={() => mark(card.id, "dismissed")}>Dismiss</button>
          </>}
        </div>
      </article>;
    })}</div>
    {!shown.length && <p className="fp-panel">{id ? "This advisory no longer applies to the current farm plan." : "No advisories match these filters."}</p>}
  </>;
}
function Inbox({ plan, cards, navigate, change }: { plan: FarmPlan; cards: Advisory[]; navigate: Navigate; change: (preferences: Preferences, locale: Locale) => void }) {
  const [channel, setChannel] = useState<Channel>("inApp");
  const [selected, select] = useState("");
  const { preferences, language } = plan.profile || plan.draft;
  const copy = messageCopy[language];
  const card = cards.find((item) => item.id === selected) || cards[0];
  return <>
    <Intro title="Notification inbox">Review farm updates and preview messages in your preferred language.</Intro>
    <div className="fp-tabs" aria-label="Message channel">{(["inApp", "whatsapp", "sms"] as const).map((item) => <button key={item} className="fp-secondary" aria-pressed={channel === item} onClick={() => setChannel(item)}>{{ inApp: "In-app", whatsapp: "WhatsApp preview", sms: "SMS preview" }[item]}</button>)}</div>
    <div className="fp-inbox">
      <section className="fp-panel fp-inbox-list"><h2>Farm updates</h2>
        {!preferences.inApp && <p className="fp-muted">In-app notifications are off. You can still preview these updates.</p>}
        {!cards.length && <p>No current notifications.</p>}
        {cards.map((item) => <button className="fp-message-item" key={item.id} aria-pressed={card?.id === item.id} onClick={() => select(item.id)}><strong>{item.kind}</strong><span>{item.crop.crop} · {item.crop.plot} · {plan.marks[item.id] === "read" ? "Read" : "Unread"}</span></button>)}
      </section>
      <section className={"fp-panel fp-message fp-message-" + channel}>
        <Tag>{channel === "inApp" ? preferences.inApp ? "Local inbox" : "In-app preview" : "Preview only · No delivery"}</Tag>
        {card ? <article className="fp-bubble" lang={language}>
          <strong>{copy.title}</strong><p>{localizedCrops[language][cropNames.indexOf(card.crop.crop)]} · {copy.categories[advisoryKinds.indexOf(card.kind)]}</p>
          <p>{copy.next}</p><p className="fp-muted">{dateLabel(card.date)} · {card.source}</p>
          <div className="fp-actions"><Link to={advisoryUrl(card)} navigate={navigate} className="fp-text">{copy.view}</Link><Link to={foldUrl(card.crop, card.kind, card.topic)} navigate={navigate} className="fp-text">{copy.explore}</Link></div>
        </article> : <p>Choose a farm update when one becomes available.</p>}
      </section>
    </div>
    <section className="fp-panel fp-form fp-section fp-narrow">
      <label>Message language<select value={language} onChange={(event) => change(preferences, event.target.value as Locale)}>{Object.entries(localeLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <PreferencesForm value={preferences} change={(value) => change(value, language)} />
    </section>
  </>;
}
const comparisonOptions = {
  water: { title: "When to check the field", current: "Check soil moisture today", currentDetail: "Walk the plot and check moisture before making an irrigation decision.", alternative: "Check again after the forecast update", alternativeDetail: "Review the next forecast and confirm conditions in the field before acting." },
  planting: { title: "When to commit to planting", current: "Keep your planned window", currentDetail: "Confirm seed, labour and plot readiness against your planned date.", alternative: "Recheck before setting a date", alternativeDetail: "Keep the date estimated while you confirm field access and local conditions." },
  "field-check": { title: "When to review establishment", current: "Walk the plot today", currentDetail: "Record observations from multiple points in the plot.", alternative: "Schedule a follow-up check", alternativeDetail: "Choose a second visit to compare observations with your first walk." },
};
function Fold({ plots, id, topic, plan, update, navigate, today }: { plots: CropPlan[]; id?: string; topic?: string; plan: FarmPlan; update: Update; navigate: Navigate; today: string }) {
  const plot = plots.find((item) => item.id === id) || plots.find((item) => !item.harvested) || plots[0];
  const key = topic === "planting" || topic === "field-check" ? topic : "water";
  const options = comparisonOptions[key];
  const cycle = plot && plot.id + "-" + plot.cycle;
  const decisionKey = cycle && cycle + "-" + key;
  const saved = decisionKey ? plan.decisions[decisionKey] : undefined;
  return <>
    <Intro title="Future Fold" action={<Link to="/living-field" navigate={navigate}>Open Living Field →</Link>}>Compare practical options for your next crop decision.</Intro>
    <div className="fp-filters"><Tag tone="fp-amber">Example comparison</Tag>{plot && <label>Crop / plot<select value={plot.id} onChange={(event) => navigate("/future-fold/" + event.target.value + "/" + key)}>{plots.map((item) => <option value={item.id} key={item.id}>{item.crop} · {item.plot} · Cycle {item.cycle}</option>)}</select></label>}</div>
    {id && id !== plot?.id && <p className="fp-muted">The linked crop is unavailable. Showing the current farm plan.</p>}
    {plot && decisionKey ? <>
      <h2>{options.title}</h2>
      <p className="fp-muted">Illustrative planning options based on your selected crop and assumptions. Scientific outputs are unavailable in this view.</p>
      <div className="fp-overview">{(["current", "alternative"] as const).map((option) => <article className="fp-panel fp-option" key={option}>
        <Tag tone={option === "alternative" ? "fp-amber" : "fp-green"}>{option === "current" ? "Current approach" : "Alternative"}</Tag>
        <h2>{options[option]}</h2><p>{option === "current" ? options.currentDetail : options.alternativeDetail}</p>
        <button type="button" className="fp-secondary" aria-pressed={saved?.option === option} onClick={() => update((current) => ({ ...current, decisions: { ...current.decisions, [decisionKey]: { option, date: today } } }))}>{saved?.option === option ? "Saved ✓" : "Save this option"}</button>
      </article>)}</div>
      <p role="status" className="fp-muted">{saved ? "Saved to this crop cycle. Revisit it in the advisory center." : ""}</p>
    </> : <p className="fp-panel">Add a crop to compare options for your farm.</p>}
    <div className="fp-actions fp-section"><Link to="/advisories" navigate={navigate}>View advisories</Link><Link to="/farms" navigate={navigate} className="fp-text">Connected science workspace ↗</Link></div>
  </>;
}
function Living({ plots, navigate, today }: { plots: CropPlan[]; navigate: Navigate; today: string }) {
  const [selected, select] = useState(plots[0]?.id || "");
  const plot = plots.find((item) => item.id === selected) || plots[0];
  const stage = plot?.harvested ? "Harvested" : !plot?.date ? "Date to be set" : plot.date > today ? "Planned planting" : plot.certainty === "estimated" ? "Estimated planting date passed" : "Confirmed planting date reached";
  return <>
    <Intro title="Living Field" action={<Link to="/future-fold" navigate={navigate}>Open Future Fold →</Link>}>Explore your plots and planting dates in a field map.</Intro>
    <div className="fp-field-map"><Tag>Illustrative field map</Tag>
      <div className="fp-plot-grid">{plots.map((item) => <button type="button" key={item.id} aria-pressed={plot?.id === item.id} onClick={() => select(item.id)}><span aria-hidden="true">{icons[item.crop]}</span><strong>{item.plot}</strong><small>{item.crop} · Cycle {item.cycle}{item.example ? " · Example" : ""}</small></button>)}</div>
    </div>
    {plot ? <section className="fp-panel fp-section"><h2>{plot.crop} · {plot.plot}</h2><p>{stage} · {plot.harvested ? dateLabel(plot.harvested) : plot.date ? dateLabel(plot.date) : "No saved date"}</p><p className="fp-muted">{plot.example ? "Example farm plan" : "Saved farm plan"} · Stage label derived from your dates.</p><Link to={foldUrl(plot)} navigate={navigate}>Explore options →</Link></section> : <p className="fp-panel">Add a crop to see it on the map.</p>}
  </>;
}

const navigation = [
  { path: "/", name: "Overview", icon: "⌂" },
  { path: "/farm", name: "My farm", icon: "▤" },
  { path: "/advisories", name: "Advisories", icon: "◇" },
  { path: "/inbox", name: "Inbox", icon: "✉" },
  { path: "/future-fold", name: "Future Fold", icon: "↗" },
  { path: "/living-field", name: "Living Field", icon: "▧" },
];
export function isFarmerPath(path: string) {
  return path === "/" || path === "/register" || navigation.slice(1).some((item) => path === item.path || path.startsWith(item.path + "/"));
}
export function FarmerApp({ path, navigate }: { path: string; navigate: Navigate }) {
  const [plan, update] = useState(localFarmAdapter.load);
  const [storageAvailable, setStorageAvailable] = useState(true);
  const today = farmToday();
  const plots = visiblePlots(plan, today);
  const cards = generateAdvisories(plan, plots, today);
  const open = cards.filter((card) => plan.marks[card.id] !== "dismissed");
  const unread = open.filter((card) => !plan.marks[card.id] || plan.marks[card.id] === "unread").length;
  const [page, id, topic] = path.split("/").filter(Boolean);
  useEffect(() => setStorageAvailable(localFarmAdapter.save(plan)), [plan]);
  useEffect(() => { window.scrollTo(0, 0); }, [path]);
  const mark = (key: string, value: FarmPlan["marks"][string]) => update((current) => current.marks[key] === value ? current : { ...current, marks: { ...current.marks, [key]: value } });
  let content: ReactNode;
  if (page === "register" && !plan.profile) content = <Registration draft={plan.draft} change={(draft) => update((current) => ({ ...current, draft }))} navigate={navigate} save={() => {
    const { name, district, language, preferences, crops, date, certainty } = plan.draft;
    const initialPlots = crops.map((crop, index) => newCrop(crop, "Plot " + (index + 1), date, certainty));
    update((current) => ({ ...current, profile: { name: name.trim(), district: district.trim(), language, preferences }, plots: initialPlots }));
    navigate("/");
  }} />;
  else if (page === "farm") content = <Farm plan={plan} plots={plots} segment={id} update={update} navigate={navigate} today={today} />;
  else if (page === "advisories") content = <AdvisoryCenter key={path} cards={cards} id={id} marks={plan.marks} mark={mark} revised={plan.forecastRevision} revise={() => update((current) => ({ ...current, forecastRevision: !current.forecastRevision }))} navigate={navigate} />;
  else if (page === "inbox") content = <Inbox plan={plan} cards={open} navigate={navigate} change={(preferences, language) => update((current) => ({ ...current, draft: { ...current.draft, preferences, language }, profile: current.profile && { ...current.profile, preferences, language } }))} />;
  else if (page === "future-fold") content = <Fold plots={plots} id={id} topic={topic} plan={plan} update={update} navigate={navigate} today={today} />;
  else if (page === "living-field") content = <Living plots={plots} navigate={navigate} today={today} />;
  else content = <Dashboard plan={plan} plots={plots} cards={open} navigate={navigate} />;
  return <div className="fp-shell">
    <aside className="fp-sidebar">
      <Link to="/" navigate={navigate} className="fp-brand"><span aria-hidden="true">◈</span> TerraPulse</Link>
      <nav aria-label="Farmer navigation">{navigation.map((item) => <Link key={item.path} className="fp-nav" current={item.path === "/" ? path === "/" : path === item.path || path.startsWith(item.path + "/")} to={item.path} navigate={navigate}><span aria-hidden="true">{item.icon}</span>{item.name}{item.path === "/inbox" && (plan.profile || plan.draft).preferences.inApp && unread > 0 && <small aria-label={unread + " unread"}>{unread}</small>}</Link>)}</nav>
      <div className="fp-sidebar-foot"><span className="fp-avatar" aria-hidden="true">{plan.profile?.name.slice(0, 1).toUpperCase() || "T"}</span><div><strong>{plan.profile?.name || "Example workspace"}</strong><small>Browser workspace</small></div></div>
    </aside>
    <main className="fp-main">{!storageAvailable && <p className="fp-error" role="status">Browser storage is unavailable. Changes will last until this page closes.</p>}{content}</main>
  </div>;
}
