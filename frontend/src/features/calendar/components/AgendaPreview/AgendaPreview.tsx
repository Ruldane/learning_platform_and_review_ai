import type { RefObject } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface Props {
  title: string;
  summary: string;
  period: string;
  complete: boolean;
  heading: RefObject<HTMLHeadingElement | null>;
  pending: boolean;
  onConfirm: () => void;
}

export function AgendaPreview({
  title,
  summary,
  period,
  complete,
  heading,
  pending,
  onConfirm,
}: Props) {
  return (
    <section
      className="space-y-2 rounded border border-border p-4"
      aria-labelledby="agenda-preview"
    >
      <h3 id="agenda-preview" ref={heading} tabIndex={-1} className="font-semibold">
        {summary}
      </h3>
      <p>{title}</p>
      <p>{period}</p>
      <Button
        aria-disabled={pending || complete}
        onClick={() => {
          if (!pending && !complete) onConfirm();
        }}
      >
        {t("calendar.confirm")}
      </Button>
      <p role="status">{complete ? t("calendar.synced") : null}</p>
    </section>
  );
}
