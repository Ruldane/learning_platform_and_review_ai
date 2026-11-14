import { t } from "@/shared/i18n/t";
import { ProfileImportForm } from "../../components/ProfileImportForm";
import { useImportProfile } from "../../hooks/useImportProfile";

/** Pas encore de profil : importer son CV (et LinkedIn, une note) pour en recevoir un brouillon. */
export function ImportPanel({ withTitle = true }: { withTitle?: boolean }) {
  const { start, pending, error } = useImportProfile();
  return (
    <section className="flex flex-col gap-3">
      {withTitle ? (
        <>
          <h2 className="text-lg font-medium">{t("cv.profilePage.importTitle")}</h2>
          <p className="max-w-prose text-muted-foreground">{t("cv.profilePage.importHint")}</p>
        </>
      ) : null}
      <ProfileImportForm pending={pending} error={error} onSubmit={start} />
    </section>
  );
}
