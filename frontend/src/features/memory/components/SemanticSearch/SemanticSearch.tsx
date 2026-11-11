import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import { KindPicker } from "../KindPicker";
import { SearchHitList } from "../SearchHitList";
import type { MemoryKindView, SearchHitView } from "../viewTypes";

interface SemanticSearchProps {
  /** `null` : aucune recherche lancée pour l'instant. */
  hits: SearchHitView[] | null;
  pending: boolean;
  onSearch: (query: string, kinds: MemoryKindView[]) => void;
  onOpen: (itemId: string) => void;
}

/** Recherche sémantique : requête, types facultatifs, résultats avec leurs scores. */
export function SemanticSearch({ hits, pending, onSearch, onOpen }: SemanticSearchProps) {
  const [query, setQuery] = useState("");
  const [kinds, setKinds] = useState<MemoryKindView[]>([]);
  const trimmed = query.trim();
  const canSearch = !pending && trimmed !== "";

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (canSearch) onSearch(trimmed, kinds);
  };

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={submit} className="flex flex-col gap-3">
        <label className="flex flex-col gap-1 text-sm font-medium">
          {t("memory.search.query")}
          <input
            type="search"
            value={query}
            placeholder={t("memory.search.placeholder")}
            onChange={(event) => setQuery(event.target.value)}
            className={fieldClass}
          />
        </label>
        <KindPicker value={kinds} onChange={setKinds} />
        <Button type="submit" disabled={!canSearch} className="self-start">
          {pending ? t("memory.search.searching") : t("memory.search.submit")}
        </Button>
      </form>
      {hits === null ? null : <SearchHitList hits={hits} onOpen={onOpen} />}
    </div>
  );
}
