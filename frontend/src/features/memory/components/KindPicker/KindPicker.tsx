import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { MEMORY_KINDS } from "../kindColors";
import type { MemoryKindView } from "../viewTypes";

interface KindPickerProps {
  value: MemoryKindView[];
  onChange: (kinds: MemoryKindView[]) => void;
}

/** Cases à cocher des six types, pour restreindre une recherche (aucune case = tous les types). */
export function KindPicker({ value, onChange }: KindPickerProps) {
  const legendId = useId();
  const toggle = (kind: MemoryKindView) =>
    onChange(value.includes(kind) ? value.filter((k) => k !== kind) : [...value, kind]);
  return (
    <div
      role="group"
      aria-labelledby={legendId}
      className="flex flex-wrap items-center gap-x-4 gap-y-1"
    >
      <span id={legendId} className="text-sm font-medium">
        {t("memory.search.kinds")}
      </span>
      {MEMORY_KINDS.map((kind) => (
        <label key={kind} className="flex items-center gap-1.5 text-sm">
          <input type="checkbox" checked={value.includes(kind)} onChange={() => toggle(kind)} />
          {t(`memory.kind.${kind}`)}
        </label>
      ))}
    </div>
  );
}
