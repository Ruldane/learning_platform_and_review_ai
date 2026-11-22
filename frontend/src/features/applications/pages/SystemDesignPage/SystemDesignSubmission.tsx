import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import type { Run } from "@/shared/realtime/useRun";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { mergeVoiceDraft, VoiceDraftControls, VoicePlayback } from "@/shared/voice";
import type { Design } from "../../systemDesignApi";
import { SystemDesignDefense } from "./SystemDesignDefense";

function hasDrawing(board: Design["board"]) {
  const { scene } = board;
  return (
    Array.isArray(scene?.elements) &&
    scene.elements.some(
      (item: unknown) =>
        item && typeof item === "object" && (!("isDeleted" in item) || !item.isDeleted),
    )
  );
}

export function SystemDesignSubmission({
  board,
  dirty,
  run,
}: {
  board: Design["board"];
  dirty: boolean;
  run: Run;
}) {
  const [defense, setDefense] = useState("");
  const prompt = run.stream.pendingInterrupt;
  const ready = prompt?.kind === "system_design_submission";
  const saved = board.step > 0 && hasDrawing(board);
  const disabled = !ready || run.actions.pending;
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!dirty && saved && ready && defense.trim()) {
      void run.actions.resume(prompt.interrupt_id, { board_id: board.id, defense });
    }
  };
  return (
    <form className="flex max-w-3xl flex-col gap-3" onSubmit={submit}>
      {ready && prompt.question ? <VoicePlayback text={prompt.question} /> : null}
      <SystemDesignDefense value={defense} onChange={setDefense} disabled={disabled} />
      {!disabled ? (
        <VoiceDraftControls onDraft={(text) => setDefense((current) => mergeVoiceDraft(current, text, 4000))} />
      ) : null}
      {(!saved || dirty) && <p className="text-sm">{t("systemDesign.saveFirst")}</p>}
      <Button
        type="submit"
        className="self-start"
        disabled={disabled || dirty || !saved || !defense.trim()}
      >
        {t("systemDesign.submit")}
      </Button>
      {run.actions.error && <InlineError message={run.actions.error} />}
    </form>
  );
}
