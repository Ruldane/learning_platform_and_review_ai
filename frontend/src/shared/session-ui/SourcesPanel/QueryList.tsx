import { t } from "@/shared/i18n/t";
import type { QueryView } from "../sourceTypes";
import { SourcesBlock } from "./SourcesBlock";

/** Les requêtes lancées : texte, langue, et leur issue (résumé ou « Sans réponse »). */
export function QueryList({ queries }: { queries: QueryView[] }) {
  return (
    <SourcesBlock title={t("session.sources.queries")} count={queries.length}>
      <ul className="flex flex-col gap-1">
        {queries.map((query) => (
          <li key={query.id} className="flex flex-wrap items-baseline gap-x-2 text-sm">
            <span className="break-words">{query.text}</span>
            {query.lang ? (
              <span className="text-xs text-muted-foreground uppercase">{query.lang}</span>
            ) : null}
            {query.ok === false ? (
              <span className="text-xs text-destructive">{t("session.sources.queryFailed")}</span>
            ) : null}
            {query.summary ? (
              <span className="text-xs text-muted-foreground">{query.summary}</span>
            ) : null}
          </li>
        ))}
      </ul>
    </SourcesBlock>
  );
}
