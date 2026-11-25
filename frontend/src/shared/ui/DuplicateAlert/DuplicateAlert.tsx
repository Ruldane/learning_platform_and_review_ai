import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";

export type DuplicateLevel = "certain" | "probable" | "possible" | "info";

/** A record close to the incoming job posting: the `message` is the server's (SPEC 6.3). */
export interface DuplicateAlertView {
  level: DuplicateLevel;
  applicationId: string;
  company: string;
  title: string;
  status:
    | "to_apply"
    | "applied"
    | "followed_up"
    | "interview"
    | "offer"
    | "rejected"
    | "no_answer"
    | "withdrawn";
  message: string;
}

interface DuplicateAlertProps {
  alerts: DuplicateAlertView[];
  /** Opens the closest existing record. */
  onOpen: (applicationId: string) => void;
  /** January confirms it is a different job. */
  onDistinct: () => void;
  onCancel: () => void;
}

const STRENGTH: DuplicateLevel[] = ["certain", "probable", "possible", "info"];
const TONE: Record<DuplicateLevel, string> = {
  certain: "border-destructive bg-destructive/10",
  probable: "border-destructive/60 bg-destructive/5",
  possible: "border-border bg-muted",
  info: "border-border bg-card",
};

const strength = (alert: DuplicateAlertView) => STRENGTH.indexOf(alert.level);

/**
 * The duplicate alert: the server's message for the strongest alert, the list of the others, and
 * the three choices (open the record, « c'est un autre poste », cancel). The level is written in
 * full words; a simple notice (`info`) is only a note, with no choices.
 */
export function DuplicateAlert({ alerts, onOpen, onDistinct, onCancel }: DuplicateAlertProps) {
  const sorted = [...alerts].sort((a, b) => strength(a) - strength(b));
  const [main, ...others] = sorted;
  if (!main) return null;
  const info = main.level === "info";
  return (
    <div
      role={info ? "note" : "alert"}
      className={cn("flex flex-col gap-3 rounded-xl border p-4 text-sm", TONE[main.level])}
    >
      <p className="text-xs font-semibold tracking-wide uppercase">
        {t(`applications.duplicate.level.${main.level}`)}
      </p>
      <p>{main.message}</p>
      {others.length > 0 && (
        <ul aria-label={t("applications.duplicate.others")} className="flex flex-col gap-1">
          {others.map((alert) => (
            <li key={alert.applicationId} className="text-muted-foreground">
              {t("applications.duplicate.other", {
                company: alert.company,
                title: alert.title,
                status: t(`applications.status.${alert.status}`),
                level: t(`applications.duplicate.level.${alert.level}`),
              })}
            </li>
          ))}
        </ul>
      )}
      {!info && (
        <div className="flex flex-wrap gap-2">
          <Button type="button" onClick={() => onOpen(main.applicationId)}>
            {t("applications.duplicate.open")}
          </Button>
          <Button type="button" variant="outline" onClick={onDistinct}>
            {t("applications.duplicate.distinct")}
          </Button>
          <Button type="button" variant="ghost" onClick={onCancel}>
            {t("applications.duplicate.cancel")}
          </Button>
        </div>
      )}
    </div>
  );
}
