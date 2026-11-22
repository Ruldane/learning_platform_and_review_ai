import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { Mission } from "../../api";
import { MissionProof } from "../MissionProof";

export function MissionSubmission({
  mission,
  working,
  error,
  onSubmit,
}: {
  mission: Mission;
  working: boolean;
  error: Error | null;
  onSubmit: (artifact: string) => void;
}) {
  const [artifact, setArtifact] = useState("");
  if (mission.submission) return <MissionProof submission={mission.submission} />;
  if (mission.status !== "active") return null;
  const canSubmit = mission.criteria.every((criterion) => criterion.observed === criterion.target);
  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (canSubmit && artifact.trim() && !working) onSubmit(artifact.trim());
      }}
    >
      {!canSubmit && <p>{t("missions.remaining")}</p>}
      <label className="flex flex-col">
        {t("missions.artifact")}
        <textarea
          className="rounded border border-border bg-background p-2"
          rows={5}
          maxLength={8000}
          value={artifact}
          onChange={(event) => setArtifact(event.target.value)}
        />
      </label>
      {error && <p role="alert">{errorMessage(error)}</p>}
      <Button
        type="submit"
        className="self-start"
        disabled={!canSubmit || working || !artifact.trim()}
      >
        {t("missions.submit")}
      </Button>
    </form>
  );
}
