import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import { fetchSession } from "@/shared/realtime/sessionApi";

const postingPath = (postingId: string) => ({ params: { path: { posting_id: postingId } } });

/** `GET /postings` : les offres, la plus récente d'abord. */
export async function fetchPostings(signal?: AbortSignal) {
  return unwrap(await api.GET("/postings", { signal }));
}

/**
 * `POST /postings` : 201 offre créée, 200 même lien ou même texte (`created` faux). Erreurs 422
 * `posting_source`, `posting_unreadable`, `posting_too_short`, `invalid_url`, `url_forbidden`.
 */
export async function createPosting(source: { url: string } | { text: string }) {
  return unwrap(await api.POST("/postings", { body: source }));
}

/** `GET /postings/{id}` : l'offre, son analyse et ses doublons ; 404 `posting_not_found`. */
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

/** `GET /postings/{id}/gap` : le tableau d'écarts et son score. */
export async function fetchGap(postingId: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/postings/{posting_id}/gap", { ...postingPath(postingId), signal }));
}

/** `POST /postings/{id}/gap` (202) : relance l'analyse ; 409 `gap_in_progress`. */
export async function relaunchGap(postingId: string) {
  return unwrap(await api.POST("/postings/{posting_id}/gap", postingPath(postingId)));
}

/**
 * `POST /postings/{id}/gap/plan` (202) : replanification « gap » pour les compétences choisies.
 * 409 `no_program`, 409 `replan_open` (`details.session_id`), 422 `skills.N`.
 */
export async function planGap(postingId: string, skills: string[]) {
  return unwrap(
    await api.POST("/postings/{posting_id}/gap/plan", {
      ...postingPath(postingId),
      body: { skills },
    }),
  );
}

/**
 * `GET /applications/check?posting_id=` : la candidature de cette offre (`own`), les fiches qui lui
 * ressemblent (`alerts`) et les simples informations (`info`). Lecture seule, sans effet.
 */
export async function fetchApplicationCheck(postingId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/applications/check", { params: { query: { posting_id: postingId } }, signal }),
  );
}

/**
 * `POST /applications` depuis une offre : la fiche reprend entreprise, poste, lien et texte de
 * l'offre. 409 `application_exists` (`details.application_id`) ou `application_duplicate`
 * (`details.alerts`) ; `distinctFrom` : les fiches que January a confirmées « autre poste ».
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

/** `GET /gap/top-missing` : les 10 compétences qui manquent le plus souvent. */
export async function fetchTopMissing(signal?: AbortSignal) {
  return unwrap(await api.GET("/gap/top-missing", { signal }));
}

/** Le programme visé par une session de replanification (son sujet), ou `null`. */
export async function programOfSession(sessionId: string): Promise<string | null> {
  const session = await fetchSession(sessionId);
  return session.subject_type === "program" ? session.subject_id : null;
}
