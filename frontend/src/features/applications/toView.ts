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
  ReminderOut,
  ReminderView,
  StatsView,
  StatusView,
} from "./types";

/** Une fiche de la liste ou du détail → la fiche que les cartes et le tableau affichent. */
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

/** Une relance du serveur ; son canal n'est pas repris (January copie, l'application n'envoie rien). */
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

/** Les indicateurs : les huit statuts sont toujours là, à zéro quand le serveur n'en dit rien. */
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

/** Les contacts à enregistrer : le serveur remplace la liste, sans identifiant ; un vide devient `null`. */
export function toContactsIn(contacts: ContactView[]): ContactIn[] {
  return contacts.map(({ name, role, url }) => ({
    name: name.trim(),
    role: role?.trim() || null,
    url: url?.trim() || null,
  }));
}

/** La question `application_confirm` de l'Assistant de suivi → la fiche à confirmer (valeurs lues, issues du serveur). */
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
