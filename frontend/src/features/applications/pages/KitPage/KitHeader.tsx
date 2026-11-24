import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { applicationPath } from "../../urls";

interface KitHeaderProps {
  applicationId: string;
  application: { company: string; title: string } | undefined;
}

/** Identify the application, link back to it, and explain how the kit works. */
export function KitHeader({ applicationId, application }: KitHeaderProps) {
  return (
    <header className="flex flex-col gap-1">
      <h1 className="text-2xl font-semibold">{t("applications.kitPage.title")}</h1>
      {application ? (
        <p className="font-medium">
          {t("applications.kitPage.for", {
            company: application.company,
            title: application.title,
          })}
        </p>
      ) : null}
      <p className="max-w-prose text-muted-foreground">{t("applications.kitPage.intro")}</p>
      <Link
        to={applicationPath(applicationId)}
        className="w-fit text-sm font-medium text-primary underline underline-offset-4"
      >
        {t("applications.kitPage.back")}
      </Link>
    </header>
  );
}
