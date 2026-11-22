import { t } from "@/shared/i18n/t";
import { ChatMarkdown } from "@/shared/ui/ChatMarkdown";

export const formats = ["review", "guided", "source"] as const;
export type Format = (typeof formats)[number];

type Edition = {
  lesson_title: string;
  revision: string;
  source_markdown: string;
  review_markdown: string;
  reading_steps: string[];
};

export function VariantReading({ edition, format, onFormat }: {
  edition: Edition;
  format: Format;
  onFormat: (value: Format) => void;
}) {
  const markdown = format === "review" ? edition.review_markdown : edition.source_markdown;
  return (
    <section className="flex flex-col gap-3 rounded border p-4">
      <h2 id="variant-reading" tabIndex={-1} className="text-lg font-semibold">
        {edition.lesson_title}
      </h2>
      <p className="break-all text-sm text-muted-foreground">
        {t("lessonVariants.revision")} <code>{edition.revision}</code>
      </p>
      <label className="grid max-w-xs gap-1">
        {t("lessonVariants.chooseFormat")}
        <select value={format} className="rounded border bg-background p-2"
          onChange={(event) => {
            const selected = formats.find((value) => value === event.target.value);
            if (selected) onFormat(selected);
          }}>
          {formats.map((value) => <option key={value} value={value}>{t(`lessonVariants.${value}`)}</option>)}
        </select>
      </label>
      {format === "guided" && edition.reading_steps.length > 0 && (
        <div className="rounded bg-muted p-3">
          <h3 className="font-semibold">{t("lessonVariants.readingSteps")}</h3>
          <ol className="list-decimal pl-5">
            {edition.reading_steps.map((step, index) => <li key={index}>{step}</li>)}
          </ol>
        </div>
      )}
      <ChatMarkdown>{markdown}</ChatMarkdown>
    </section>
  );
}
