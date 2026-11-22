import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { Episode } from "../../api";
import { PodcastAudio } from "./PodcastAudio";
import { PodcastQuiz } from "./PodcastQuiz";

export function PodcastEpisode({ episode }: { episode: Episode }) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-xl font-semibold">{episode.title}</h2>
      <Link className="self-start text-sm underline" to={`/apprendre/lecons/${episode.lesson_id}`}>
        {t("podcast.openLesson")}
      </Link>
      {episode.status === "ready" ? <PodcastAudio key={episode.id} id={episode.id} /> : null}
      {episode.status === "transcript" ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("podcast.transcriptOnly")}
        </p>
      ) : null}
      {episode.lines.length ? (
        <section className="flex flex-col gap-3">
          <h2 className="text-lg font-semibold">{t("podcast.transcript")}</h2>
          {episode.lines.map((line, rank) => (
            <p key={rank} className="whitespace-pre-wrap break-words text-sm leading-relaxed">
              <strong>{t(`podcast.speakers.${line.speaker}`)}</strong> {line.text}
            </p>
          ))}
        </section>
      ) : null}
      {episode.questions.length ? <PodcastQuiz key={episode.id} episode={episode} /> : null}
    </section>
  );
}
