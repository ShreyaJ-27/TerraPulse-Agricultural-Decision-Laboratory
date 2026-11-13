import { ReactNode } from "react";
import { Locale, localeLabels } from "../i18n";

export function PageContainer({ children }: { children: ReactNode }) {
  return <main className="page-container">{children}</main>;
}

export function ReusableCard({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <article className={`info-card ${className}`}>{children}</article>;
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <section className="empty-state" aria-labelledby="empty-state-title">
      <span className="state-icon" aria-hidden="true">⌁</span>
      <div>
        <h2 id="empty-state-title">{title}</h2>
        <p>{description}</p>
        {action}
      </div>
    </section>
  );
}

export function LoadingState({ label }: { label: string }) {
  return <div className="loading-state" role="status"><span className="spinner" aria-hidden="true" />{label}</div>;
}

export function ErrorState({ label }: { label: string }) {
  return <div className="error-state" role="alert"><span aria-hidden="true">!</span>{label}</div>;
}

export function LanguageSelector({
  locale,
  onChange,
  label,
}: {
  locale: Locale;
  onChange: (locale: Locale) => void;
  label: string;
}) {
  return (
    <label className="language-selector">
      <span>{label}</span>
      <select value={locale} onChange={(event) => onChange(event.target.value as Locale)} aria-label={label}>
        {Object.entries(localeLabels).map(([value, name]) => <option key={value} value={value}>{name}</option>)}
      </select>
    </label>
  );
}
