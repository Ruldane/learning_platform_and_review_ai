import { t } from "@/shared/i18n/t";
import type { MemoryItemDetailView } from "../viewTypes";

/** Fragments indexés d'un élément (rien à afficher tant qu'il n'est pas indexé). */
export function ChunkList({ chunks }: { chunks: MemoryItemDetailView["chunks"] }) {
  if (chunks.length === 0) return null;
  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold">{t("memory.drawer.chunks")}</h3>
      <ol className="flex flex-col gap-2">
        {chunks.map((chunk) => (
          <li key={chunk.id} className="rounded-lg border border-border px-3 py-2 text-sm">
            <p className="text-xs text-muted-foreground">
              {t("memory.drawer.chunk", { n: chunk.ordinal + 1, tokens: chunk.token_count })}
            </p>
            <p className="whitespace-pre-wrap">{chunk.text}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
