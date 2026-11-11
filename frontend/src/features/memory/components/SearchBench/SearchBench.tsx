import { useId, useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import { KindPicker } from "../KindPicker";
import { BenchResult } from "./BenchResult";
import type { MemoryKindView, SearchHitView } from "../viewTypes";

/** Nombre de résultats par défaut d'`memory_search` (SPEC 4.4) et bornes acceptées. */
const DEFAULT_K = 8;
const MIN_K = 1;
const MAX_K = 50;

function parseK(raw: string): number {
  const value = Number.parseInt(raw, 10);
  if (Number.isNaN(value)) return DEFAULT_K;
  return Math.min(MAX_K, Math.max(MIN_K, value));
}

interface SearchBenchProps {
  result: { hits: SearchHitView[]; agentText: string } | null;
  pending: boolean;
  onRun: (query: string, kinds: MemoryKindView[], k: number) => void;
}

/** Banc d'essai : ce qu'un agent recevrait pour une requête, texte exact et fragments avec scores. */
export function SearchBench({ result, pending, onRun }: SearchBenchProps) {
  const kId = useId();
  const [query, setQuery] = useState("");
  const [kinds, setKinds] = useState<MemoryKindView[]>([]);
  const [k, setK] = useState(String(DEFAULT_K));
  const trimmed = query.trim();
  const canRun = !pending && trimmed !== "";

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!canRun) return;
    const count = parseK(k);
    setK(String(count));
    onRun(trimmed, kinds, count);
  };

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">{t("memory.bench.intro")}</p>
      <form onSubmit={submit} noValidate className="flex flex-col gap-3">
        <label className="flex flex-col gap-1 text-sm font-medium">
          {t("memory.search.query")}
          <input
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className={fieldClass}
          />
        </label>
        <KindPicker value={kinds} onChange={setKinds} />
        <label htmlFor={kId} className="text-sm font-medium">
          {t("memory.bench.k")}
        </label>
        <input
          id={kId}
          type="number"
          min={MIN_K}
          max={MAX_K}
          value={k}
          onChange={(event) => setK(event.target.value)}
          className={`${fieldClass} w-24`}
        />
        <Button type="submit" disabled={!canRun} className="self-start">
          {pending ? t("memory.bench.running") : t("memory.bench.run")}
        </Button>
      </form>
      {result ? <BenchResult hits={result.hits} agentText={result.agentText} /> : null}
    </div>
  );
}
