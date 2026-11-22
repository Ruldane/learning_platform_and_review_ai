import { useEffect, useId, useRef, type ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface Props {
  phase: "suggested" | "paused" | "review";
  busy?: boolean;
  children?: ReactNode;
  onPause: () => void;
  onReview: () => void;
  onSummary: () => void;
  onContinue: () => void;
}

export function ConcentrationPanel(props: Props) {
  const { phase, busy, children, onPause, onReview, onSummary, onContinue } = props;
  const id = useId();
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (phase !== "suggested") heading.current?.focus();
  }, [phase]);
  const title =
    phase === "paused"
      ? "concentration.paused"
      : phase === "review"
        ? "concentration.review"
        : "concentration.title";
  const options = [
    ["concentration.pause", onPause, "default"],
    ["concentration.review", onReview, "outline"],
    ["concentration.summary", onSummary, "outline"],
    ["concentration.continue", onContinue, "ghost"],
  ] as const;
  return (
    <aside aria-labelledby={id} className="flex flex-col gap-3 rounded-xl border bg-card p-4">
      <h2 id={id} ref={heading} tabIndex={-1} className="font-semibold">
        {t(title)}
      </h2>
      {phase === "suggested" ? (
        <>
          <p role="status" className="text-sm">
            {t("concentration.suggestion")}
          </p>
          <div className="flex flex-wrap gap-2">
            {options.map(([label, action, variant]) => (
              <Button key={label} type="button" onClick={action} variant={variant} disabled={busy}>
                {t(label)}
              </Button>
            ))}
          </div>
        </>
      ) : (
        <>
          {children}
          <Button type="button" className="self-start" onClick={onContinue}>
            {t("concentration.resume")}
          </Button>
        </>
      )}
    </aside>
  );
}
