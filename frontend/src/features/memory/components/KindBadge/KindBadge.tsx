import { t } from "@/shared/i18n/t";
import { KIND_COLORS } from "../kindColors";
import type { MemoryKindView } from "../viewTypes";

/** Type badge: a coloured dot and the type name, written out, never colour alone. */
export function KindBadge({ kind }: { kind: MemoryKindView }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 text-sm font-medium"
      style={{ color: KIND_COLORS[kind] }}
    >
      <span
        aria-hidden="true"
        className="size-2.5 rounded-full"
        style={{ backgroundColor: KIND_COLORS[kind] }}
      />
      {t(`memory.kind.${kind}`)}
    </span>
  );
}
