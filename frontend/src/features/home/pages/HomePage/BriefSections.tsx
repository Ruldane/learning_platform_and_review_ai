import type { ReactNode } from "react";
import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { useCaptureRequest } from "@/shared/lib/captureRequest";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { AdviceCard } from "../../components/AdviceCard";
import { BlockCard } from "../../components/BlockCard";
import { BriefHeader } from "../../components/BriefHeader";
import { OffersCard } from "../../components/OffersCard";
import { PodcastBriefLink } from "../../components/PodcastBriefLink";
import { QuickActions } from "../../components/QuickActions";
import { ReadingBriefLink } from "../../components/ReadingBriefLink";
import { RemindersCard } from "../../components/RemindersCard";
import { ResourceCard } from "../../components/ResourceCard";
import { ReviewsCard } from "../../components/ReviewsCard";
import { WeekCard } from "../../components/WeekCard";
import type { BriefView } from "../../toView";

/** The routes home leads to (it never imports another feature: it only knows their paths). */
const STUDY_SESSION = "/study/session";
const REVIEWS = "/study/reviews";
const POSTINGS = "/career/postings";
const GOALS = "/learn/goals";
const applicationPath = (applicationId: string) => `/applications/${applicationId}`;

/**
 * Today's brief: the header, quick actions, then the seven sections in F17 order
 * (block, reviews, reminders, offers, progress, resource, advice). Without a validated program
 * (`week` empty), the block and progress make room for « Commence par un objectif ».
 */
export function BriefSections({ brief, guide }: { brief: BriefView; guide?: ReactNode }) {
  const navigate = useNavigate();
  const requestCapture = useCaptureRequest((state) => state.request);
  const down = (name: string) => brief.unavailable.includes(name);
  // An unavailable week is not « aucun programme »: the block stays shown.
  const noProgram = brief.week === null && !down("week");
  return (
    <div className="flex flex-col gap-4">
      <BriefHeader day={brief.day} generatedAt={brief.generatedAt} />
      {guide}
      <QuickActions
        onStart={() => void navigate(STUDY_SESSION)}
        onReview={() => void navigate(REVIEWS)}
        onAddPosting={() => void navigate(POSTINGS)}
        onCapture={requestCapture}
      />
      {noProgram ? (
        <EmptyState
          title={t("home.noProgram.title")}
          description={t("home.noProgram.description")}
          action={{ label: t("home.noProgram.action"), onClick: () => void navigate(GOALS) }}
        />
      ) : (
        <BlockCard
          block={brief.block}
          unavailable={down("block")}
          onStart={() => void navigate(STUDY_SESSION)}
        />
      )}
      <ReviewsCard
        queue={brief.reviews.queue}
        remaining={brief.reviews.remaining}
        unavailable={down("reviews")}
        onReview={() => void navigate(REVIEWS)}
      />
      <ReadingBriefLink count={brief.readingUnread} />
      <RemindersCard
        due={brief.reminders.due}
        items={brief.reminders.items}
        unavailable={down("reminders")}
        onOpen={(applicationId) => void navigate(applicationPath(applicationId))}
      />
      <OffersCard items={brief.offers} unavailable={down("offers")} />
      {noProgram ? null : <WeekCard week={brief.week} unavailable={down("week")} />}
      <ResourceCard resource={brief.resource} />
      <AdviceCard sentences={brief.advice.sentences} status={brief.advice.status} />
      <PodcastBriefLink />
    </div>
  );
}
