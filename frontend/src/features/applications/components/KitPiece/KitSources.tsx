import { t } from "@/shared/i18n/t";
import { webUrl } from "@/shared/session-ui";
import type { KitSourceView } from "../viewTypes";

/** Le nom lisible d'une page : son titre, sinon son adresse sans le protocole. */
function nameOf(source: KitSourceView): string {
  if (source.title?.trim()) return source.title.trim();
  return source.url.replace(/^https?:\/\//, "");
}

/**
 * Les pages que le dossier cite, numérotées comme les `[n]` du texte. Un lien s'ouvre dans un nouvel
 * onglet (`noopener noreferrer`) ; une adresse qui n'est pas http ou https reste du texte.
 */
export function KitSources({ sources }: { sources: KitSourceView[] }) {
  if (sources.length === 0) return null;
  return (
    <section aria-label={t("applications.kitPiece.sources")} className="flex flex-col gap-1">
      <h4 className="text-sm font-medium">{t("applications.kitPiece.sources")}</h4>
      <ol className="flex flex-col gap-1 text-sm">
        {[...sources]
          .sort((a, b) => a.rank - b.rank)
          .map((source) => {
            const label = t("applications.kitPiece.sourceItem", {
              rank: source.rank,
              title: nameOf(source),
            });
            const href = webUrl(source.url)?.href;
            return (
              <li key={source.rank} className="break-words">
                {href ? (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary underline underline-offset-4"
                  >
                    {label}
                    <span className="sr-only"> {t("applications.kitPiece.newTab")}</span>
                  </a>
                ) : (
                  label
                )}
              </li>
            );
          })}
      </ol>
    </section>
  );
}
