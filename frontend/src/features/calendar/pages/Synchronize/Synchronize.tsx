import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { AgendaPreview } from "../../components/AgendaPreview";
import { ChoiceField } from "../../components/ChoiceField";
import type { Selection } from "../../api";
import { InterviewChoice } from "../InterviewChoice";
import { StudyChoice } from "../StudyChoice";
import { formatPeriod } from "./formatPeriod";
import { usePreview } from "./usePreview";

interface Props {
  initialProgram: string;
  initialApplication: string;
}

export function Synchronize({ initialProgram, initialApplication }: Props) {
  const [kind, setKind] = useState<Selection["kind"]>(initialApplication ? "interview" : "study");
  const { preview, heading, pending, error, reset, propose, confirm } = usePreview();
  const choiceProps = { pending, onChange: reset, onSelect: propose };
  return (
    <section className="flex flex-col gap-4" aria-labelledby="agenda-selection">
      <h2 id="agenda-selection" className="text-xl font-semibold">
        {t("calendar.choose")}
      </h2>
      <ChoiceField
        label={t("calendar.category")}
        value={kind}
        disabled={pending}
        options={[
          { id: "study", label: t("calendar.study") },
          { id: "interview", label: t("calendar.interview") },
        ]}
        onChange={(value) => {
          setKind(value === "interview" ? "interview" : "study");
          reset();
        }}
      />
      {kind === "study" ? (
        <StudyChoice initial={initialProgram} {...choiceProps} />
      ) : (
        <InterviewChoice initial={initialApplication} {...choiceProps} />
      )}
      {error ? <p role="alert">{errorMessage(error)}</p> : null}
      {preview ? (
        <AgendaPreview
          title={preview.title}
          summary={t(`calendar.actions.${preview.action}`)}
          period={formatPeriod(preview)}
          complete={preview.status === "synced"}
          heading={heading}
          pending={pending}
          onConfirm={() => confirm(preview.id)}
        />
      ) : null}
    </section>
  );
}
