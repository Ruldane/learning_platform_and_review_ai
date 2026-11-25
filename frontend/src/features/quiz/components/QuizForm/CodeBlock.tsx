import { t } from "@/shared/i18n/t";

/** A question's code, shown as is in a keyboard-scrollable block (never interpreted). */
export function CodeBlock({ rank, code }: { rank: number; code: string }) {
  return (
    <pre
      role="region"
      tabIndex={0}
      aria-label={t("quiz.form.codeLabel", { rank })}
      className="mt-2 overflow-x-auto rounded-lg bg-muted p-3 font-mono text-sm"
    >
      <code>{code}</code>
    </pre>
  );
}
