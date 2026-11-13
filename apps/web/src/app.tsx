import { Component, ErrorInfo, ReactNode, useEffect, useMemo, useState } from "react";
import { AppShell, Route } from "./components/layout";
import { EmptyState, ErrorState, PageContainer, ReusableCard } from "./components/ui";
import { getInitialLocale, translations } from "./i18n";

function getRoute(): Route | null {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  return path === "/" || path === "/connect" ? "connect" : path === "/assisted" ? "assisted" : path === "/observatory" ? "observatory" : null;
}

function useRoute() {
  const [route, setRoute] = useState<Route | null>(getRoute);
  useEffect(() => {
    const handlePopState = () => setRoute(getRoute());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);
  const navigate = (nextRoute: Route) => {
    window.history.pushState({}, "", `/${nextRoute}`);
    setRoute(nextRoute);
  };
  return { route, navigate };
}

function WebGLCheck() {
  const [available, setAvailable] = useState<boolean | null>(null);
  useEffect(() => {
    let supported = false;
    try {
      const canvas = document.createElement("canvas");
      supported = Boolean(canvas.getContext("webgl2") || canvas.getContext("webgl"));
    } catch {
      supported = false;
    }
    setAvailable(supported);
  }, []);
  return available;
}

function ConnectPage({ copy, onNavigate }: { copy: typeof translations.en; onNavigate: (route: Route) => void }) {
  return (
    <PageContainer>
      <section className="hero-section">
        <div className="hero-copy"><p className="eyebrow">01 / Farmer workspace</p><h2>{copy.connectTitle}</h2><p>{copy.connectDescription}</p><button className="primary-button" onClick={() => onNavigate("observatory")}>{copy.configureAction}<span aria-hidden="true">→</span></button></div>
        <div className="hero-orbit" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit-core"><span>TP</span></div><i className="orbit-dot dot-one" /><i className="orbit-dot dot-two" /></div>
      </section>
      <EmptyState title={copy.configureTitle} description={copy.configureDescription} />
      <section className="section-block"><div className="section-heading"><div><p className="eyebrow">The platform</p><h2>{copy.capabilitiesTitle}</h2></div><p>{copy.capabilitiesDescription}</p></div><div className="card-grid">
        <ReusableCard><span className="card-number">01</span><span className="card-icon">▦</span><h3>{copy.farmWorkspace}</h3><p>{copy.farmWorkspaceDescription}</p><span className="card-link">{copy.upcoming} <span>↗</span></span></ReusableCard>
        <ReusableCard><span className="card-number">02</span><span className="card-icon">◇</span><h3>{copy.cropPlanning}</h3><p>{copy.cropPlanningDescription}</p><span className="card-link">{copy.upcoming} <span>↗</span></span></ReusableCard>
        <ReusableCard className="card-dark"><span className="card-number">03</span><span className="card-icon">◌</span><h3>{copy.observatory}</h3><p>{copy.observatoryDescription}</p><button className="text-button" onClick={() => onNavigate("observatory")}>{copy.configureAction} <span>→</span></button></ReusableCard>
      </div></section>
    </PageContainer>
  );
}

function AssistedPage({ copy }: { copy: typeof translations.en }) {
  return <PageContainer><section className="page-intro"><p className="eyebrow">02 / FPO & field workers</p><h2>{copy.assistedTitle}</h2><p>{copy.assistedDescription}</p></section><div className="assisted-layout"><section className="support-panel"><div className="panel-kicker">FIELD OPERATIONS</div><div className="support-illustration" aria-hidden="true"><span>◎</span><i /><i /><i /></div><h3>{copy.fieldWorkspace}</h3><p>{copy.fieldWorkspaceDescription}</p></section><div className="support-cards"><ReusableCard><span className="card-icon">✦</span><h3>{copy.supportOverview}</h3><p>{copy.supportOverviewDescription}</p><span className="card-link">{copy.upcoming} <span>↗</span></span></ReusableCard><ReusableCard><span className="card-icon">⌁</span><h3>{copy.futureCapability}</h3><p>{copy.assistedDescription}</p><span className="card-link">{copy.upcoming} <span>↗</span></span></ReusableCard></div></div></PageContainer>;
}

function ObservatoryFallback({ copy, onNavigate }: { copy: typeof translations.en; onNavigate: (route: Route) => void }) {
  return <div className="observatory-fallback"><div className="fallback-symbol" aria-hidden="true">◌</div><h3>{copy.immersiveUnavailable}</h3><p>{copy.immersiveUnavailableDescription}</p><button className="secondary-button" onClick={() => onNavigate("connect")}>{copy.returnToConnect} <span>→</span></button></div>;
}

function ObservatoryPage({ copy, onNavigate }: { copy: typeof translations.en; onNavigate: (route: Route) => void }) {
  const webgl = WebGLCheck();
  return <PageContainer><section className="page-intro observatory-intro"><p className="eyebrow">03 / Scientific exploration</p><h2>{copy.observatoryTitle}</h2><p>{copy.observatoryDescription}</p></section><section className="observatory-layout"><div className="viewport-panel" aria-label={copy.viewportLabel}><div className="viewport-toolbar"><span className="live-indicator" /> VIEWPORT / 01 <span>◫</span></div>{webgl === false ? <ObservatoryFallback copy={copy} onNavigate={onNavigate} /> : <div className="viewport-placeholder"><div className="field-grid" aria-hidden="true" /><div className="viewport-center"><span className="viewport-icon">◌</span><h3>{copy.livingField}</h3><p>{copy.livingFieldDescription}</p></div></div>}</div><aside className="observatory-aside"><div className="aside-label">THE NEXT LAYER</div><h3>{copy.futureFoldTitle}</h3><p>{copy.futureFoldDescription}</p><div className="signal-list"><div><span className="signal-dot green" />Field context <strong>—</strong></div><div><span className="signal-dot amber" />Environmental signals <strong>—</strong></div><div><span className="signal-dot blue" />Decision pathways <strong>—</strong></div></div></aside></section></PageContainer>;
}

function NotFound({ copy, onNavigate }: { copy: typeof translations.en; onNavigate: (route: Route) => void }) {
  return <PageContainer><div className="not-found"><ErrorState label={copy.notFound} /><h2>{copy.notFound}</h2><p>{copy.notFoundDescription}</p><button className="primary-button" onClick={() => onNavigate("connect")}>{copy.goToConnect} <span>→</span></button></div></PageContainer>;
}

class AppErrorBoundary extends Component<{ copy: typeof translations.en; children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("TerraPulse workspace rendering failed", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return <PageContainer><div className="not-found"><ErrorState label={this.props.copy.error} /><h2>{this.props.copy.error}</h2><p>{this.props.copy.notFoundDescription}</p></div></PageContainer>;
    }
    return this.props.children;
  }
}

export function App() {
  const { route, navigate } = useRoute();
  const [locale, setLocale] = useState(getInitialLocale);
  const copy = useMemo(() => translations[locale], [locale]);
  const changeLocale = (nextLocale: typeof locale) => { setLocale(nextLocale); window.localStorage.setItem("terrapulse-locale", nextLocale); };
  const title = route === "assisted" ? copy.assisted : route === "observatory" ? copy.observatory : route === "connect" ? copy.connect : copy.connect;
  const subtitle = route === "assisted" ? copy.assistedDescription : route === "observatory" ? copy.observatoryDescription : copy.connectDescription;
  return <AppErrorBoundary copy={copy}><AppShell route={route ?? "connect"} copy={copy} locale={locale} onLocaleChange={changeLocale} onNavigate={navigate} title={title} subtitle={subtitle}>{route === "connect" && <ConnectPage copy={copy} onNavigate={navigate} />}{route === "assisted" && <AssistedPage copy={copy} />}{route === "observatory" && <ObservatoryPage copy={copy} onNavigate={navigate} />}{route === null && <NotFound copy={copy} onNavigate={navigate} />}</AppShell></AppErrorBoundary>;
}
