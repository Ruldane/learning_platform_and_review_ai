import { http, HttpResponse } from "msw";
import { API } from "./councilApi";
import { settingsApi } from "./settingsApi";

type Body = Record<string, unknown>;

/** Un rapport de `GET /health` : un état par service. */
export const healthReport = (checks: Record<string, [boolean, string]>, status = "ok") => ({
  status,
  checks: Object.fromEntries(
    Object.entries(checks).map(([name, [ok, detail]]) => [name, { ok, detail }]),
  ),
});

/** Une réponse de `GET /health/embedding`. */
export const embeddingOut = (percent: number | null, present = false, detail = "") => ({
  model: "bge-m3",
  present,
  percent: present ? 100 : percent,
  detail,
});

interface OnboardingApiOptions {
  /** Les réglages lus : le premier état du faux serveur (`onboarding_done: false`, compte neuf). */
  settings: Body;
  /** Les clés lues : le premier état, qu'un enregistrement fait évoluer. */
  keys?: Body[];
  models?: object;
  /** Lectures successives de `GET /health` ; la dernière se répète. */
  health?: object[];
  /** Lectures successives de `GET /health/embedding` ; la dernière se répète. */
  embedding?: object[];
  /** Les premières lectures de `GET /settings` qui échouent (500). */
  settingsFailures?: number;
  /** Les premières lectures de `GET /settings/api-keys` qui échouent (500). */
  keysFailures?: number;
  /** Réponse de `POST /settings/api-keys/{provider}/test`. */
  keyTest?: { ok: boolean; message: string };
  /** Réponse à un `PUT /settings` (une 422, par exemple), ou rien pour l'accepter. */
  put?: (body: Body) => Response | undefined;
  /** Réponse à `POST /profile/import`, ou rien pour l'accepter (202). */
  importProfile?: (request: Request) => Response | undefined;
  /** Tient chaque `PUT /settings` jusqu'à l'ouverture de la porte. */
  gate?: Promise<void>;
}

const at = <T>(items: T[], index: number): T => items[Math.min(index, items.length - 1)]!;

const failure = () =>
  HttpResponse.json(
    { error: { code: "internal_error", message: "Le serveur a échoué.", details: null } },
    { status: 500 },
  );

type Reads = Record<"settings" | "keys" | "health" | "embedding", number>;

/** Les clés : lecture (qui peut échouer d'abord), enregistrement et test. */
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
      return HttpResponse.json(options.keyTest ?? { ok: true, message: "Clé valide." });
    }),
  ];
}

/**
 * Faux serveur du premier lancement : réglages en mémoire (une écriture se relit), clés (un
 * enregistrement les fait évoluer), santé, progression du modèle d'embeddings et import du profil.
 * Les compteurs et les corps reçus servent aux assertions ; une clé enregistrée n'est gardée que
 * pour son fournisseur (jamais la valeur).
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
