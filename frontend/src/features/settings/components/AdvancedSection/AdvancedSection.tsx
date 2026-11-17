import { useId } from "react";
import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface AdvancedSectionProps {
  open: boolean;
  onToggle: () => void;
  /**
   * Le contenu n'est monté que déployé : rien n'est lu ni dessiné tant que la section est repliée.
   */
  children: ReactNode;
}

/** « Mode avancé » (SPEC 11.2) : une section repliée par défaut, ouverte par un bouton. */
export function AdvancedSection({ open, onToggle, children }: AdvancedSectionProps) {
  const panelId = useId();
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg font-medium">{t("settings.advanced.title")}</h2>
      <p className="text-muted-foreground">{t("settings.advanced.intro")}</p>
      <div>
        <Button
          type="button"
          variant="outline"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={onToggle}
        >
          {open ? t("settings.advanced.hide") : t("settings.advanced.show")}
        </Button>
      </div>
      <div id={panelId} hidden={!open}>
        {open ? children : null}
      </div>
    </section>
  );
}
