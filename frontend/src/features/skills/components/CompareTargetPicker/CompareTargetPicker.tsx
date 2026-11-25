import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { CompareTargetView, PostingChoiceView } from "../viewTypes";

interface CompareTargetPickerProps {
  target: CompareTargetView;
  onTarget: (target: CompareTargetView) => void;
  /** The analyzed offers; empty until they are read. */
  postings: PostingChoiceView[];
  postingId: string | null;
  onPosting: (postingId: string | null) => void;
}

function entryText(posting: PostingChoiceView): string {
  return posting.company
    ? t("skills.compare.postingEntry", { title: posting.title, company: posting.company })
    : posting.title;
}

/**
 * Choose what to compare against: the goal's target role, or « Une offre » (then a dropdown
 * of the analyzed offers). Everything works from the keyboard: arrows between the two choices.
 */
export function CompareTargetPicker(props: CompareTargetPickerProps) {
  const { target, onTarget, postings, postingId, onPosting } = props;
  const name = useId();
  const selectId = useId();
  const option = (value: CompareTargetView, label: string) => (
    <label className="flex items-center gap-2 text-sm">
      <input
        type="radio"
        name={name}
        value={value}
        checked={target === value}
        onChange={() => onTarget(value)}
      />
      {label}
    </label>
  );
  return (
    <div className="flex flex-wrap items-end gap-4">
      <fieldset className="flex flex-wrap items-center gap-4">
        <legend className="mb-1 text-sm font-medium">{t("skills.compare.pickerLabel")}</legend>
        {option("goal", t("skills.compare.pickerGoal"))}
        {option("posting", t("skills.compare.pickerPosting"))}
      </fieldset>
      {target === "posting" && postings.length > 0 ? (
        <div className="flex min-w-60 flex-1 flex-col gap-1">
          <label htmlFor={selectId} className="text-sm font-medium">
            {t("skills.compare.postingLabel")}
          </label>
          <select
            id={selectId}
            value={postingId ?? ""}
            onChange={(event) => onPosting(event.target.value === "" ? null : event.target.value)}
            className={fieldClass}
          >
            <option value="">{t("skills.compare.postingPlaceholder")}</option>
            {postings.map((posting) => (
              <option key={posting.id} value={posting.id}>
                {entryText(posting)}
              </option>
            ))}
          </select>
        </div>
      ) : null}
    </div>
  );
}
