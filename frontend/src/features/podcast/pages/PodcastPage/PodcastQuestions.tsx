import { t } from "@/shared/i18n/t";
import type { CheckResult, Episode } from "../../api";

interface PodcastQuestionsProps {
  questions: Episode["questions"];
  selected: Record<number, number>;
  onChange: (question: number, choice: number) => void;
  result?: CheckResult;
}

export function PodcastQuestions({ questions, selected, onChange, result }: PodcastQuestionsProps) {
  return (
    <>
      {questions.map((question, index) => {
        const correction = result?.corrections[index];
        return (
          <fieldset key={index} className="flex flex-col gap-2 rounded-lg border p-3">
            <legend className="px-1 font-medium">{question.question}</legend>
            {question.choices.map((choice, rank) => (
              <label key={rank} className="flex items-start gap-2 text-sm">
                <input
                  type="radio"
                  className="mt-1"
                  name={`podcast-question-${index}`}
                  checked={selected[index] === rank}
                  onChange={() => onChange(index, rank)}
                />
                <span>{choice}</span>
              </label>
            ))}
            {correction ? (
              <p className="mt-1 text-sm">
                <strong>{t("podcast.answer")}</strong> {question.choices[correction.answer]}.{" "}
                {correction.explanation}
              </p>
            ) : null}
          </fieldset>
        );
      })}
    </>
  );
}
