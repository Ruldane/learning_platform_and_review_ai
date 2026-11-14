import { t } from "@/shared/i18n/t";
import { agentIdentity } from "@/shared/session-ui";
import type { ModificationView } from "../viewTypes";

interface ModificationHeaderProps {
  mod: ModificationView;
  headingId: string;
}

/** Le type et l'action, l'état écrit en toutes lettres, et l'agent qui a proposé la modification. */
export function ModificationHeader({ mod, headingId }: ModificationHeaderProps) {
  return (
    <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
      <h3 id={headingId} className="text-sm font-semibold">
        {t("cv.mod.heading", {
          type: t(`cv.mod.type.${mod.type}`),
          action: t(`cv.mod.action.${mod.action}`),
        })}
      </h3>
      <span className="rounded-md border px-1.5 py-0.5 text-xs font-medium">
        {t(`cv.mod.status.${mod.status}`)}
      </span>
      {mod.ignoredIn != null ? (
        <span className="rounded-md border border-foreground/60 px-1.5 py-0.5 text-xs font-medium">
          {t("cv.mod.ignored", { number: mod.ignoredIn })}
        </span>
      ) : null}
      <span className="text-xs text-muted-foreground">
        {t("cv.mod.author", { name: agentIdentity(mod.author).name })}
      </span>
    </header>
  );
}
