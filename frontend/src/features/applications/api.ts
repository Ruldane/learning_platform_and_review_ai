import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type {
  ApplicationIn,
  ApplicationPatch,
  EventIn,
  FreeInterviewIn,
  InterviewIn,
  KitKindView,
} from "./types";

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

/** `GET /applications/{id}/kit` : toujours les sept pièces, `pending` pour celles pas encore rangées. */
export async function fetchKit(applicationId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/applications/{application_id}/kit", {
      ...applicationPath(applicationId),
      signal,
    }),
  );
}

/**
 * `POST /applications/{id}/kit` (202) : lance le kit. 409 `kit_in_progress` (`details.session_id`),
 * `posting_required`, `profile_required` ; 503 `engine_unavailable`.
 */
export async function startKit(applicationId: string) {
  return unwrap(
    await api.POST("/applications/{application_id}/kit", applicationPath(applicationId)),
  );
}

/** `PATCH /applications/{id}/kit/{kind}` : le texte de January ; le serveur relit une pièce à vérifier. */
export async function patchKitItem(applicationId: string, kind: KitKindView, content: string) {
  return unwrap(
    await api.PATCH("/applications/{application_id}/kit/{kind}", {
      params: { path: { application_id: applicationId, kind } },
      body: { content },
    }),
  );
}

/** `GET /interviews` : les entretiens de January, le plus récent d'abord ; `applicationId` filtre sur une fiche (404 si elle n'existe pas). */
export async function fetchInterviews(applicationId: string | null, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/interviews", {
      params: { query: applicationId ? { application_id: applicationId } : {} },
      signal,
    }),
  );
}

/** `GET /interviews/{id}` : un entretien (relu : une session morte le passe à `failed`) ; 404 `interview_not_found`. */
export async function fetchInterview(interviewId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/interviews/{interview_id}", {
      params: { path: { interview_id: interviewId } },
      signal,
    }),
  );
}

/**
 * `POST /applications/{id}/interviews` (202) : un entretien sur une fiche. 409 `interview_in_progress`
 * (`details.interview_id`), `profile_required` ; 404 ; 503 `engine_unavailable`.
 */
export async function startApplicationInterview(applicationId: string, body: InterviewIn) {
  return unwrap(
    await api.POST("/applications/{application_id}/interviews", {
      ...applicationPath(applicationId),
      body,
    }),
  );
}

/** `POST /interviews` (202) : un entretien sans fiche, sur une offre (`posting_id`) ou un intitulé (`role`). */
export async function startFreeInterview(body: FreeInterviewIn) {
  return unwrap(await api.POST("/interviews", { body }));
}

/** `GET /postings` : les offres, la plus récente d'abord (le choix de l'offre d'un entretien libre). */
export async function fetchPostings(signal?: AbortSignal) {
  return unwrap(await api.GET("/postings", { signal }));
}
