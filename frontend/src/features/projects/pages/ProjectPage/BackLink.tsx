import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { PORTFOLIO_PATH } from "../../paths";

/** Le lien de retour au Portfolio, en tête de chaque état de la page. */
export function BackLink() {
  return (
    <Link to={PORTFOLIO_PATH} className="text-sm text-primary underline underline-offset-4">
      {t("projects.page.back")}
    </Link>
  );
}
