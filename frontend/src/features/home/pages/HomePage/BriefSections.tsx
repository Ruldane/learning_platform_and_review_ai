import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { useCaptureRequest } from "@/shared/lib/captureRequest";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { AdviceCard } from "../../components/AdviceCard";
import { BlockCard } from "../../components/BlockCard";
import { BriefHeader } from "../../components/BriefHeader";
import { OffersCard } from "../../components/OffersCard";
import { QuickActions } from "../../components/QuickActions";
import { RemindersCard } from "../../components/RemindersCard";
import { ResourceCard } from "../../components/ResourceCard";
import { ReviewsCard } from "../../components/ReviewsCard";
import { WeekCard } from "../../components/WeekCard";
import type { BriefView } from "../../toView";

/** Les routes où l'accueil mène (il n'importe jamais une autre feature : il ne connaît que ses chemins). */
const STUDY_SESSION = "/etudier/session";
const REVIEWS = "/etudier/revisions";
const POSTINGS = "/carriere/offres";
const GOALS = "/apprendre/objectifs";
const applicationPath = (applicationId: string) => `/candidatures/${applicationId}`;

/**
 * Le brief du jour : l'en-tête, les actions rapides puis les sept rubriques dans l'ordre de F17
 * (bloc, révisions, relances, offres, avancement, ressource, conseil). Sans programme validé
 * (`week` vide), le bloc et l'avancement laissent la place à « Commence par un objectif ».
 */
export function BriefSections({ brief }: { brief: BriefView }) {
  const navigate = useNavigate();
  const requestCapture = useCaptureRequest((state) => state.request);
  const noProgram = brief.week === null;
  return (
    <div className="flex flex-col gap-4">
      <BriefHeader day={brief.day} generatedAt={brief.generatedAt} />
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
        <BlockCard block={brief.block} onStart={() => void navigate(STUDY_SESSION)} />
      )}
      <ReviewsCard
        queue={brief.reviews.queue}
        remaining={brief.reviews.remaining}
        onReview={() => void navigate(REVIEWS)}
      />
      <RemindersCard
        due={brief.reminders.due}
        items={brief.reminders.items}
        onOpen={(applicationId) => void navigate(applicationPath(applicationId))}
      />
      <OffersCard items={brief.offers} />
      {noProgram ? null : <WeekCard week={brief.week} />}
      <ResourceCard resource={brief.resource} />
      <AdviceCard sentences={brief.advice.sentences} status={brief.advice.status} />
    </div>
  );
}
