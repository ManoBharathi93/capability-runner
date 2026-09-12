import { AlertTriangle, Check, LoaderCircle } from "lucide-react";
import type { ReactNode } from "react";

export function StatusBadge({ status }: { status: string | null | undefined }) {
  const normalized = status?.toUpperCase() ?? "UNKNOWN";
  const tone = normalized.includes("SUCCESS") || normalized === "READY" || normalized === "COMPLETED"
    ? "success"
    : normalized.includes("FAIL") || normalized === "STOPPED"
      ? "danger"
      : normalized.includes("BUSINESS") || normalized.includes("PAUSE") || normalized.includes("INTERVENTION")
        ? "warning"
        : "info";
  return <span className={`status-badge ${tone}`}><span />{humanize(normalized)}</span>;
}

export function LoadingState({ label = "Loading workspace data" }: { label?: string }) {
  return <div className="state-message"><LoaderCircle className="spin" size={25} /><strong>{label}</strong></div>;
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="state-message error-state">
      <AlertTriangle size={25} />
      <strong>Unable to load this view</strong>
      <p>{message}</p>
      {retry && <button className="button button-secondary" type="button" onClick={retry}>Try again</button>}
    </div>
  );
}

export function EmptyState({ icon, title, copy, action }: { icon: ReactNode; title: string; copy: string; action?: ReactNode }) {
  return <div className="empty-state">{icon}<h4>{title}</h4><p>{copy}</p>{action}</div>;
}

export function SuccessMark() {
  return <span className="success-mark"><Check size={18} strokeWidth={3} /></span>;
}

export function humanize(value: string): string {
  return value.toLowerCase().replaceAll("_", " ").replace(/(^|\s)\S/g, (letter) => letter.toUpperCase());
}

export function formatDate(value: string | undefined): string {
  if (!value) return "Unavailable";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}