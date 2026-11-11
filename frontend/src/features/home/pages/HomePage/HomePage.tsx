import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";

export function HomePage() {
  return (
    <>
      <h1 className="text-2xl font-semibold">{t("home.title")}</h1>
      <p className="mt-2 text-muted-foreground">{t("home.intro")}</p>
      <div className="mt-6">
        <EmptyState title={t("home.empty.title")} description={t("home.empty.description")} />
      </div>
    </>
  );
}
