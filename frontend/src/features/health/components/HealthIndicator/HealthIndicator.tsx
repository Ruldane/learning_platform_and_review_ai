import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";

/** Shape of the `GET /health` report (generated types; not imported, the split rule forbids it). */
interface HealthReportView {
  status: "ok" | "degraded" | "down";
  checks: Record<string, { ok: boolean; detail: string }>;
}

interface HealthIndicatorProps {
  report?: HealthReportView;
  isLoading: boolean;
  /** The request failed: the server is unreachable. */
  isError?: boolean;
}

type Tone = "neutral" | "ok" | "warn" | "bad";

const DOT_CLASS: Record<Tone, string> = {
  neutral: "bg-muted-foreground",
  ok: "bg-emerald-600",
  warn: "bg-amber-600",
  bad: "bg-red-600",
};

function summarize({ report, isLoading, isError }: HealthIndicatorProps) {
  if (isError) return { tone: "bad", label: t("health.unreachable") } as const;
  if (isLoading || !report) return { tone: "neutral", label: t("health.loading") } as const;
  if (report.status === "ok") return { tone: "ok", label: t("health.allOk") } as const;
  if (report.status === "degraded") return { tone: "warn", label: t("health.degraded") } as const;
  return { tone: "bad", label: t("health.down") } as const;
}

/** Service health light: colored dot and text (color is never alone). */
export function HealthIndicator(props: HealthIndicatorProps) {
  const { tone, label } = summarize(props);
  const failing =
    tone === "warn" && props.report
      ? Object.entries(props.report.checks).filter(([, check]) => !check.ok)
      : [];
  return (
    <div role="status" aria-label={t("health.label")} className="text-sm">
      <p className="flex items-center gap-2">
        <span aria-hidden="true" className={cn("size-2.5 rounded-full", DOT_CLASS[tone])} />
        <span>{label}</span>
      </p>
      {failing.length > 0 ? (
        <ul className="mt-1 text-muted-foreground">
          {failing.map(([service, check]) => (
            <li key={service}>{t("health.failing", { service, detail: check.detail })}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
