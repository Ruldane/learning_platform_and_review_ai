import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { ChatMarkdown } from "@/shared/ui/ChatMarkdown";

export function HandoffPreview({ guide, busy, onApprove, onExport }: {
  guide: { digest: string; markdown: string };
  busy: boolean;
  onApprove?: () => void;
  onExport?: () => void;
}) {
  return (
    <section className="grid gap-3 rounded border p-4">
      <h2 id="handoff-preview" tabIndex={-1} className="text-lg font-semibold">
        {t(onApprove ? "projectHandoffs.previewTitle" : "projectHandoffs.approved")}
      </h2>
      <p className="break-all text-sm text-muted-foreground">
        {t("projectHandoffs.revision")} <code>{guide.digest}</code>
      </p>
      <ChatMarkdown allowLinks={false}>{guide.markdown}</ChatMarkdown>
      {onApprove && (
        <Button className="w-fit" onClick={onApprove} disabled={busy}>
          {t("projectHandoffs.approve")}
        </Button>
      )}
      {onExport && (
        <Button className="w-fit" onClick={onExport} disabled={busy}>
          {t("projectHandoffs.download")}
        </Button>
      )}
    </section>
  );
}
