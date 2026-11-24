import { useMutation } from "@tanstack/react-query";
import { useContext } from "react";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { RunSourceAvailability, useRunSource } from "@/shared/lib/runSource";
import { RunSourceMenu } from "@/shared/session-ui/RunSourceMenu";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { startDesign } from "../../systemDesignApi";

const noKeys = new Set<string>();

export function SystemDesignStart() {
  const navigate = useNavigate();
  const [source, setSource] = useRunSource();
  const keyed = useContext(RunSourceAvailability) ?? noKeys;
  const start = useMutation({
    mutationFn: () => startDesign(source),
    onSuccess: ({ interview_id }) => navigate(`/applications/system-design/${interview_id}`),
  });
  return (
    <div className="flex flex-col items-start gap-3">
      <RunSourceMenu value={source} onChange={setSource} keyed={keyed} />
      <Button type="button" disabled={start.isPending} onClick={() => start.mutate()}>
        {t("systemDesign.start")}
      </Button>
      {start.error && <InlineError message={errorMessage(start.error)} />}
    </div>
  );
}
