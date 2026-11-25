import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { PostingChoice } from "../../hooks/usePostingChoices";

interface PostingSelectProps {
  id: string;
  value: string;
  postings: PostingChoice[];
  disabled: boolean;
  onChange: (postingId: string) => void;
}

/** The list of analysed postings, for an interview without a record. */
export function PostingSelect({ id, value, postings, disabled, onChange }: PostingSelectProps) {
  return (
    <label htmlFor={id} className="flex flex-col gap-1 text-sm font-medium">
      {t("applications.interviewSetup.target.postingLabel")}
      <select
        id={id}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className={fieldClass}
      >
        <option value="">{t("applications.interviewSetup.target.postingPlaceholder")}</option>
        {postings.map((posting) => (
          <option key={posting.id} value={posting.id}>
            {posting.label}
          </option>
        ))}
      </select>
    </label>
  );
}
