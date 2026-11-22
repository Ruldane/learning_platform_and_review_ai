import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { acceptExplanation, type Explanation } from "../../feynmanApi";
import { ExplanationTranscript } from "./ExplanationTranscript";

export function ExplanationReport({ row, onSaved }: { row: Explanation; onSaved: () => void }) {
  const savedStatus = useRef<HTMLParagraphElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const save = useMutation({ mutationFn: () => acceptExplanation(row.id), onSuccess: onSaved });
  useEffect(() => heading.current?.focus(), []);
  const saved = save.data ?? row.report?.saved;
  useEffect(() => {
    if (save.data) savedStatus.current?.focus();
  }, [save.data]);
  const report = row.report;
  if (!report) return null;
  const offers = report.cards.length > 0 || report.proof_skill !== null;
  return (
    <section className="flex flex-col gap-3 rounded-lg border border-border p-4">
      <h2 ref={heading} tabIndex={-1} className="text-xl font-semibold">
        {t("feynman.report")}
      </h2>
      <p className="whitespace-pre-wrap">{report.summary}</p>
      <ExplanationTranscript report={report} />
      {report.cards.length > 0 && (
        <ul aria-label={t("feynman.cards")} className="flex flex-col gap-2">
          {report.cards.map((card, index) => (
            <li key={`${index}:${card.front}`}>
              <strong>{card.front}</strong> · {card.back}
            </li>
          ))}
        </ul>
      )}
      {report.proof_skill && <p>{t("feynman.proof", { skill: report.proof_skill })}</p>}
      {offers && !saved && (
        <Button
          type="button"
          className="self-start"
          disabled={save.isPending}
          onClick={() => save.mutate()}
        >
          {t("feynman.save")}
        </Button>
      )}
      {save.error && <InlineError message={errorMessage(save.error)} />}
      {saved && (
        <p ref={savedStatus} tabIndex={-1} role="status">
          {t("feynman.saved")}
        </p>
      )}
    </section>
  );
}
