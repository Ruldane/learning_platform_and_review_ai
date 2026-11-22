import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface IncidentReportProps {
  report: string;
  ready: boolean;
  disabled: boolean;
  verified: boolean;
  reviewMessage: string | null;
  onReport: (text: string) => void;
}

export function IncidentReport({
  report,
  ready,
  disabled,
  verified,
  reviewMessage,
  onReport,
}: IncidentReportProps) {
  const [draft, setDraft] = useState<string | null>(null);
  const text = verified ? report : (draft ?? report);
  const canSend = ready && !disabled && !verified && text.trim().length >= 8;
  return (
    <form
      className="flex flex-col items-start gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (canSend) onReport(text.trim());
      }}
    >
      <label className="text-xl font-semibold" htmlFor="incident-report">
        {t("oncall.report")}
      </label>
      <p id="incident-report-help" className="text-sm">
        {t("oncall.reportHelp")}
      </p>
      <textarea
        id="incident-report"
        aria-describedby="incident-report-help"
        className="w-full rounded-md border border-[var(--border)] bg-card p-3"
        value={text}
        onChange={(event) => setDraft(event.target.value)}
        maxLength={6000}
        rows={6}
        readOnly={verified || disabled}
      />
      <Button type="submit" aria-disabled={!canSend}>
        {t("oncall.send")}
      </Button>
      {!ready && !verified && <p className="text-sm">{t("oncall.reportWaiting")}</p>}
      {reviewMessage && <p role="status">{reviewMessage}</p>}
    </form>
  );
}
