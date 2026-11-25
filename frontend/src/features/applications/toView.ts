import type { InterruptPayload } from "@/shared/realtime/types";
import type { DuplicateAlertView } from "@/shared/ui/DuplicateAlert";
import { STATUS_ORDER } from "./types";
import type {
  AlertOut,
  ApplicationDetail,
  ApplicationOut,
  ApplicationStatsOut,
  ApplicationView,
  ConfirmationView,
  ContactIn,
  ContactOut,
  ContactView,
  EventOut,
  EventView,
  KitItemOut,
  KitOut,
  KitPieceView,
  KitView,
  ReminderOut,
  ReminderView,
  StatsView,
  StatusView,
} from "./types";

/** A record from the list or detail → the record the cards and the table display. */
export function toApplicationView(out: ApplicationOut | ApplicationDetail): ApplicationView {
  return {
    id: out.id,
    company: out.company,
    title: out.title,
    status: out.status,
    channel: out.channel,
    appliedOn: out.applied_on,
    interviewOn: out.interview_on,
    nextAction: out.next_action,
    nextActionOn: out.next_action_on,
    dueReminders: out.due_reminders,
  };
}

export function toContactView(out: ContactOut): ContactView {
  return { id: out.id, name: out.name, role: out.role, url: out.url };
}

export function toEventView(out: EventOut): EventView {
  return {
    id: out.id,
    kind: out.kind,
    at: out.at,
    statusFrom: out.status_from,
    statusTo: out.status_to,
    text: out.text,
  };
}

/** A reminder from the server; its channel is not carried over (January copies, the app sends
 * nothing). */
export function toReminderView(out: ReminderOut): ReminderView {
  return {
    id: out.id,
    applicationId: out.application_id,
    kind: out.kind,
    dueOn: out.due_on,
    company: out.company,
    title: out.title,
    contact: out.contact ? toContactView(out.contact) : null,
    linkedinSearchUrl: out.linkedin_search_url,
    draft: out.draft,
  };
}

/** The indicators: the eight statuses are always there, at zero when the server says nothing. */
export function toStatsView(out: ApplicationStatsOut): StatsView {
  const byStatus = Object.fromEntries(
    STATUS_ORDER.map((status) => [status, out.by_status[status] ?? 0]),
  ) as Record<StatusView, number>;
  return {
    byStatus,
    responseRate: out.response_rate,
    meanResponseDays: out.mean_response_days,
    dueReminders: out.due_reminders,
  };
}

export function toAlertView(out: AlertOut): DuplicateAlertView {
  return {
    level: out.level,
    applicationId: out.application_id,
    company: out.company,
    title: out.title,
    status: out.status,
    message: out.message,
  };
}

/** The contacts to save: the server replaces the list, without an identifier; an empty one becomes
 * `null`. */
export function toContactsIn(contacts: ContactView[]): ContactIn[] {
  return contacts.map(({ name, role, url }) => ({
    name: name.trim(),
    role: role?.trim() || null,
    url: url?.trim() || null,
  }));
}

/** The `application_confirm` question from the tracking Assistant → the record to confirm (values
 * read, server outcomes). */
export function toConfirmationView(payload: InterruptPayload): ConfirmationView {
  return {
    question: payload.question,
    fields: (payload.fields ?? []).map((field) => ({
      id: field.id,
      label: field.label,
      required: field.required ?? false,
      maxLength: field.max_length ?? 2000,
      value: field.value ?? "",
    })),
    options: (payload.options ?? []).map(({ value, label }) => ({ value, label })),
  };
}

/** A kit piece from the server → the piece the page shows. */
export function toKitPieceView(out: KitItemOut): KitPieceView {
  return {
    kind: out.kind,
    status: out.status,
    content: out.content,
    flags: out.flags,
    salaryFields: out.salary_fields,
    words: out.words,
    sources: out.sources.map(({ rank, url, title }) => ({ rank, url, title })),
    edited: out.edited,
    error: out.error,
    updatedAt: out.updated_at,
  };
}

/** The kit from the server → the page view. */
export function toKitView(out: KitOut): KitView {
  return { sessionId: out.session_id, running: out.running, pieces: out.items.map(toKitPieceView) };
}
