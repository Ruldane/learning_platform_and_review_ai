import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { DuplicateAlert } from "@/shared/ui/DuplicateAlert";
import { InlineError } from "@/shared/ui/states/InlineError";
import { useCreateApplication } from "../../hooks/useCreateApplication";
import { toAlertView } from "../../toView";
import { applicationPath } from "../../urls";
import { ManualFields } from "./ManualFields";
import { EMPTY_DRAFT, manualProblem, toBody, type ManualDraft } from "./manualDraft";

/**
 * Créer une fiche à la main. Une fiche qui ressemble à une autre (409) affiche l'alerte de doublon :
 * ouvrir la fiche existante, « C'est un autre poste » (la fiche est alors créée, avec la liste des
 * fiches confirmées distinctes) ou annuler. Une fois créée, la fiche s'ouvre, avec les informations
 * « même entreprise » éventuelles.
 */
export function ManualSection() {
  const navigate = useNavigate();
  const create = useCreateApplication();
  const [draft, setDraft] = useState<ManualDraft>(EMPTY_DRAFT);
  const [refused, setRefused] = useState(false);

  async function submit(distinctFrom: string[] = []) {
    setRefused(true);
    if (manualProblem(draft) !== null || create.pending) return;
    const created = await create.create(toBody(draft, distinctFrom));
    if (created) {
      void navigate(applicationPath(created.application.id), { state: { info: created.info } });
    }
  }

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    void submit();
  };
  return (
    <section aria-labelledby="manual-title" className="flex flex-col gap-3">
      <h2 id="manual-title" className="text-lg font-semibold">
        {t("applications.newPage.manualTitle")}
      </h2>
      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-3">
        <ManualFields
          draft={draft}
          problem={refused ? manualProblem(draft) : null}
          onChange={setDraft}
        />
        {create.error ? <InlineError message={create.error} /> : null}
        <DuplicateAlert
          alerts={create.alerts.map(toAlertView)}
          onOpen={(id) => void navigate(applicationPath(id))}
          onDistinct={() => void submit(create.alerts.map((alert) => alert.application_id))}
          onCancel={create.clearAlerts}
        />
        <div>
          <Button type="submit" disabled={create.pending}>
            {t(
              create.pending
                ? "applications.newPage.manualPending"
                : "applications.newPage.manualAction",
            )}
          </Button>
        </div>
      </form>
    </section>
  );
}
