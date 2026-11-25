import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { OptionGroup } from "../../components/OptionGroup";
import type { PostingChoice } from "../../hooks/usePostingChoices";
import { PostingSelect } from "./PostingSelect";
import { RoleInput } from "./RoleInput";
import { kindOf, type TargetDraft, type TargetKind } from "./targetDraft";

interface TargetFieldsProps {
  draft: TargetDraft;
  postings: PostingChoice[];
  disabled: boolean;
  onChange: (draft: TargetDraft) => void;
}

/** Interview without a record: an analysed posting to choose, or a job title to enter. */
export function TargetFields({ draft, postings, disabled, onChange }: TargetFieldsProps) {
  const id = useId();
  const kind = kindOf(draft, postings.length > 0);
  return (
    <div className="flex flex-col gap-3">
      {postings.length > 0 ? (
        <OptionGroup
          legend={t("applications.interviewSetup.target.legend")}
          name="target"
          value={kind}
          disabled={disabled}
          options={[
            { value: "posting", label: t("applications.interviewSetup.target.posting") },
            { value: "role", label: t("applications.interviewSetup.target.role") },
          ]}
          onChange={(value) => onChange({ ...draft, kind: value as TargetKind })}
        />
      ) : (
        <p className="text-sm text-muted-foreground">
          {t("applications.interviewSetup.target.noPostings")}
        </p>
      )}
      {kind === "posting" ? (
        <PostingSelect
          id={`${id}-posting`}
          value={draft.postingId}
          postings={postings}
          disabled={disabled}
          onChange={(postingId) => onChange({ ...draft, postingId })}
        />
      ) : (
        <RoleInput
          id={`${id}-role`}
          value={draft.role}
          disabled={disabled}
          onChange={(role) => onChange({ ...draft, role })}
        />
      )}
    </div>
  );
}
