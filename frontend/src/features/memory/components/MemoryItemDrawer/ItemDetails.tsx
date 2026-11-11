import { t } from "@/shared/i18n/t";
import { authorLabel } from "../authorLabel";
import { formatDayTime } from "../formatDate";
import { KindBadge } from "../KindBadge";
import type { MemoryItemDetailView } from "../viewTypes";

const headingClass = "text-sm font-semibold";

/** Métadonnées, texte, étiquettes et preuves d'un élément. */
export function ItemDetails({ item }: { item: MemoryItemDetailView }) {
  return (
    <>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
        <KindBadge kind={item.kind} />
        {item.status === "pending" ? <span>{t("memory.pendingBadge")}</span> : null}
        {item.level ? <span>{t(`memory.level.${item.level}`)}</span> : null}
        <span>{authorLabel(item.created_by)}</span>
        <span className="text-muted-foreground">{formatDayTime(item.created_at)}</span>
        {item.indexed ? null : (
          <span className="text-muted-foreground">{t("memory.notIndexed")}</span>
        )}
      </div>
      <section className="flex flex-col gap-1">
        <h3 className={headingClass}>{t("memory.drawer.text")}</h3>
        <p className="whitespace-pre-wrap">{item.text}</p>
      </section>
      <section className="flex flex-col gap-1">
        <h3 className={headingClass}>{t("memory.drawer.tags")}</h3>
        {item.tags.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("memory.drawer.noTags")}</p>
        ) : (
          <ul className="flex flex-wrap gap-2 text-sm">
            {item.tags.map((tag) => (
              <li key={tag} className="rounded-md bg-muted px-2 py-0.5">
                {tag}
              </li>
            ))}
          </ul>
        )}
      </section>
      {item.evidence.length === 0 ? null : (
        <section className="flex flex-col gap-1">
          <h3 className={headingClass}>{t("memory.drawer.evidence")}</h3>
          <ul className="list-disc pl-5 text-sm">
            {item.evidence.map((proof) => (
              <li key={proof} className="break-words">
                {proof}
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
