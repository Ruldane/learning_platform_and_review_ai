import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { ImportPanel } from "./ImportPanel";

/** « Importer d'autres documents » : rouvre le formulaire d'import sous un profil déjà là. */
export function ReimportSection() {
  const [open, setOpen] = useState(false);
  return (
    <section className="flex flex-col gap-3">
      <Button
        variant="outline"
        className="self-start"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        {open ? t("cv.profilePage.reimportClose") : t("cv.profilePage.reimport")}
      </Button>
      {open ? <ImportPanel withTitle={false} /> : null}
    </section>
  );
}
