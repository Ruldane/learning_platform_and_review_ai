import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

export function IssuedLink({ url }: { url: string }) {
  const [copied, setCopied] = useState(false);
  function copy() {
    void navigator.clipboard.writeText(url).then(() => setCopied(true), () => setCopied(false));
  }
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border p-4">
      <label className="flex flex-col gap-1.5 text-sm">
        <span>{t("mentorReviews.link")}</span>
        <input id="mentor-link" readOnly value={url}
          className="min-w-0 rounded-md border border-input bg-background p-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
      </label>
      <Button type="button" variant="outline" className="self-start" onClick={copy}
        disabled={!navigator.clipboard}>
        {t("mentorReviews.copy")}
      </Button>
      {copied && <p role="status">{t("mentorReviews.copied")}</p>}
    </div>
  );
}
