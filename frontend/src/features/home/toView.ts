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

/** Today's brief, section by section, in the shape the components read. */
export interface BriefView {
  id: string;
  /** The local day, `YYYY-MM-DD`. */
  day: string;
  generatedAt: string;
  block: BlockView | null;
  reviews: { queue: number; remaining: number };
  reminders: { due: number; items: ReminderItemView[] };
  offers: OfferItemView[];
  readingUnread: number;
  /** `null`: no validated program. */
  week: WeekView | null;
  resource: ResourceView | null;
  advice: { sentences: string[] | null; status: AdviceStatus };
  /** The advice session, followed while it is `pending`. */
  sessionId: string | null;
  /** Sections whose source was down this morning: their empty value is not a real zero. */
  unavailable: readonly string[];
}

function offerView(offer: BriefOut["offers"]["items"][number]): OfferItemView {
  const { title, company, score, url, run_id, offer_ref } = offer;
  const view = { title, company, score, url };
  if (!run_id || !offer_ref) return view;
  return {
    ...view,
    gapPath:
      `/career/compatible-offers/${encodeURIComponent(run_id)}/${encodeURIComponent(offer_ref)}`,
  };
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
    offers: brief.offers.items.map(offerView),
    readingUnread: brief.reading_unread ?? 0,
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
