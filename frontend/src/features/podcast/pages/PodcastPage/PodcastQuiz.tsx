import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { checkPodcast, type Episode } from "../../api";
import { PodcastQuestions } from "./PodcastQuestions";

export function PodcastQuiz({ episode }: { episode: Episode }) {
  const [selected, setSelected] = useState<Record<number, number>>({});
  const grade = useMutation({
    mutationFn: (answers: number[]) => checkPodcast(episode.id, answers),
  });
  const choices = episode.questions.flatMap((_, index) => {
    const answer = selected[index];
    return answer === undefined ? [] : [answer];
  });
  const complete = choices.length === episode.questions.length;
  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (complete && !grade.isPending) grade.mutate(choices);
      }}
    >
      <h2 className="text-lg font-semibold">{t("podcast.quiz")}</h2>
      <PodcastQuestions
        questions={episode.questions}
        selected={selected}
        result={grade.data}
        onChange={(question, choice) => {
          setSelected({ ...selected, [question]: choice });
          if (grade.data) grade.reset();
        }}
      />
      <Button type="submit" className="self-start" disabled={!complete || grade.isPending}>
        {t("podcast.check")}
      </Button>
      {grade.error ? <InlineError message={errorMessage(grade.error)} /> : null}
      {grade.data ? <p role="status">{t("podcast.score", { score: grade.data.score })}</p> : null}
    </form>
  );
}
