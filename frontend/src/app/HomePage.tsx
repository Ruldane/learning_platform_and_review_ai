import { t } from "@/shared/i18n/t";

export function HomePage() {
  return (
    <>
      <h1 className="text-2xl font-semibold">{t("app.welcome.title")}</h1>
      <p className="mt-2 text-muted-foreground">{t("app.welcome.intro")}</p>
    </>
  );
}
