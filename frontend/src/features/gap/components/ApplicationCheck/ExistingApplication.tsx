import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ExistingApplicationView } from "../viewTypes";

interface ExistingApplicationProps {
  application: ExistingApplicationView;
  onOpen: (applicationId: string) => void;
}

/** « Tu as déjà une candidature pour cette offre » et son bouton d'ouverture. */
export function ExistingApplication({ application, onOpen }: ExistingApplicationProps) {
  return (
    <>
      <p>
        {t("applications.check.existing", {
          company: application.company,
          title: application.title,
          status: t(`applications.status.${application.status}`),
        })}
      </p>
      <div>
        <Button type="button" onClick={() => onOpen(application.id)}>
          {t("applications.check.open")}
        </Button>
      </div>
    </>
  );
}
