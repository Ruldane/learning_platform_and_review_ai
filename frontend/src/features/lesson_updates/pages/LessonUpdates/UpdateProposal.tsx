import { useEffect, useId, useRef } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { UpdateView } from "../../api";

interface ProposalProps {
  item: UpdateView;
  busy: boolean;
  onAccept: () => void;
}

export function UpdateProposal({ item, busy, onAccept }: ProposalProps) {
  const heading = useId();
  const status = useRef<HTMLParagraphElement>(null);
  const previous = useRef(item.state);
  const ready = item.state === "ready" || item.state === "failed";
  const action = item.state === "ready" ? "accept" : item.changes.length ? "retryCheck" : "retryDraft";
  useEffect(() => {
    if (["failed", "ready"].includes(previous.current) && !ready) status.current?.focus();
    previous.current = item.state;
  }, [item.state, ready]);
  return (
    <article aria-labelledby={heading} className="grid gap-3 rounded-xl border bg-card p-4">
      <h3 id={heading} className="font-semibold">
        {t("lessonUpdates.release", { name: item.library, version: item.version })}
      </h3>
      <p ref={status} role="status" tabIndex={-1}>
        {t(`lessonUpdates.state.${item.state}`)}
      </p>
      <p className="break-words">{item.apis.join(", ")}</p>
      <a
        href={item.source_url}
        target="_blank"
        rel="noreferrer"
        className="justify-self-start underline"
      >
        {t("lessonUpdates.source")}
      </a>
      {item.explanation && <p className="whitespace-pre-wrap break-words">{item.explanation}</p>}
      {item.changes.map(({ block, before, after }) => (
        <details className="rounded-md border p-2" key={block}>
          <summary className="cursor-pointer">{t("lessonUpdates.compare", { block })}</summary>
          <p className="mt-2 text-sm font-semibold">{t("lessonUpdates.before")}</p>
          <pre className="overflow-x-auto whitespace-pre-wrap break-words text-xs">{before}</pre>
          <p className="mt-2 text-sm font-semibold">{t("lessonUpdates.after")}</p>
          <pre className="overflow-x-auto whitespace-pre-wrap break-words text-xs">{after}</pre>
        </details>
      ))}
      {ready && (
        <Button type="button" className="justify-self-start" disabled={busy} onClick={onAccept}>
          {t(`lessonUpdates.${action}`)}
        </Button>
      )}
    </article>
  );
}
