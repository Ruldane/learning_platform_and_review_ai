import { Link } from "react-router";
import { t } from "@/shared/i18n/t";

/** « Profil validé : version N », avec le lien vers les modèles de CV ; rien avant la validation. */
export function SavedNotice({ version }: { version: number | null }) {
  if (version === null) return null;
  return (
    <p role="status" className="text-sm font-medium">
      {t("cv.profilePage.saved", { version })}{" "}
      <Link to="/carriere/cv" className="underline underline-offset-4">
        {t("cv.profilePage.toCv")}
      </Link>
    </p>
  );
}
