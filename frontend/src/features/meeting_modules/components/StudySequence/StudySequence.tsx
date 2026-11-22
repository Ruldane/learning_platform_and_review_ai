import { t } from "@/shared/i18n/t";

interface Step {
  source_line: number;
  instruction: string;
  criterion: string;
  minutes: number;
}

interface Props {
  steps: readonly Step[];
  excerpts: readonly { line: number; text: string }[];
}

export function StudySequence({ steps, excerpts }: Props) {
  if (!steps.length) return null;
  const sources = new Map(excerpts.map((item) => [item.line, item.text]));
  return (
    <section className="grid gap-3">
      <h2 className="font-semibold">{t("meetingModules.steps")}</h2>
      <ol className="grid gap-3">
        {steps.map((item) => (
          <li key={item.source_line} className="grid gap-2 rounded border p-3">
            <span className="text-sm">
              {t("meetingModules.line", { line: item.source_line })} ·{" "}
              {t("meetingModules.duration", { minutes: item.minutes })}
            </span>
            <blockquote className="break-words font-medium">
              {sources.get(item.source_line)}
            </blockquote>
            <p>{item.instruction}</p>
            <div>
              <p className="text-sm font-medium">{t("meetingModules.check")}</p>
              <p>{item.criterion}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
