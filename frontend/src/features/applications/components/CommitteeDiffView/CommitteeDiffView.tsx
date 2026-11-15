import { t } from "@/shared/i18n/t";
import type { CommitteeDiffView as DiffView } from "../viewTypes";
import { TextList } from "./TextList";
import { VoteDiffTable } from "./VoteDiffTable";

interface CommitteeDiffViewProps {
  /** `null` : première exécution de l'offre. */
  diff: DiffView | null;
}

/** L'avant et l'après : les votes persona par persona, les objections levées et les nouvelles. */
export function CommitteeDiffView({ diff }: CommitteeDiffViewProps) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold">{t("applications.diffView.title")}</h2>
      {diff === null ? (
        <p>{t("applications.diffView.first")}</p>
      ) : (
        <>
          <VoteDiffTable votes={diff.votes} />
          <TextList
            title={t("applications.diffView.resolvedTitle")}
            items={diff.resolved}
            empty={t("applications.diffView.resolvedEmpty")}
          />
          <TextList
            title={t("applications.diffView.addedTitle")}
            items={diff.added}
            empty={t("applications.diffView.addedEmpty")}
          />
        </>
      )}
    </section>
  );
}
