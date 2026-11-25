import { t } from "@/shared/i18n/t";
import { webUrl } from "@/shared/session-ui";
import type { KitSourceView } from "../viewTypes";

/** The readable name of a page: its title, otherwise its address without the protocol. */
function nameOf(source: KitSourceView): string {
  if (source.title?.trim()) return source.title.trim();
  return source.url.replace(/^https?:\/\//, "");
}

/**
 * The pages the file cites, numbered like the `[n]` in the text. A link opens in a new
 * tab (`noopener noreferrer`); an address that is not http or https stays as text.
 */
export function KitSources({ sources }: { sources: KitSourceView[] }) {
  if (sources.length === 0) return null;
  return (
    <section aria-label={t("applications.kitPiece.sources")} className="flex flex-col gap-1">
      <h3 className="text-sm font-medium">{t("applications.kitPiece.sources")}</h3>
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
