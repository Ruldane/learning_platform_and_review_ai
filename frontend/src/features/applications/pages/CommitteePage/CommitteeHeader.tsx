import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { SimulationBanner } from "../../components/SimulationBanner";
import { applicationPath } from "../../urls";

interface CommitteeHeaderProps {
  applicationId: string;
  application: { company: string; title: string } | undefined;
}

/** Le titre, la fiche jugée, le bandeau permanent « Simulation, pas une prédiction » et le retour à la fiche. */
export function CommitteeHeader({ applicationId, application }: CommitteeHeaderProps) {
  return (
    <header className="flex flex-col gap-2">
      <h1 className="text-2xl font-semibold">{t("applications.committeePage.title")}</h1>
      {application ? (
        <p className="font-medium">
          {t("applications.committeePage.for", {
            company: application.company,
            title: application.title,
          })}
        </p>
      ) : null}
      <SimulationBanner />
      <p className="max-w-prose text-muted-foreground">{t("applications.committeePage.intro")}</p>
      <Link
        to={applicationPath(applicationId)}
        className="w-fit text-sm font-medium text-primary underline underline-offset-4"
      >
        {t("applications.committeePage.back")}
      </Link>
    </header>
  );
}
