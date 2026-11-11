import { http, HttpResponse } from "msw";
import { apiBaseUrl } from "@/shared/api/client";
import type {
  DocumentOut,
  MapResponse,
  MemoryItemDetail,
  MemoryItemOut,
  SearchResponse,
  StatsOut,
} from "./types";

/** Données de test de la feature (réponses typiques du back) ; jamais importées par le code de l'application. */
export const API = `${apiBaseUrl}/api/v1`;
const NOW = "2026-11-11T10:00:00Z";

export function itemOut(overrides: Partial<MemoryItemOut> = {}): MemoryItemOut {
  return {
    id: "i1",
    kind: "acquis",
    title: "Attention",
    text: "Le mécanisme d'attention pondère les jetons.",
    tags: ["nlp"],
    evidence: [],
    created_by: "archivist",
    created_at: NOW,
    updated_at: NOW,
    status: "active",
    indexed: true,
    level: "declare",
    lang: "fr",
    reason: "Document « Cours NLP » marqué « déjà appris ».",
    session_id: "s1",
    source_id: null,
    ...overrides,
  };
}

export function itemDetail(overrides: Partial<MemoryItemDetail> = {}): MemoryItemDetail {
  const base = itemOut();
  return {
    ...base,
    chunks: [{ id: "c1", ordinal: 1, text: "Le mécanisme d'attention.", token_count: 120 }],
    neighbors: [{ item_id: "i2", title: "Transformeurs", kind: "document", score: 0.71 }],
    writes: [
      {
        id: "w1",
        item_id: base.id,
        item_title: base.title,
        action: "create",
        author: "archivist",
        session_id: "s1",
        reason: "Document « Cours NLP » marqué « déjà appris ».",
        created_at: NOW,
      },
    ],
    ...overrides,
  };
}

export function statsOut(overrides: Partial<StatsOut> = {}): StatsOut {
  return {
    by_kind: { document: 3, acquis: 5, lecon: 2, source: 1, offre: 0, decision: 1 },
    dashboard_url: "http://localhost:6333/dashboard",
    dimension: 1024,
    last_write: {
      id: "w1",
      item_id: "i1",
      item_title: "Attention",
      action: "create",
      author: "archivist",
      session_id: null,
      reason: null,
      created_at: NOW,
    },
    pending_decisions: 1,
    reindex: { status: "idle", done: 0, total: 0, error: null },
    total_chunks: 48,
    total_items: 12,
    unindexed_items: 0,
    vectorize_limit: 5_000_000,
    vectorize_share: 0.25,
    ...overrides,
  };
}

export function documentOut(overrides: Partial<DocumentOut> = {}): DocumentOut {
  return {
    id: "d1",
    name: "cours.pdf",
    source_kind: "pdf",
    status: "indexed",
    error: null,
    learned: false,
    item_id: "i2",
    size_bytes: 1200,
    url: null,
    created_at: NOW,
    updated_at: NOW,
    ...overrides,
  };
}

export const mapOut: MapResponse = {
  method: "pca",
  truncated: false,
  points: [
    { item_id: "i1", title: "Attention", kind: "acquis", x: 0.2, y: -0.3 },
    { item_id: "i2", title: "Cours NLP", kind: "document", x: -0.5, y: 0.4 },
  ],
};

export const searchOut: SearchResponse = {
  agent_text: "<<<CONTENU_NON_FIABLE>>>Cours NLP<<<FIN_CONTENU_NON_FIABLE>>>",
  hits: [
    {
      chunk_id: "c9",
      item_id: "i2",
      kind: "document",
      title: "Cours NLP",
      text: "L'attention relie chaque jeton aux autres.",
      score: 0.834,
      created_by: "user",
    },
  ],
};

/** Faux back en mémoire : les lectures reflètent les écritures ; `requests` garde chaque appel. */
export interface MemoryBackend {
  items: MemoryItemOut[];
  stats: StatsOut;
  map: MapResponse;
  documents: DocumentOut[];
  requests: { method: string; url: URL }[];
  /** Écritures reçues, dans l'ordre (le corps JSON, ou `null`). */
  writes: { method: string; path: string; body: unknown }[];
}

