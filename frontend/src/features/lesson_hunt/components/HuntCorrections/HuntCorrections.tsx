import { t } from "@/shared/i18n/t";

interface Props {
  answers: { spotted: boolean; explained: boolean; feedback: string }[];
  corrections: { source: string; replacement: string; explanation: string }[];
}

export function HuntCorrections({ answers, corrections }: Props) {
  return (
    <section className="flex flex-col gap-4 rounded-lg border p-4" aria-labelledby="hunt-bilan">
      <h2 id="hunt-bilan" className="text-lg font-semibold">
        {t("lessonHunt.corrections")}
      </h2>
      <ol className="list-decimal space-y-2 pl-5">
        {answers.map((answer, index) => (
          <li key={index}>
            <p className="font-medium">
              {t(
                answer.explained
                  ? "lessonHunt.explained"
                  : answer.spotted
                    ? "lessonHunt.spotted"
                    : "lessonHunt.missed",
              )}
            </p>
            <p>{answer.feedback}</p>
          </li>
        ))}
      </ol>
      <ul className="space-y-3">
        {corrections.map((edit) => (
          <li key={edit.source} className="rounded-md bg-muted p-3">
            <p className="whitespace-pre-wrap font-medium">{edit.source}</p>
            <p className="mt-1">{edit.explanation}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
