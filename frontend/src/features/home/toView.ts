import type {
  ActivityItemView,
  AdviceStatus,
  BlockView,
  OfferItemView,
  ReminderItemView,
  ResourceView,
  WeekView,
} from "./components/viewTypes";
import type { ActivityItem, BriefOut } from "./types";

/** Le brief du jour, rubrique par rubrique, sous la forme que lisent les composants. */
export interface BriefView {
  id: string;
  /** Le jour local `AAAA-MM-JJ`. */
  day: string;
  generatedAt: string;
  block: BlockView | null;
  reviews: { queue: number; remaining: number };
  reminders: { due: number; items: ReminderItemView[] };
  offers: OfferItemView[];
  /** `null` : aucun programme validé. */
  week: WeekView | null;
  resource: ResourceView | null;
  advice: { sentences: string[] | null; status: AdviceStatus };
  /** La session du conseil, suivie tant qu'il est `pending`. */
  sessionId: string | null;
  /** Les rubriques dont la source était en panne ce matin (`block`, `reviews`, `reminders`, `offers`, `week`) : leur valeur vide n'est pas un vrai zéro. */
  unavailable: readonly string[];
}

export function toBriefView(brief: BriefOut): BriefView {
  return {
    id: brief.id,
    day: brief.day,
    generatedAt: brief.generated_at,
    block: brief.block && {
      moduleTitle: brief.block.module_title,
      lessonTitle: brief.block.lesson_title,
      minutes: brief.block.minutes,
      tasks: brief.block.tasks.map((task) => ({ title: task.title, minutes: task.minutes })),
    },
    reviews: { queue: brief.reviews.queue, remaining: brief.reviews.remaining },
    reminders: {
      due: brief.reminders.due,
      items: brief.reminders.items.map((item) => ({
        id: item.reminder_id,
        applicationId: item.application_id,
        company: item.company,
        title: item.title,
        dueOn: item.due_on,
      })),
    },
    offers: brief.offers.items.map((offer) => ({
      title: offer.title,
      company: offer.company,
      score: offer.score,
      url: offer.url,
    })),
    week: brief.week && {
      doneMinutes: brief.week.done_minutes,
      plannedMinutes: brief.week.planned_minutes,
      streakDays: brief.week.streak_days,
      tasksDone: brief.week.tasks_done,
      tasksTotal: brief.week.tasks_total,
    },
    resource: brief.resource && {
      title: brief.resource.title,
      domain: brief.resource.domain,
      published: brief.resource.published,
      why: brief.resource.why,
      url: brief.resource.url,
    },
    advice: { sentences: brief.advice, status: brief.advice_status },
    sessionId: brief.session_id,
    unavailable: brief.unavailable ?? [],
  };
}

export function toActivityView(item: ActivityItem): ActivityItemView {
  return {
    id: item.id,
    kind: item.kind,
    at: item.at,
    title: item.title,
    detail: item.detail ?? null,
    link: item.link ?? null,
  };
}
