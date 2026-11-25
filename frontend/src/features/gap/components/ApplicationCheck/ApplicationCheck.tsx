import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { DuplicateAlert, type DuplicateAlertView } from "@/shared/ui/DuplicateAlert";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { ExistingApplicationView } from "../viewTypes";
import { ExistingApplication } from "./ExistingApplication";

interface ApplicationCheckProps {
  /** The application that already exists for this posting, if any. */
  own: ExistingApplicationView | null;
  /** The close cards (duplicates, notes); the alert sorts them and states the level. */
  alerts: DuplicateAlertView[];
  creating: boolean;
  error: string | null;
  onOpen: (applicationId: string) => void;
  onCreate: () => void;
  /** « C'est un autre poste »: the application is created despite the close cards. */
  onDistinct: () => void;
  onCancel: () => void;
}

/**
 * A posting's application: the existing card to open, or otherwise the duplicate alert when
 * cards resemble it (its three choices) and the « Créer la candidature » button (hidden while
 * a close card needs a choice: the alert carries it). A plain note blocks nothing.
 */
export function ApplicationCheck({
  own,
  alerts,
  creating,
  error,
  onOpen,
  onCreate,
  onDistinct,
  onCancel,
}: ApplicationCheckProps) {
  const blocking = alerts.some((alert) => alert.level !== "info");
  return (
    <section
      aria-label={t("applications.check.label")}
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      {own ? (
        <ExistingApplication application={own} onOpen={onOpen} />
      ) : (
        <>
          <DuplicateAlert
            alerts={alerts}
            onOpen={onOpen}
            onDistinct={onDistinct}
            onCancel={onCancel}
          />
          {error ? <InlineError message={error} /> : null}
          {blocking ? null : (
            <div>
              <Button type="button" disabled={creating} onClick={onCreate}>
                {t(creating ? "applications.check.creating" : "applications.check.create")}
              </Button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
