import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { issueSyncToken } from "../../api";

export function SyncTokenPanel() {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const issue = useMutation({
    mutationFn: issueSyncToken,
    onMutate: () => {
      setCopied(false);
      setCopyError(false);
    },
  });
  const token = issue.data?.token;
  const copy = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setCopyError(false);
    } catch {
      setCopyError(true);
    }
  };
  return (
    <details className="max-w-3xl rounded-xl border border-border p-4">
      <summary className="cursor-pointer font-semibold">{t("brain.relay")}</summary>
      <div className="mt-3 flex flex-col gap-3">
        <p className="text-sm text-muted-foreground">
          {t("brain.tokenInstructions", { variable: "TREMPLIN_BRAIN_SYNC_TOKEN" })}
        </p>
        <Button
          type="button"
          variant="outline"
          className="self-start"
          disabled={issue.isPending}
          onClick={() => issue.mutate()}
        >
          {t("brain.issue")}
        </Button>
        {issue.error ? <InlineError message={errorMessage(issue.error)} /> : null}
        {copyError ? <InlineError message={t("brain.copyError")} /> : null}
        {token ? (
          <div className="flex flex-wrap items-center gap-3">
            <code className="break-all rounded bg-muted p-2 text-sm">{token}</code>
            <Button type="button" variant="outline" onClick={() => void copy(token)}>
              {t(copied ? "brain.copied" : "brain.copy")}
            </Button>
          </div>
        ) : null}
      </div>
    </details>
  );
}
