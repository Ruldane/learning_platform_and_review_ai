import { t } from "@/shared/i18n/t";
import { SearchHitList } from "../SearchHitList";
import type { SearchHitView } from "../viewTypes";

interface BenchResultProps {
  hits: SearchHitView[];
  agentText: string;
}

/** Fragments retenus (avec scores), puis le texte exact remis à l'agent, tel quel. */
export function BenchResult({ hits, agentText }: BenchResultProps) {
  return (
    <>
      <SearchHitList hits={hits} />
      <section className="flex flex-col gap-1">
        <h3 className="text-sm font-semibold">{t("memory.bench.agentText")}</h3>
        <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg border border-border bg-muted p-3 text-xs">
          {agentText}
        </pre>
      </section>
    </>
  );
}
