import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";

interface Props {
  busy: boolean;
  error: Error | null;
  html: string | undefined;
}

export function PortfolioPreview({ busy, error, html }: Props) {
  if (busy) return <LoadingState />;
  if (error) return <InlineError message={errorMessage(error)} />;
  if (!html) return null;
  return (
    <iframe
      title={t("portfolio.preview")}
      sandbox=""
      srcDoc={html}
      className="h-[31rem] w-full rounded-lg border border-border"
    />
  );
}
