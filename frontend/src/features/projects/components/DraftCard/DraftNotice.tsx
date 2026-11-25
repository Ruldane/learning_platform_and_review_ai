import { t } from "@/shared/i18n/t";
import type { DraftView } from "../viewTypes";

/**
 * Warning on a draft to check. The terms come from the server as is (« 10000 »,
 * « Kubernetes »), joined by « , »: the text invents or rephrases nothing.
 */
export function DraftNotice({ draft }: { draft: DraftView }) {
  if (draft.status !== "to_check") return null;
  return (
    <p role="note" className="rounded-lg border border-amber-500/60 bg-amber-500/10 p-2 text-sm">
      {draft.flags.length > 0
        ? t("projects.draft.toCheck", { flags: draft.flags.join(", ") })
        : t("projects.draft.toCheckNoFlag")}
    </p>
  );
}
