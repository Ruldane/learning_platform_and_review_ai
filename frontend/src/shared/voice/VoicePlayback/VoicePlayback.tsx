import { useRef } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { usePlayback } from "./usePlayback";

const MAX_SPOKEN_TEXT = 1200;

export function VoicePlayback({ text }: { text: string }) {
  const clean = text.trim();
  const playback = usePlayback(clean);
  const action = useRef<HTMLButtonElement>(null);
  if (!clean) return null;
  const chars = Array.from(clean);
  const label = chars.length > MAX_SPOKEN_TEXT ? t("voice.preview") : t("voice.listen");
  return (
    <div className="flex flex-col items-start gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          ref={action}
          type="button"
          variant="ghost"
          size="sm"
          aria-disabled={playback.view?.loading}
          onClick={() => {
            if (!playback.view?.loading)
              void playback.prepare(chars.slice(0, MAX_SPOKEN_TEXT).join(""));
          }}
        >
          {playback.view?.loading ? t("voice.preparing") : label}
        </Button>
        {(playback.view?.loading || playback.view?.url) && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              action.current?.focus();
              playback.cancel();
            }}
          >
            {t("voice.cancel")}
          </Button>
        )}
      </div>
      {playback.view?.url && (
        <audio controls src={playback.view.url} aria-label={t("voice.player")} />
      )}
      {playback.view?.error && (
        <p role="alert" className="text-sm text-destructive">
          {playback.view.error}
        </p>
      )}
    </div>
  );
}
