import { t } from "@/shared/i18n/t";
import { ExchangeList } from "../ExchangeList";
import { ScoreBar } from "../ScoreBar";
import type { InterviewView } from "../viewTypes";
import { CardsSection } from "./CardsSection";
import { DebriefPoints } from "./DebriefPoints";
import { ImprovedAnswer } from "./ImprovedAnswer";
import { UnratedNote } from "./UnratedNote";

interface DebriefViewProps {
  interview: InterviewView;
  /** La page des révisions (flashcards), où les fiches de l'entretien attendent. */
  reviewsHref: string;
}

/**
 * Le débrief d'un entretien : les quatre notes sur 5 (en texte et en barre), trois points forts,
 * trois points à corriger, la réponse améliorée (« à vérifier » si elle cite des termes que le
 * profil ne dit pas), les fiches de révision créées et chaque réponse avec sa note.
 */
export function DebriefView({ interview, reviewsHref }: DebriefViewProps) {
  const { debrief } = interview;
  if (debrief === null) return null;
  return (
    <div className="flex flex-col gap-5">
      <section className="flex flex-col gap-2">
        <h3 id="debrief-scores" className="text-lg font-semibold">
          {t("applications.debrief.scores")}
        </h3>
        <ul aria-labelledby="debrief-scores" className="flex max-w-lg flex-col gap-3">
          {debrief.scores.map((score) => (
            <ScoreBar key={score.key} name={score.key} value={score.value} />
          ))}
        </ul>
        <UnratedNote unrated={debrief.unrated} />
      </section>
      <DebriefPoints title={t("applications.debrief.strengths")} items={debrief.strengths} />
      <DebriefPoints title={t("applications.debrief.fixes")} items={debrief.fixes} />
      <ImprovedAnswer
        text={debrief.improvedAnswer}
        flags={interview.flags}
        question={interview.exchanges.find((entry) => entry.index === debrief.weakestIndex)}
      />
      <CardsSection count={interview.cardsCreated} reviewsHref={reviewsHref} />
      <section aria-labelledby="debrief-answers" className="flex flex-col gap-2">
        <h3 id="debrief-answers" className="text-lg font-semibold">
          {t("applications.debrief.answers")}
        </h3>
        <ExchangeList
          exchanges={interview.exchanges}
          missed={debrief.missed}
          expected={debrief.expected}
        />
      </section>
    </div>
  );
}
