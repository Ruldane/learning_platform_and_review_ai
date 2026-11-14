import { http, HttpResponse } from "msw";
import { API, sessionOut } from "./councilApi";
import { apiError } from "./councilHarness";
import {
  emptyProfile,
  modificationOut,
  profileOut,
  reviewOut,
  templateOut,
  templateSummary,
  versionOut,
} from "./cvFixtures";

type Over = Record<string, unknown>;

export * from "./cvFixtures";

type Reply = (request: Request) => Response | Promise<Response>;

interface CvApi {
  /** Lectures successives de `GET /profile` ; la dernière se répète. */
  profiles?: Over[];
  profileVersions?: Over[];
  profile?: () => Response;
  putProfile?: Reply;
  importProfile?: Reply;
  templates?: Over[][];
  /** Remplace la lecture de la liste des modèles (une panne, par exemple). */
  templateList?: () => Response;
  template?: Over[];
  templateRead?: () => Response;
  createTemplate?: Reply;
  documents?: Over[];
  reviews?: Over[];
  review?: () => Response;
  startReview?: Reply;
  patchModification?: Reply;
  patchBulk?: Reply;
  generate?: Reply;
  versions?: Over[];
  /** Remplace la lecture de la liste des versions (une panne, par exemple). */
  versionList?: () => Response;
  version?: Over;
  postings?: Over[];
}

const at = <T>(items: T[], index: number): T => items[Math.min(index, items.length - 1)]!;

/** Un refus du back au format d'erreur. */
export const refusal = (status: number, code: string, message: string, details: unknown = null) =>
  HttpResponse.json(apiError(code, message, details), { status });

const newState = () => ({
  puts: [] as unknown[],
  /** Le `content-type` de chaque envoi : jsdom ne relit pas un corps multipart. */
  imports: [] as string[],
  creates: [] as string[],
  patches: [] as { id: string; body: unknown }[],
  bulks: [] as unknown[],
  generates: [] as unknown[],
  activated: [] as string[],
  starts: 0,
  reads: { profile: 0, templates: 0, template: 0, review: 0 },
});

type State = ReturnType<typeof newState>;

function profileRoutes(api: CvApi, state: State) {
  const profiles = api.profiles ?? [emptyProfile];
  return [
    http.get(
      `${API}/profile`,
      () => api.profile?.() ?? HttpResponse.json(at(profiles, state.reads.profile++)),
    ),
    http.put(`${API}/profile`, async ({ request }) => {
      state.puts.push(await request.clone().json());
      return (
        api.putProfile?.(request) ??
        HttpResponse.json(profileOut({ version: 3, status: "validated", source: "january" }))
      );
    }),
    http.post(`${API}/profile/import`, async ({ request }) => {
      state.imports.push(request.headers.get("content-type") ?? "");
      return (
        api.importProfile?.(request) ??
        HttpResponse.json({ session_id: "s1", document_ids: ["d1"] }, { status: 202 })
      );
    }),
    http.get(`${API}/profile/versions`, () =>
      HttpResponse.json(
        api.profileVersions ?? [
          { version: 2, status: "draft", source: "archivist", created_at: "2026-11-10T10:00:00Z" },
        ],
      ),
    ),
  ];
}

function templateRoutes(api: CvApi, state: State) {
  const lists = api.templates ?? [[templateSummary()]];
  const reads = api.template ?? [templateOut()];
  return [
    http.get(
      `${API}/cv/templates`,
      () => api.templateList?.() ?? HttpResponse.json(at(lists, state.reads.templates++)),
    ),
    http.get(
      `${API}/cv/templates/t1`,
      () => api.templateRead?.() ?? HttpResponse.json(at(reads, state.reads.template++)),
    ),
    http.post(`${API}/cv/templates`, async ({ request }) => {
      state.creates.push(request.headers.get("content-type") ?? "");
      return (
        api.createTemplate?.(request) ??
        HttpResponse.json({ template_id: "t1", session_id: "d1" }, { status: 202 })
      );
    }),
    http.post(`${API}/cv/templates/:id/activate`, ({ params }) => {
      state.activated.push(String(params.id));
      return new HttpResponse(null, { status: 204 });
    }),
    http.get(`${API}/documents`, () => HttpResponse.json(api.documents ?? [])),
  ];
}

function reviewRoutes(api: CvApi, state: State) {
  const reviews = api.reviews ?? [reviewOut()];
  return [
    http.post(`${API}/cv/reviews`, ({ request }) => {
      state.starts += 1;
      return (
        api.startReview?.(request) ??
        HttpResponse.json({ review_id: "rv1", session_id: "r1" }, { status: 202 })
      );
    }),
    http.get(
      `${API}/cv/reviews/rv1`,
      () => api.review?.() ?? HttpResponse.json(at(reviews, state.reads.review++)),
    ),
    http.patch(`${API}/cv/modifications/:id`, async ({ request, params }) => {
      const body = await request.clone().json();
      state.patches.push({ id: String(params.id), body });
      return (
        api.patchModification?.(request) ??
        HttpResponse.json(modificationOut(String(params.id), { status: "accepted" }))
      );
    }),
    http.patch(`${API}/cv/reviews/rv1/modifications`, async ({ request }) => {
      state.bulks.push(await request.clone().json());
      return api.patchBulk?.(request) ?? HttpResponse.json({ updated: 1, skipped: ["m2"] });
    }),
    http.post(`${API}/cv/reviews/rv1/generate`, async ({ request }) => {
      state.generates.push(
        await request
          .clone()
          .json()
          .catch(() => null),
      );
      return api.generate?.(request) ?? HttpResponse.json({ version_id: "v1" }, { status: 202 });
    }),
  ];
}

function versionRoutes(api: CvApi) {
  return [
    http.get(
      `${API}/cv/versions`,
      () => api.versionList?.() ?? HttpResponse.json(api.versions ?? [versionOut()]),
    ),
    http.get(`${API}/cv/versions/:id`, () => HttpResponse.json(api.version ?? versionOut())),
    http.get(`${API}/postings`, () =>
      HttpResponse.json(
        api.postings ?? [
          { id: "p1", title: "Ingénieure données", company: "Société Fictive", status: "ready" },
        ],
      ),
    ),
    http.get(`${API}/sessions/:id`, ({ params }) => {
      const id = String(params.id);
      const graph = id === "r1" ? "cv_review" : "cv_capture";
      return HttpResponse.json(sessionOut(id, "running", { graph, subject_type: "cv" }));
    }),
  ];
}

/**
 * Les routes du profil, des modèles, des revues et des versions de CV. `state` garde les corps
 * reçus (profil enregistré, envois, décisions, générations) et le nombre de lectures.
 */
export function cvApi(api: CvApi = {}) {
  const state = newState();
  const handlers = [
    ...profileRoutes(api, state),
    ...templateRoutes(api, state),
    ...reviewRoutes(api, state),
    ...versionRoutes(api),
  ];
  return { state, handlers };
}
