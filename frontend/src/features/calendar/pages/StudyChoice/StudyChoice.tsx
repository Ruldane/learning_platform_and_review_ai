import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ChoiceField } from "../../components/ChoiceField";
import type { ChoiceProps } from "../../forms";
import { useStudyChoices } from "./useStudyChoices";

export function StudyChoice({ initial, pending, onChange, onSelect }: ChoiceProps) {
  const choices = useStudyChoices(initial);
  const valid = choices.selected && choices.tasks.some((row) => row.id === choices.task);
  return (
    <form
      className="flex flex-col items-start gap-3"
      onChange={onChange}
      onSubmit={(event) => {
        event.preventDefault();
        if (valid && !pending)
          onSelect({ kind: "study", program_id: choices.selected, source_id: choices.task });
      }}
    >
      {choices.pending ? <LoadingState label={t("calendar.loading")} /> : null}
      {choices.error ? <p role="alert">{errorMessage(choices.error)}</p> : null}
      <ChoiceField
        label={t("calendar.program")}
        value={choices.selected}
        disabled={pending}
        options={choices.programs}
        onChange={choices.setProgram}
        placeholder
      />
      {choices.selected ? (
        <ChoiceField
          label={t("calendar.block")}
          value={choices.task}
          disabled={pending}
          options={choices.tasks}
          onChange={choices.setTask}
          placeholder
        />
      ) : null}
      <Button type="submit" disabled={pending || !valid}>
        {t("calendar.preview")}
      </Button>
    </form>
  );
}
