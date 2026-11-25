import { Link } from "react-router";
import { t } from "@/shared/i18n/t";

/** « Profil validé : version N », with the link to the CV templates; nothing before validation. */
export function SavedNotice({ version }: { version: number | null }) {
  if (version === null) return null;
  return (
    <p role="status" className="text-sm font-medium">
      {t("cv.profilePage.saved", { version })}{" "}
      <Link to="/career/cv" className="underline underline-offset-4">
        {t("cv.profilePage.toCv")}
      </Link>
    </p>
  );
}
