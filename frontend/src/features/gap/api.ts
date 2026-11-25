import { api, apiBaseUrl } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";
import { runSourceHeaders, type RunSource } from "@/shared/lib/runSource";
import { fetchSession } from "@/shared/realtime/sessionApi";

const postingPath = (postingId: string) => ({ params: { path: { posting_id: postingId } } });

/** `GET /postings`: the postings, newest first. */
export async function fetchPostings(signal?: AbortSignal) {
  return unwrap(await api.GET("/postings", { signal }));
}

/**
 * `POST /postings`: 201 posting created, 200 same link or same text (`created` false). Errors 422
 * `posting_source`, `posting_unreadable`, `posting_too_short`, `invalid_url`, `url_forbidden`.
 */
export async function createPosting(source: { url: string } | { text: string }, provider?: RunSource) {
  return unwrap(await api.POST("/postings", { body: source, headers: runSourceHeaders(provider) }));
}

/** `GET /postings/{id}`: the posting, its analysis and its duplicates; 404 `posting_not_found`. */
export async function fetchPosting(postingId: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/postings/{posting_id}", { ...postingPath(postingId), signal }));
}

/** `DELETE /postings/{id}` (204) ; 409 `review_in_progress`. */
export async function deletePosting(postingId: string): Promise<void> {
  unwrap(await api.DELETE("/postings/{posting_id}", postingPath(postingId)));
}

/** `POST /postings/{id}/distinct` (204) : « ces deux offres sont distinctes ». */
export async function markDistinct(postingId: string, otherId: string): Promise<void> {
  unwrap(
    await api.POST("/postings/{posting_id}/distinct", {
      ...postingPath(postingId),
      body: { other_id: otherId },
    }),
  );
}

/** `GET /postings/{id}/gap`: the gap table and its score. */
export async function fetchGap(postingId: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/postings/{posting_id}/gap", { ...postingPath(postingId), signal }));
}

/** `POST /postings/{id}/gap` (202) : relance l'analyse ; 409 `gap_in_progress`. */
export async function relaunchGap(postingId: string, provider?: RunSource) {
  return unwrap(await api.POST("/postings/{posting_id}/gap", {
    ...postingPath(postingId),
    headers: runSourceHeaders(provider),
  }));
}

/**
 * `POST /postings/{id}/gap/plan` (202): « gap » replanning for the chosen skills.
 * 409 `no_program`, 409 `replan_open` (`details.session_id`), 422 `skills.N`.
 */
export async function planGap(
  postingId: string,
  body: components["schemas"]["PlanGapIn"],
  provider?: RunSource,
) {
  return unwrap(
    await api.POST("/postings/{posting_id}/gap/plan", {
      ...postingPath(postingId),
      headers: runSourceHeaders(provider),
      body,
    }),
  );
}

export async function fetchTargetPrograms(signal?: AbortSignal) {
  const programs = unwrap(await api.GET("/programs", { signal }));
  return programs.filter((program) => program.status === "validated");
}

/**
 * `GET /applications/check?posting_id=`: this posting's application (`own`), the cards that
 * resemble it (`alerts`) and plain notes (`info`). Read only, no side effects.
 */
export async function fetchApplicationCheck(postingId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/applications/check", { params: { query: { posting_id: postingId } }, signal }),
  );
}

/**
 * `POST /applications` from a posting: the card takes over company, role, link and text of
 * the posting. 409 `application_exists` (`details.application_id`) or `application_duplicate`
 * (`details.alerts`); `distinctFrom`: the cards January confirmed as « autre poste ».
 */
export async function createApplicationFromPosting(postingId: string, distinctFrom: string[]) {
  return unwrap(
    await api.POST("/applications", {
      body: {
        posting_id: postingId,
        status: "to_apply",
        ...(distinctFrom.length > 0 ? { distinct_from: distinctFrom } : {}),
      },
    }),
  );
}

/** `GET /gap/top-missing`: the 10 skills that are most often missing. */
export async function fetchTopMissing(signal?: AbortSignal) {
  return unwrap(await api.GET("/gap/top-missing", { signal }));
}

/** The program targeted by a replanning session (its subject), or `null`. */
export async function programOfSession(sessionId: string): Promise<string | null> {
  const session = await fetchSession(sessionId);
  return session.subject_type === "program" ? session.subject_id : null;
}

/**
 * `POST /postings/{id}/gap/validate` (202): « Je les maîtrise déjà », a « Valider mes
 * acquis » and its quiz. 409 `no_program`, 409 `week_full`, 422 `skills.N`.
 */
export async function validateGap(postingId: string, skills: string[], provider?: RunSource) {
  return unwrap(
    await api.POST("/postings/{posting_id}/gap/validate", {
      ...postingPath(postingId),
      headers: runSourceHeaders(provider),
      body: { skills },
    }),
  );
}

/** `GET /cv/versions?posting_id=`: the CVs generated for this posting, newest first. */
export async function fetchPostingCvs(postingId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/cv/versions", { params: { query: { posting_id: postingId } }, signal }),
  );
}

/** The PDF of a generated CV (the `CV_….pdf` name comes from the server header). */
export const cvPdfUrl = (versionId: string) =>
  `${apiBaseUrl}/api/v1/cv/versions/${versionId}/pdf`;
