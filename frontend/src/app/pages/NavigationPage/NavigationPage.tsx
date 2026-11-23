import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { sectionLanding, type Section } from "../../navigation";

export function NavigationPage({
  section,
  children,
}: {
  section: Exclude<Section, "home">;
  children: ReactNode;
}) {
  return (
    <div className="grid gap-6">
      <header className="grid gap-2 border-b pb-5">
        <h1 className="text-2xl font-semibold">{t(sectionLanding(section).labelKey)}</h1>
        <p className="text-muted-foreground">{t(`navigation.headings.${section}`)}</p>
      </header>
      {children}
    </div>
  );
}
