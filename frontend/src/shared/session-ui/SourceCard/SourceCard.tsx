import { t } from "@/shared/i18n/t";
import type { SourceView } from "../sourceTypes";
import { webUrl } from "../webUrl";

const DAY = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long", timeZone: "UTC" });
const ISO_DAY = /^\d{4}-\d{2}-\d{2}/;

/** Date ISO → « 4 mars 2026 » ; tout autre texte est rendu tel quel. */
function formatDate(value: string): string {
  if (!ISO_DAY.test(value)) return value;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : DAY.format(date);
}

/**
 * Une page lue par l'Éclaireur : titre (lien vers la page, sauf si elle est illisible), note,
 * auteur, date, langue, et la raison quand la page est écartée ou illisible. Une page illisible
 * n'est jamais un lien : aucun texte n'en a été lu, elle ne peut pas être citée.
 */
export function SourceCard({ source }: { source: SourceView }) {
  const unreadable = source.status === "unreadable";
  const address = webUrl(source.url);
  const showReason = (unreadable || source.verdict === "rejected") && source.reason;
  return (
    <article className="flex flex-col gap-1 rounded-lg border border-border bg-card px-3 py-2 text-sm">
      <h4 className="font-medium break-words">
        {address && !unreadable ? (
          <a
            href={address.href}
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2 hover:text-primary"
          >
            {source.title}
          </a>
        ) : (
          source.title
        )}
      </h4>
      {address ? (
        <p className="text-xs break-all text-muted-foreground">{address.hostname}</p>
      ) : null}
      <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
        {source.score !== null ? (
          <span className="font-medium text-foreground" title={t("session.sources.scoreTitle")}>
            {t("session.sources.score", { score: Math.round(source.score) })}
          </span>
        ) : null}
        {source.author ? <span title={t("session.sources.author")}>{source.author}</span> : null}
        {source.date ? (
          <span title={t("session.sources.date")}>{formatDate(source.date)}</span>
        ) : null}
        {source.lang ? (
          <span className="uppercase" title={t("session.sources.lang")}>
            {source.lang}
          </span>
        ) : null}
      </p>
      {showReason ? <p>{source.reason}</p> : null}
    </article>
  );
}
