import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LibraryFilters } from "../../components/LibraryFilters";
import { useResourceStatus } from "../../hooks/useResourceStatus";
import { usePrograms } from "../../hooks/usePrograms";
import type { LibraryFilterValue } from "../../types";
import { LibraryResults } from "./LibraryResults";

const NO_FILTER: LibraryFilterValue = { programId: null, type: null, lang: null, status: null };

/**
 * Library (`/learn/library`): all the resources of the programs, filterable by
 * program, type, language and reading status (to read, read).
 */
export function LibraryPage() {
  const [filters, setFilters] = useState<LibraryFilterValue>(NO_FILTER);
  const programs = usePrograms();
  const resourceStatus = useResourceStatus();
  const options = (programs.data ?? []).map(({ id, title }) => ({ id, title }));
  const filtered = Object.values(filters).some((value) => value !== null);
  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold">{t("lessons.library.title")}</h1>
        <p className="mt-2 text-muted-foreground">{t("lessons.library.intro")}</p>
      </header>
      <LibraryFilters value={filters} programs={options} onChange={setFilters} />
      {resourceStatus.error ? <InlineError message={resourceStatus.error} /> : null}
      <LibraryResults
        filters={filters}
        filtered={filtered}
        latestProgramId={programs.data?.[0]?.id ?? null}
        onClearFilters={() => setFilters(NO_FILTER)}
        onToggleStatus={resourceStatus.setStatus}
      />
    </div>
  );
}
