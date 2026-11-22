import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { buildDraft, type Site } from "../../api";
import { CandidateChoices } from "./CandidateChoices";

export function PortfolioCandidates({
  candidates,
  reload,
}: {
  candidates: Site["candidates"];
  reload: () => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const build = useMutation({ mutationFn: buildDraft, onSuccess: reload });
  const current = selected.filter((id) => candidates.some((candidate) => candidate.id === id));
  const toggle = (id: string) =>
    setSelected((before) =>
      before.includes(id) ? before.filter((key) => key !== id) : [...before, id],
    );
  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="mb-2 text-lg font-semibold">{t("portfolio.select")}</legend>
      {candidates.length === 0 && <p>{t("portfolio.noFacts")}</p>}
      <CandidateChoices
        candidates={candidates}
        selected={current}
        busy={build.isPending}
        onToggle={toggle}
      />
      <Button
        type="button"
        className="self-start"
        disabled={build.isPending || current.length === 0}
        onClick={() => build.mutate(current)}
      >
        {t("portfolio.prepare")}
      </Button>
      {build.error && <InlineError message={errorMessage(build.error)} />}
    </fieldset>
  );
}
