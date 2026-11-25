import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { PORTFOLIO_PATH } from "../../paths";

/** The link back to the Portfolio, at the top of each state of the page. */
export function BackLink() {
  return (
    <Link to={PORTFOLIO_PATH} className="text-sm text-primary underline underline-offset-4">
      {t("projects.page.back")}
    </Link>
  );
}
