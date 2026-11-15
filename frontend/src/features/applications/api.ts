import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { ApplicationIn, ApplicationPatch, EventIn } from "./types";

const applicationPath = (applicationId: string) => ({
  params: { path: { application_id: applicationId } },
});

/** `GET /applications` : toutes les fiches, la plus récente d'abord ; relit d'abord les versions de CV. */
export async function fetchApplications(signal?: AbortSignal) {
  return unwrap(await api.GET("/applications", { signal }));
}

/** `GET /applications/stats` : les indicateurs et le nombre de relances dues. */
export async function fetchStats(signal?: AbortSignal) {
  return unwrap(await api.GET("/applications/stats", { signal }));
}

/** `GET /applications/{id}` : la fiche, ses contacts, son fil et ses relances ; 404 `application_not_found`. */
export async function fetchApplication(applicationId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/applications/{application_id}", { ...applicationPath(applicationId), signal }),
  );
}

/**
 * `POST /applications` (201) : `{ application, info }`. 409 `application_duplicate`
 * (`details.alerts`), 422 `fields`.
 */
export async function createApplication(body: ApplicationIn) {
  return unwrap(await api.POST("/applications", { body }));
}

/** `PATCH /applications/{id}` : les champs envoyés changent, `null` efface ; jamais le statut. */
export async function patchApplication(applicationId: string, body: ApplicationPatch) {
  return unwrap(
    await api.PATCH("/applications/{application_id}", { ...applicationPath(applicationId), body }),
  );
}

/** `POST /applications/{id}/events` : un changement de statut (avec sa date) ou une note. */
export async function postEvent(applicationId: string, body: EventIn) {
  return unwrap(
    await api.POST("/applications/{application_id}/events", {
      ...applicationPath(applicationId),
      body,
    }),
  );
}

/** `POST /applications/intake` (202) : la saisie en une phrase ; 409 `intake_in_progress`. */
export async function startIntake(text: string) {
  return unwrap(await api.POST("/applications/intake", { body: { text } }));
}

/** `GET /reminders?due=` : les relances dues (`true`) ou toutes (`false`), l'échéance croissante. */
export async function fetchReminders(due: boolean, signal?: AbortSignal) {
  return unwrap(await api.GET("/reminders", { params: { query: { due } }, signal }));
}

export type ReminderAction = "done" | "postpone" | "ignore";

/** `PATCH /reminders/{id}` : fait, reporté de 3 jours ou ignoré ; 404 `reminder_not_found`, 409 `reminder_closed`. */
export async function patchReminder(reminderId: string, action: ReminderAction) {
  return unwrap(
    await api.PATCH("/reminders/{reminder_id}", {
      params: { path: { reminder_id: reminderId } },
      body: { action },
    }),
  );
}
