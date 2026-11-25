import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import { runSourceHeaders, type RunSource } from "@/shared/lib/runSource";
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

/** `GET /applications`: all records, most recent first; re-reads the CV versions first. */
export async function fetchApplications(signal?: AbortSignal) {
  return unwrap(await api.GET("/applications", { signal }));
}

/** `GET /applications/stats`: the indicators and the number of reminders due. */
export async function fetchStats(signal?: AbortSignal) {
  return unwrap(await api.GET("/applications/stats", { signal }));
}

/** `GET /applications/{id}`: the record, its contacts, its thread and its reminders; 404
 * `application_not_found`. */
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

/** `PATCH /applications/{id}`: the fields sent change, `null` clears; never the status. */
export async function patchApplication(applicationId: string, body: ApplicationPatch) {
  return unwrap(
    await api.PATCH("/applications/{application_id}", { ...applicationPath(applicationId), body }),
  );
}

/** `POST /applications/{id}/events`: a status change (with its date) or a note. */
export async function postEvent(applicationId: string, body: EventIn) {
  return unwrap(
    await api.POST("/applications/{application_id}/events", {
      ...applicationPath(applicationId),
      body,
    }),
  );
}

/** `POST /applications/intake` (202): the one-sentence entry; 409 `intake_in_progress`. */
export async function startIntake(text: string, source?: RunSource) {
  return unwrap(
    await api.POST("/applications/intake", { body: { text }, headers: runSourceHeaders(source) }),
  );
}

/** `GET /reminders?due=`: the reminders due (`true`) or all of them (`false`), by ascending due
 * date. */
export async function fetchReminders(due: boolean, signal?: AbortSignal) {
  return unwrap(await api.GET("/reminders", { params: { query: { due } }, signal }));
}

export type ReminderAction = "done" | "postpone" | "ignore";

/** `PATCH /reminders/{id}`: done, postponed by 3 days, or ignored; 404 `reminder_not_found`, 409
 * `reminder_closed`. */
export async function patchReminder(reminderId: string, action: ReminderAction) {
  return unwrap(
    await api.PATCH("/reminders/{reminder_id}", {
      params: { path: { reminder_id: reminderId } },
      body: { action },
    }),
  );
}

/** `GET /applications/{id}/kit`: always the seven pieces, `pending` for those not yet filed. */
export async function fetchKit(applicationId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/applications/{application_id}/kit", {
      ...applicationPath(applicationId),
      signal,
    }),
  );
}

/**
 * `POST /applications/{id}/kit` (202): starts the kit. 409 `kit_in_progress`
 * (`details.session_id`),
 * `posting_required`, `profile_required` ; 503 `engine_unavailable`.
 */
export async function startKit(applicationId: string, source?: RunSource) {
  return unwrap(
    await api.POST("/applications/{application_id}/kit", {
      ...applicationPath(applicationId),
      headers: runSourceHeaders(source),
    }),
  );
}

/** `PATCH /applications/{id}/kit/{kind}`: January's text; the server re-reads a piece to check. */
export async function patchKitItem(applicationId: string, kind: KitKindView, content: string) {
  return unwrap(
    await api.PATCH("/applications/{application_id}/kit/{kind}", {
      params: { path: { application_id: applicationId, kind } },
      body: { content },
    }),
  );
}

/** `GET /interviews`: January's interviews, most recent first; `applicationId` filters by record
 * (404 if it does not exist). */
export async function fetchInterviews(applicationId: string | null, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/interviews", {
      params: { query: applicationId ? { application_id: applicationId } : {} },
      signal,
    }),
  );
}

/** `GET /interviews/{id}`: an interview (re-read: a dead session sets it to `failed`); 404
 * `interview_not_found`. */
export async function fetchInterview(interviewId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/interviews/{interview_id}", {
      params: { path: { interview_id: interviewId } },
      signal,
    }),
  );
}

/**
 * `POST /applications/{id}/interviews` (202): an interview on a record. 409 `interview_in_progress`
 * (`details.interview_id`), `profile_required` ; 404 ; 503 `engine_unavailable`.
 */
export async function startApplicationInterview(
  applicationId: string,
  body: InterviewIn,
  source?: RunSource,
) {
  return unwrap(
    await api.POST("/applications/{application_id}/interviews", {
      headers: runSourceHeaders(source),
      ...applicationPath(applicationId),
      body,
    }),
  );
}

/** `POST /interviews` (202): an interview without a record, on a posting (`posting_id`) or a job
 * title (`role`). */
export async function startFreeInterview(body: FreeInterviewIn, source?: RunSource) {
  return unwrap(await api.POST("/interviews", { body, headers: runSourceHeaders(source) }));
}

/** `GET /postings`: the postings, most recent first (the posting choice for a free interview). */
export async function fetchPostings(signal?: AbortSignal) {
  return unwrap(await api.GET("/postings", { signal }));
}

/** `GET /committee?posting_id=`: the committee runs for a posting, most recent first. */
export async function fetchCommittees(postingId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/committee", { params: { query: { posting_id: postingId } }, signal }),
  );
}

/** `GET /committee/{id}`: a run (re-read: a dead session sets it to `failed`); 404
 * `committee_not_found`. */
export async function fetchCommittee(runId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/committee/{run_id}", { params: { path: { run_id: runId } }, signal }),
  );
}

/**
 * `POST /committee` (202): judges a CV version. 404 `version_not_found`, `posting_not_found`;
 * 409 `version_not_ready`, `committee_in_progress` (`details.run_id`), `profile_required` ; 503.
 */
export async function startCommittee(cvVersionId: string, source?: RunSource) {
  return unwrap(
    await api.POST("/committee", {
      body: { cv_version_id: cvVersionId },
      headers: runSourceHeaders(source),
    }),
  );
}

/** `GET /cv/versions?posting_id=`: the CV versions of a posting (those the committee can judge: the
 * ready ones). */
export async function fetchCvVersions(postingId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/cv/versions", { params: { query: { posting_id: postingId } }, signal }),
  );
}
