import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { DuplicateAlert, type DuplicateAlertView } from "@/shared/ui/DuplicateAlert";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { ExistingApplicationView } from "../viewTypes";
import { ExistingApplication } from "./ExistingApplication";

interface ApplicationCheckProps {
  /** La candidature qui existe déjà pour cette offre, s'il y en a une. */
  own: ExistingApplicationView | null;
  /** Les fiches proches (doublons, informations) ; l'alerte les ordonne et dit le niveau. */
  alerts: DuplicateAlertView[];
  creating: boolean;
  error: string | null;
  onOpen: (applicationId: string) => void;
  onCreate: () => void;
  /** « C'est un autre poste » : la candidature est créée malgré les fiches proches. */
  onDistinct: () => void;
  onCancel: () => void;
}

/**
 * La candidature d'une offre : la fiche existante à ouvrir, ou, sinon, l'alerte de doublon quand
 * des fiches lui ressemblent (ses trois choix) et le bouton « Créer la candidature » (caché tant
 * qu'une fiche proche demande un choix : l'alerte le porte). Une simple information ne bloque rien.
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
