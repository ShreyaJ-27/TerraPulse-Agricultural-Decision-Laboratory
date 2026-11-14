import { ReactNode, useEffect, useState } from "react";
import { Locale, Translation, localeLabels } from "../i18n";
import { LanguageSelector } from "./ui";

export type Route = string;

type NavItem = { route: Route; label: string; icon: string };

export function NavigationItem({
  item,
  active,
  onNavigate,
}: {
  item: NavItem;
  active: boolean;
  onNavigate: (route: Route) => void;
}) {
  return (
    <button
      className={`nav-item ${active ? "active" : ""} `}
      onClick={() => onNavigate(item.route)}
      aria-current={active ? "page" : undefined}
      aria-label={item.label}
    >
      <span className="nav-icon" aria-hidden="true">{item.icon}</span>
      <span>{item.label}</span>
    </button>
  );
}

export function Sidebar({
  route,
  copy,
  locale,
  onLocaleChange,
  onNavigate,
}: {
  route: Route;
  copy: Translation;
  locale: Locale;
  onLocaleChange: (locale: Locale) => void;
  onNavigate: (route: Route) => void;
}) {
  const primary: NavItem[] = [
    { route: "connect", label: copy.workspace, icon: "⌂" },
    { route: "advisories", label: "Advisories", icon: "◎" },
    { route: "observatory", label: copy.observatory, icon: "◌" },
  ];
  const workspace: NavItem[] = [
    { route: "crop-planning", label: copy.cropPlanning, icon: "◇" },
    { route: "calendar", label: "Calendar", icon: "▤" },
    { route: "future-fold", label: copy.futureFold, icon: "↗" },
    { route: "living-field", label: "Living Field", icon: "▦" },
    { route: "saved-decisions", label: copy.savedDecisions, icon: "♡" },
  ];
  return (
    <aside className="sidebar" aria-label="Primary navigation">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true"><span /></span>
        <span><strong>Terra</strong>Pulse<small>AGRICULTURAL INTELLIGENCE</small></span>
      </div>
      <div className="nav-section">
        <p className="nav-label">Explore</p>
        {primary.map((item) => <NavigationItem key={item.label} item={item} active={route === item.route} onNavigate={onNavigate} />)}
      </div>
      <div className="nav-section nav-section-secondary">
        <p className="nav-label">Workspace</p>
        {workspace.map((item) => <NavigationItem key={item.route} item={item} active={route === item.route} onNavigate={onNavigate} />)}
      </div>
      <div className="sidebar-footer">
        <LanguageSelector locale={locale} onChange={onLocaleChange} label={copy.language} />
        <div className="sidebar-status"><span className="status-dot" />{copy.connected}<small>Browser ready</small></div>
        <p className="version">{copy.version}</p>
      </div>
    </aside>
  );
}

export function ConnectionStatus({ copy }: { copy: Translation }) {
  const [online, setOnline] = useState(window.navigator.onLine);
  useEffect(() => {
    const update = () => setOnline(window.navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => { window.removeEventListener("online", update); window.removeEventListener("offline", update); };
  }, []);
  return (
    <div className={`connection-status ${online ? "online" : "offline"}`} role="status" aria-live="polite">
      <span className="status-dot" />
      <span>{online ? copy.connected : copy.offline}</span>
      {!online && <small>Live data retrieval unavailable</small>}
    </div>
  );
}

export function TopHeader({
  title,
  subtitle,
  copy,
  locale,
  onLocaleChange,
  onMenu,
}: {
  title: string;
  subtitle: string;
  copy: Translation;
  locale: Locale;
  onLocaleChange: (locale: Locale) => void;
  onMenu: () => void;
}) {
  return (
    <header className="top-header">
      <button className="menu-button" onClick={onMenu} aria-label={copy.menu}>☰</button>
      <div><p className="breadcrumb">TerraPulse <span>/</span> {title}</p><h1>{title}</h1><p className="header-subtitle">{subtitle}</p></div>
      <div className="header-actions"><ConnectionStatus copy={copy} /><LanguageSelector locale={locale} onChange={onLocaleChange} label={copy.language} /></div>
    </header>
  );
}

export function AppShell({ children, farmWorkspace = false, ...props }: { children: ReactNode; farmWorkspace?: boolean } & Omit<Parameters<typeof Sidebar>[0], "children"> & Omit<Parameters<typeof TopHeader>[0], "onMenu">) {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className={farmWorkspace ? "app-shell farm-workspace-shell" : "app-shell"}>
      <div className={`sidebar-wrap ${menuOpen ? "open" : ""}`}><Sidebar {...props} onNavigate={(route) => { setMenuOpen(false); props.onNavigate(route); }} /></div>
      {menuOpen && <button className="scrim" onClick={() => setMenuOpen(false)} aria-label="Close navigation" />}
      <div className="app-main"><TopHeader {...props} onMenu={() => setMenuOpen(true)} /><div className="content-wrap">{children}</div></div>
    </div>
  );
}

export { localeLabels };
