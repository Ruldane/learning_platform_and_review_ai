import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import { CV_VERSIONS_PATH } from "../../urls";
import { DrawerSection } from "./DrawerSection";

/** La version du CV envoyée avec la fiche, et le lien vers la page des versions. */
export function VersionSection({ number }: { number: number | null }) {
  return (
    <DrawerSection title={t("applications.drawer.versionTitle")}>
      {number === null ? (
        <p className="text-sm text-muted-foreground">{t("applications.drawer.versionNone")}</p>
      ) : (
        <p className="text-sm">{t("applications.drawer.versionNumber", { number })}</p>
      )}
      <div>
        <Link to={CV_VERSIONS_PATH} className={buttonVariants({ variant: "outline" })}>
          {t("applications.drawer.versionOpen")}
        </Link>
      </div>
    </DrawerSection>
  );
}
