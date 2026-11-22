import { t } from "@/shared/i18n/t";
import type { ReadFilter, ReadingKind } from "../../api";

const kinds = ["offer", "article", "paper", "release"] as const;
const states = ["unread", "read", "all"] as const;

interface ReadingFiltersProps {
  state: ReadFilter;
  kind: ReadingKind | "";
  onState: (state: ReadFilter) => void;
  onKind: (kind: ReadingKind | "") => void;
}

export function ReadingFilters({ state, kind, onState, onKind }: ReadingFiltersProps) {
  return (
    <div className="flex flex-wrap gap-3">
      <label className="flex flex-col gap-1 text-sm">
        {t("reading.state")}
        <select
          className="rounded-md border bg-background p-2"
          value={state}
          onChange={(event) =>
            onState(states.find((value) => value === event.target.value) ?? "all")
          }
        >
          {states.map((value) => (
            <option key={value} value={value}>
              {t(`reading.${value}`)}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm">
        {t("reading.kinds")}
        <select
          className="rounded-md border bg-background p-2"
          value={kind}
          onChange={(event) => onKind(kinds.find((value) => value === event.target.value) ?? "")}
        >
          <option value="">{t("reading.allKinds")}</option>
          {kinds.map((value) => (
            <option key={value} value={value}>
              {t(`reading.kind.${value}`)}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