export function memoryBackend(init: Partial<MemoryBackend> = {}): MemoryBackend {
  return {
    items: [itemOut(), itemOut({ id: "i3", title: "Backpropagation", kind: "lecon", level: null })],
    stats: statsOut(),
    map: mapOut,
    documents: [],
    requests: [],
    writes: [],
    ...init,
  };
}

/** Lectures du faux back (liste filtrée par statut et type, détail, statistiques, carte, documents). */
export function readHandlers(b: MemoryBackend) {
  const seen = (request: Request) => {
    b.requests.push({ method: request.method, url: new URL(request.url) });
  };
  return [
    http.get(`${API}/memory/items`, ({ request }) => {
      seen(request);
      const q = new URL(request.url).searchParams;
      const status = q.get("status") ?? "active";
      const kind = q.get("kind");
      const items = b.items.filter((i) => i.status === status && (!kind || i.kind === kind));
      return HttpResponse.json({ items, total: items.length });
    }),
    http.get(`${API}/memory/items/:id`, ({ request, params }) => {
      seen(request);
      const item = b.items.find((i) => i.id === params.id);
      if (!item) {
        const error = {
          code: "memory_item_not_found",
          message: "Élément introuvable.",
          details: null,
        };
        return HttpResponse.json({ error }, { status: 404 });
      }
      return HttpResponse.json(itemDetail(item));
    }),
    http.get(`${API}/memory/stats`, ({ request }) => {
      seen(request);
      return HttpResponse.json(b.stats);
    }),
    http.get(`${API}/memory/map`, ({ request }) => {
      seen(request);
      return HttpResponse.json(b.map);
    }),
    http.get(`${API}/documents`, ({ request }) => {
      seen(request);
      return HttpResponse.json(b.documents);
    }),
  ];
}

/** Réponse d'erreur au format du back. */
export const apiError = (code: string, message: string, status = 400) =>
  HttpResponse.json({ error: { code, message, details: null } }, { status });

/** Écritures du faux back : elles sont notées dans `writes` et modifient `items` comme le vrai back. */
export function writeHandlers(b: MemoryBackend) {
  const note = async (request: Request) => {
    const text = await request.text();
    const path = new URL(request.url).pathname.replace("/api/v1", "");
    b.writes.push({ method: request.method, path, body: text ? JSON.parse(text) : null });
    return text ? (JSON.parse(text) as Record<string, unknown>) : {};
  };
  return [
    http.post(`${API}/memory/items`, async ({ request }) => {
      const body = await note(request);
      return HttpResponse.json(itemOut({ id: "new1", ...body } as Partial<MemoryItemOut>), {
        status: 201,
      });
    }),
    http.patch(`${API}/memory/items/:id`, async ({ request, params }) => {
      const body = await note(request);
      b.items = b.items.map((i) => (i.id === params.id ? { ...i, ...body } : i));
      return HttpResponse.json(b.items.find((i) => i.id === params.id));
    }),
    http.delete(`${API}/memory/items/:id`, async ({ request, params }) => {
      await note(request);
      b.items = b.items.filter((i) => i.id !== params.id);
      return new HttpResponse(null, { status: 204 });
    }),
    http.post(`${API}/memory/items/:id/merge`, async ({ request, params }) => {
      const body = (await note(request)) as { other_ids: string[] };
      b.items = b.items.filter((i) => !body.other_ids.includes(i.id));
      return HttpResponse.json(b.items.find((i) => i.id === params.id));
    }),
    http.post(`${API}/memory/reindex`, async ({ request }) => {
      await note(request);
      return HttpResponse.json(
        { status: "queued", done: 0, total: 5, error: null },
        { status: 202 },
      );
    }),
    http.post(`${API}/memory/search`, async ({ request }) => {
      await note(request);
      return HttpResponse.json(searchOut);
    }),
  ];
}
