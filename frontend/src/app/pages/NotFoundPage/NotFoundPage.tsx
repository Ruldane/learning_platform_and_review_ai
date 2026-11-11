import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

export function NotFoundPage() {
  return (
    <>
      <h1 className="text-2xl font-semibold">{t("app.notFound.title")}</h1>
      <Button asChild className="mt-4">
        <Link to="/">{t("app.notFound.back")}</Link>
      </Button>
    </>
  );
}
