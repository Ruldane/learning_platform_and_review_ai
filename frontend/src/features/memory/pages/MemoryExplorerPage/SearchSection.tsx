import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { SemanticSearch } from "../../components/SemanticSearch";
import { useMemorySearch } from "../../hooks/useMemorySearch";

/** Recherche sémantique : requête, types, résultats avec leurs scores ; un clic ouvre l'élément. */
export function SearchSection({ onOpen }: { onOpen: (itemId: string) => void }) {
  const search = useMemorySearch();
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg font-semibold">{t("memory.page.searchTitle")}</h2>
      <SemanticSearch
        hits={search.data?.hits ?? null}
        pending={search.isPending}
        onSearch={(query, kinds) => search.mutate({ query, kinds })}
        onOpen={onOpen}
      />
      {search.isError ? <InlineError message={errorMessage(search.error)} /> : null}
    </section>
  );
}
