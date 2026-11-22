import { useRef, useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { ReturnState } from "../../api";
import { formatDate } from "../../dates";
import { ReminderFields } from "../ReminderFields";
import { useReminder } from "./useReminder";

export function ReturnReminder({ state }: { state: ReturnState }) {
  const heading = useRef<HTMLHeadingElement>(null);
  const [draft, setDraft] = useState<string | null>(null);
  const day = draft ?? state.reminder_on ?? "";
  const save = useReminder(() => setDraft(null));
  const remove = () => {
    heading.current?.focus();
    save.mutate(null);
  };
  return (
    <section className="flex flex-col gap-2">
      <h2 ref={heading} tabIndex={-1} className="font-semibold">
        {t("studyReturn.reminder")}
      </h2>
      {state.reminder_due ? (
        <p role="status">{t("studyReturn.due")}</p>
      ) : (
        state.reminder_on && (
          <p role="status">{t("studyReturn.scheduled", { date: formatDate(state.reminder_on) })}</p>
        )
      )}
      <ReminderFields
        day={day}
        hasReminder={!!state.reminder_on}
        saving={save.isPending}
        onChange={setDraft}
        onSave={() => save.mutate(day)}
        onRemove={remove}
      />
      {save.isError && <p role="alert">{errorMessage(save.error)}</p>}
    </section>
  );
}
