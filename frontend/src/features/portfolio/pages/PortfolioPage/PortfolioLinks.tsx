import { useMutation } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { proposeLink, type Publication, type Target } from "../../api";

export function PortfolioLinks({ value, reload }: { value: Publication; reload: () => void }) {
  const links = useMutation({
    mutationFn: ([target, enabled]: [Target, boolean]) => proposeLink(value, target, enabled),
    onSuccess: reload,
  });
  return (
    <div className="flex flex-wrap gap-2">
      <Button
        type="button"
        variant="outline"
        disabled={links.isPending}
        onClick={() => links.mutate(["cv", !value.use_in_cv])}
      >
        {t(value.use_in_cv ? "portfolio.clearCv" : "portfolio.proposeCv")}
      </Button>
      <Button
        type="button"
        variant="outline"
        disabled={links.isPending}
        onClick={() => links.mutate(["kit", !value.use_in_kit])}
      >
        {t(value.use_in_kit ? "portfolio.clearKit" : "portfolio.proposeKit")}
      </Button>
      {links.error && <InlineError message={errorMessage(links.error)} />}
    </div>
  );
}
