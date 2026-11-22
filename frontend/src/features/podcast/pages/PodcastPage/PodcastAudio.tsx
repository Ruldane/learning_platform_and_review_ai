import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { audioUrl } from "../../api";

export function PodcastAudio({ id }: { id: string }) {
  const [error, setError] = useState(false);
  return error ? (
    <p className="text-sm text-muted-foreground">{t("podcast.transcriptOnly")}</p>
  ) : (
    <section className="flex flex-col gap-2 rounded-xl border bg-card p-4">
      <p className="text-sm text-muted-foreground">{t("podcast.audioAI")}</p>
      <audio
        controls
        preload="none"
        className="w-full"
        aria-label={t("podcast.player")}
        src={audioUrl(id)}
        onError={() => setError(true)}
      />
    </section>
  );
}
