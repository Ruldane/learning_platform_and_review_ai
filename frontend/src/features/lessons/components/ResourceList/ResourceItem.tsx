import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import type { ResourceView } from "../viewTypes";
import { ResourceAttachment } from "./ResourceAttachment";
import { ResourceTitle } from "./ResourceTitle";

interface ResourceItemProps {
  resource: ResourceView;
  onToggleStatus: (resourceId: string, status: ResourceView["status"]) => void;
}

/** « Français », « anglais »… : le nom de la langue, ou son code si le navigateur ne le connaît pas. */
function languageName(code: string): string {
  try {
    return new Intl.DisplayNames(["fr"], { type: "language" }).of(code) ?? code;
  } catch {
    return code;
  }
}

function facts(resource: ResourceView): string[] {
  const minutes = resource.durationMinutes;
  return [
    t(`lessons.resources.type.${resource.type}`),
    resource.lang ? languageName(resource.lang) : null,
    minutes ? t("lessons.resources.minutes", { minutes }) : null,
    resource.level ? t(`lessons.resources.level.${resource.level}`) : null,
    resource.author ? t("lessons.resources.byAuthor", { author: resource.author }) : null,
    resource.date,
  ].filter((fact): fact is string => fact !== null && fact !== "");
}

/** Une ressource : titre, type, langue, durée, niveau, auteur, date, raison, copie locale et statut. */
export function ResourceItem({ resource, onToggleStatus }: ResourceItemProps) {
  const read = resource.status === "read";
  return (
    <li className="flex flex-col gap-2 rounded-xl border bg-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className={cn("min-w-0 font-semibold break-words", read && "text-muted-foreground")}>
          <ResourceTitle resource={resource} />
        </h3>
        <span
          className={cn(
            "rounded-full border px-2 py-0.5 text-xs font-medium",
            read ? "bg-muted text-muted-foreground" : "border-primary text-primary",
          )}
        >
          {t(`lessons.resources.status.${resource.status}`)}
        </span>
      </div>
      <p className="text-sm text-muted-foreground">{facts(resource).join(" · ")}</p>
      <p className="text-sm">{t("lessons.resources.reason", { reason: resource.reason })}</p>
      <ResourceAttachment resource={resource} />
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="self-start"
        onClick={() => onToggleStatus(resource.id, read ? "to_read" : "read")}
      >
        {t(read ? "lessons.resources.markToRead" : "lessons.resources.markRead", {
          title: resource.title,
        })}
      </Button>
    </li>
  );
}
