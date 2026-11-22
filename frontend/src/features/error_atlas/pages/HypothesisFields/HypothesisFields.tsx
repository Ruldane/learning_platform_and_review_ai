import { t } from "@/shared/i18n/t";
import type { ObservationInput } from "../../api";
import { confidenceLabels } from "../../labels";

export type HypothesisDraft = { label: string; confidence: ObservationInput["confidence"] };
const levels = ["low", "medium", "high"] as const;

export function HypothesisFields({
  draft,
  onChange,
}: {
  draft: HypothesisDraft;
  onChange: (next: HypothesisDraft) => void;
}) {
  return (
    <>
      <label className="flex flex-col gap-1">
        {t("errorAtlas.prerequisite")}
        <input
          type="text"
          required
          maxLength={120}
          minLength={2}
          className="rounded border border-border bg-background p-2"
          value={draft.label}
          onChange={(event) => onChange({ ...draft, label: event.target.value })}
        />
      </label>
      <label className="flex flex-col gap-1">
        {t("errorAtlas.confidence")}
        <select
          className="rounded border border-border bg-background p-2"
          value={draft.confidence}
          onChange={(event) => {
            const confidence = levels.find((level) => level === event.target.value);
            if (confidence) onChange({ ...draft, confidence });
          }}
        >
          {levels.map((level) => (
            <option key={level} value={level}>
              {t(confidenceLabels[level])}
            </option>
          ))}
        </select>
      </label>
    </>
  );
}
