import { useMutation } from "@tanstack/react-query";
import { useContext, useRef } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { RunSourceAvailability, useRunSource, type RunSource } from "@/shared/lib/runSource";
import { RunSourceMenu } from "@/shared/session-ui/RunSourceMenu";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { launchExplanation, type FeynmanEntry } from "../../feynmanApi";

type Entry = Exclude<FeynmanEntry, { kind: "saved" }>;
const noKeys = new Set<string>();

export function ExplanationStart({
  entry,
  onStart,
}: {
  entry: Entry;
  onStart: (id: string) => void;
}) {
  const [source, setSource] = useRunSource();
  const keyed = useContext(RunSourceAvailability) ?? noKeys;
  const attempt = useRef<{ id: string; source: RunSource }>(null);
  const start = useMutation({
    mutationFn: ({ id, source }: NonNullable<typeof attempt.current>) =>
      launchExplanation(entry, id, source),
    onSuccess: (started) => {
      attempt.current = null;
      onStart(started.session_id);
    },
  });
  if (entry.kind === "ide" && !entry.path) return <p>{t("feynman.chooseFile")}</p>;
  const launch = () => {
    if (attempt.current?.source !== source) attempt.current = { id: crypto.randomUUID(), source };
    start.mutate(attempt.current);
  };
  return (
    <div className="flex flex-col items-start gap-3">
      {entry.kind === "ide" && entry.path && <p>{t("feynman.file", { name: entry.path })}</p>}
      <RunSourceMenu value={source} onChange={setSource} keyed={keyed} />
      <Button type="button" disabled={start.isPending} onClick={launch}>
        {t("feynman.start")}
      </Button>
      {start.error && <InlineError message={errorMessage(start.error)} />}
    </div>
  );
}
