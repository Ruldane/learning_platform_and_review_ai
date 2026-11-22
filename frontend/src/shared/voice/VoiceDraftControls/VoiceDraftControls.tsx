import { useRef } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { canRecord } from "../capture";
import { useVoiceDraft } from "../useVoiceDraft";

function mainAction(draft: ReturnType<typeof useVoiceDraft>) {
  switch (draft.view.stage) {
    case "permission":
      return { label: t("voice.asking"), action: undefined };
    case "recording":
      return { label: t("voice.stop"), action: draft.view.hasSamples ? draft.finish : undefined };
    case "ready":
      return { label: t("voice.transcribe"), action: () => void draft.send() };
    case "transcribing":
      return { label: t("voice.transcribing"), action: undefined };
    case "idle":
      return { label: t("voice.start"), action: () => void draft.start() };
  }
}

export function VoiceDraftControls({ onDraft }: { onDraft: (text: string) => void }) {
  const draft = useVoiceDraft(onDraft);
  const main = useRef<HTMLButtonElement>(null);
  if (!canRecord()) return null;
  const { label, action } = mainAction(draft);
  return (
    <div className="flex w-full flex-col gap-2">
      {draft.view.stage === "idle" && (
        <p className="text-xs text-muted-foreground">{t("voice.microphoneHint")}</p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Button ref={main} type="button" variant="outline" aria-disabled={!action} onClick={action}>
          {label}
        </Button>
        {draft.view.stage !== "idle" && (
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              main.current?.focus();
              draft.cancel();
            }}
          >
            {t("voice.cancel")}
          </Button>
        )}
      </div>
      {draft.view.error && (
        <p role="alert" className="text-sm text-destructive">
          {draft.view.error}
        </p>
      )}
      <div role="status" className="text-sm text-muted-foreground">
        {draft.view.notice ?? (draft.view.stage === "recording" ? t("voice.recording") : "")}
      </div>
    </div>
  );
}
