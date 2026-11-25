import { http, HttpResponse } from "msw";
import { API } from "./councilApi";
import { settingsApi } from "./settingsApi";

type Body = Record<string, unknown>;

/** A `GET /health` report: one state per service. */
export const healthReport = (checks: Record<string, [boolean, string]>, status = "ok") => ({
  status,
  checks: Object.fromEntries(
    Object.entries(checks).map(([name, [ok, detail]]) => [name, { ok, detail }]),
  ),
});

/** A `GET /health/embedding` response. */
export const embeddingOut = (percent: number | null, present = false, detail = "") => ({
  model: "bge-m3",
  present,
  percent: present ? 100 : percent,
  detail,
});

interface OnboardingApiOptions {
  /** The settings read: the fake server's first state (`onboarding_done: false`, new account). */
  settings: Body;
  /** The keys read: the first state, which a save changes. */
  keys?: Body[];
  models?: object;
  /** Successive reads of `GET /health`; the last one repeats. */
  health?: object[];
  /** Successive reads of `GET /health/embedding`; the last one repeats. */
  embedding?: object[];
  /** The first reads of `GET /settings` that fail (500). */
  settingsFailures?: number;
  /** The first reads of `GET /settings/api-keys` that fail (500). */
  keysFailures?: number;
  /** Response of `POST /settings/api-keys/{provider}/test`. */
  keyTest?: { ok: boolean; message: string };
  /** Response to a `PUT /settings` (a 422, for example), or nothing to accept it. */
  put?: (body: Body) => Response | undefined;
  /** Response to `POST /profile/import`, or nothing to accept it (202). */
  importProfile?: (request: Request) => Response | undefined;
  /** Holds each `PUT /settings` until the gate opens. */
  gate?: Promise<void>;
}

const at = <T>(items: T[], index: number): T => items[Math.min(index, items.length - 1)]!;

const failure = () =>
  HttpResponse.json(
    { error: { code: "internal_error", message: "Le serveur a échoué.", details: null } },
    { status: 500 },
  );

type Reads = Record<"settings" | "keys" | "health" | "embedding", number>;

/** The keys: read (which may fail first), save and test. */
function keyHandlers(
  options: OnboardingApiOptions,
  keys: Body[],
  reads: Reads,
  saved: string[],
  tested: string[],
) {
  return [
    http.get(`${API}/settings/api-keys`, () => {
      reads.keys += 1;
      if (reads.keys <= (options.keysFailures ?? 0)) return failure();
      return HttpResponse.json(keys);
    }),
    http.post(`${API}/settings/api-keys`, async ({ request }) => {
      const { provider, key } = (await request.json()) as { provider: string; key: string };
      saved.push(provider);
      const index = keys.findIndex((entry) => entry.provider === provider);
      const entry = { ...keys[index], source: "ui", last4: key.slice(-4), readable: true };
      keys[index] = entry;
      return HttpResponse.json(entry);
    }),
    http.post(`${API}/settings/api-keys/:provider/test`, ({ params }) => {
      tested.push(String(params.provider));
      return HttpResponse.json(options.keyTest ?? { ok: true, message: "API key is valid." });
    }),
  ];
}

/**
 * Fake first-run server: settings in memory (a write reads back), keys (a save
 * changes them), health, embedding model progress and profile import.
 * The counters and bodies received serve as assertions; a saved key is kept only
 * for its provider (never the value).
 */
export function onboardingApi(options: OnboardingApiOptions) {
  const base = settingsApi({
    settings: options.settings,
    models: options.models,
    put: options.put,
    gate: options.gate,
  });
  const keys = [...(options.keys ?? [])];
  const reads: Reads = { settings: 0, keys: 0, health: 0, embedding: 0 };
  const saved: string[] = [];
  const tested: string[] = [];
  const imports: { contentType: string }[] = [];

  const handlers = [
    http.get(`${API}/settings`, () => {
      reads.settings += 1;
      if (reads.settings <= (options.settingsFailures ?? 0)) return failure();
      return HttpResponse.json(base.state.settings);
    }),
    ...keyHandlers(options, keys, reads, saved, tested),
    http.get(`${API}/health`, () => {
      reads.health += 1;
      return HttpResponse.json(at(options.health ?? [healthReport({})], reads.health - 1));
    }),
    http.get(`${API}/health/embedding`, () => {
      reads.embedding += 1;
      return HttpResponse.json(
        at(options.embedding ?? [embeddingOut(null, true)], reads.embedding - 1),
      );
    }),
    http.post(`${API}/profile/import`, ({ request }) => {
      imports.push({ contentType: request.headers.get("content-type") ?? "" });
      return (
        options.importProfile?.(request) ??
        HttpResponse.json({ session_id: "s1", document_ids: ["d1"] }, { status: 202 })
      );
    }),
    ...base.handlers,
  ];
  return { handlers, state: base.state, puts: base.puts, reads, saved, tested, imports };
}
