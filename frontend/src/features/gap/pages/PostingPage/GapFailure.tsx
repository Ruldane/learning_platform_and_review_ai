import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { useRelaunchGap } from "../../hooks/useRelaunchGap";

export function GapFailure({ relaunch }: { relaunch: ReturnType<typeof useRelaunchGap> }) {
  return (
    <div className="flex flex-col items-start gap-2">
      <InlineError message={relaunch.error ?? t("gap.posting.gapFailed")} />
      {relaunch.providerMenu}
      <Button onClick={relaunch.relaunch} disabled={relaunch.pending}>
        {relaunch.pending ? t("gap.posting.relaunching") : t("gap.posting.relaunch")}
      </Button>
    </div>
  );
}
