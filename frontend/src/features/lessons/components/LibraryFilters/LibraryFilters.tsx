import { t, type MessageKey } from "@/shared/i18n/t";
import { FilterSelect } from "./FilterSelect";
import type { LibraryFilterValue, ProgramOption, ResourceStatus, ResourceType } from "../viewTypes";

interface LibraryFiltersProps {
  value: LibraryFilterValue;
  programs: ProgramOption[];
  onChange: (value: LibraryFilterValue) => void;
}

const TYPES: ResourceType[] = ["documentation", "cours", "video", "article", "depot", "papier"];
const LANGS = ["fr", "en", "es", "de"] as const;
const STATUSES: ResourceStatus[] = ["to_read", "read"];

const labelled = (values: readonly string[], key: (value: string) => MessageKey) =>
  values.map((value) => ({ value, label: t(key(value)) }));

/** Les filtres de la bibliothèque : programme, type, langue et statut de lecture. */
export function LibraryFilters({ value, programs, onChange }: LibraryFiltersProps) {
  return (
    <div role="group" aria-label={t("lessons.filters.label")} className="flex flex-wrap gap-3">
      <FilterSelect
        label={t("lessons.filters.program")}
        value={value.programId}
        allLabel={t("lessons.filters.all")}
        options={programs.map((program) => ({ value: program.id, label: program.title }))}
        onChange={(programId) => onChange({ ...value, programId })}
      />
      <FilterSelect
        label={t("lessons.filters.type")}
        value={value.type}
        allLabel={t("lessons.filters.all")}
        options={labelled(TYPES, (type) => `lessons.resources.type.${type}` as MessageKey)}
        onChange={(type) => onChange({ ...value, type: type as ResourceType | null })}
      />
      <FilterSelect
        label={t("lessons.filters.lang")}
        value={value.lang}
        allLabel={t("lessons.filters.allFeminine")}
        options={labelled(LANGS, (lang) => `lessons.filters.lang_${lang}` as MessageKey)}
        onChange={(lang) => onChange({ ...value, lang })}
      />
      <FilterSelect
        label={t("lessons.filters.status")}
        value={value.status}
        allLabel={t("lessons.filters.all")}
        options={labelled(STATUSES, (status) => `lessons.resources.status.${status}` as MessageKey)}
        onChange={(status) => onChange({ ...value, status: status as ResourceStatus | null })}
      />
    </div>
  );
}
