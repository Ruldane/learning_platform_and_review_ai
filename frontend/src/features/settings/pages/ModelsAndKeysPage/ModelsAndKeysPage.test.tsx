import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { apiKeysFixture, modelsFixture, settingsFixture } from "../../fixtures";
import type { ApiKeyOut, ModelsOut, SettingsOut } from "../../types";
import { ModelsAndKeysPage } from "./ModelsAndKeysPage";

const BASE = `${apiBaseUrl}/api/v1/settings`;
const SECRET = "sk-ant-secret-1234";

interface Backend {
  settings: SettingsOut;
  keys: ApiKeyOut[];
  models: ModelsOut;
  puts: Record<string, unknown>[];
}

/** Faux back en mémoire : les écritures sont visibles aux lectures suivantes. */
function mockBackend(overrides: Partial<Backend> = {}): Backend {
  const state: Backend = {
    settings: settingsFixture,
    keys: apiKeysFixture,
    models: modelsFixture,
    puts: [],
    ...overrides,
  };
  server.use(
    http.get(BASE, () => HttpResponse.json(state.settings)),
    http.put(BASE, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      state.puts.push(body);
      state.settings = { ...state.settings, ...body, vision_enabled: true } as SettingsOut;
      return HttpResponse.json(state.settings);
    }),
    http.get(`${BASE}/api-keys`, () => HttpResponse.json(state.keys)),
    http.get(`${BASE}/models`, () => HttpResponse.json(state.models)),
  );
  return state;
}

function renderPage() {
  const user = userEvent.setup();
  render(<ModelsAndKeysPage />, { wrapper: createQueryWrapper() });
  return user;
}

const card = (name: string) => within(screen.getByRole("article", { name }));

async function openPage() {
  const user = renderPage();
  await screen.findByRole("heading", { level: 1, name: "Modèles et clés" });
  return user;
}

describe("ModelsAndKeysPage", () => {
  it("affiche le chargement puis les clés, les préréglages et les niveaux", async () => {
    mockBackend();
    renderPage();
    expect(screen.getByRole("status")).toHaveTextContent("Chargement");
    expect(await screen.findByRole("heading", { name: "Clés API" })).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(3);
    expect(card("Anthropic").getByText("•••• 9876")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tout Haiku" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getAllByRole("row")).toHaveLength(5);
  });

  it("enregistre puis teste une clé", async () => {
    const backend = mockBackend();
    server.use(
      http.post(`${BASE}/api-keys`, () => {
        backend.keys = backend.keys.map((k) =>
          k.provider === "anthropic" ? { ...k, last4: "1234" } : k,
        );
        return HttpResponse.json(backend.keys[0]);
      }),
      http.post(`${BASE}/api-keys/anthropic/test`, () =>
        HttpResponse.json({ ok: true, message: "Clé valide." }),
      ),
    );
    const user = await openPage();
    await user.type(screen.getByLabelText("Clé API Anthropic"), SECRET);
    await user.click(card("Anthropic").getByRole("button", { name: "Enregistrer" }));
    expect(await card("Anthropic").findByText("•••• 1234")).toBeInTheDocument();
    expect(screen.getByLabelText("Clé API Anthropic")).toHaveValue("");
    expect(screen.queryByText(new RegExp(SECRET))).not.toBeInTheDocument();
    await user.click(card("Anthropic").getByRole("button", { name: "Tester" }));
    expect(await card("Anthropic").findByRole("status")).toHaveTextContent("Clé valide.");
  });

  it("envoie la clé au bon fournisseur", async () => {
    mockBackend();
    let received: unknown = null;
    server.use(
      http.post(`${BASE}/api-keys`, async ({ request }) => {
        received = await request.json();
        return HttpResponse.json(apiKeysFixture[2]);
      }),
    );
    const user = await openPage();
    await user.type(screen.getByLabelText("Clé API GLM (Z.ai)"), "glm-key-0000");
    await user.click(card("GLM (Z.ai)").getByRole("button", { name: "Enregistrer" }));
    await card("GLM (Z.ai)").findByRole("button", { name: "Enregistrer" });
    expect(received).toEqual({ provider: "glm", key: "glm-key-0000" });
  });

  it("affiche l'erreur du serveur et garde la saisie quand l'enregistrement échoue", async () => {
    mockBackend();
    server.use(
      http.post(`${BASE}/api-keys`, () =>
        HttpResponse.json(
          { error: { code: "invalid_key", message: "La clé est trop courte.", details: null } },
          { status: 422 },
        ),
      ),
    );
    const user = await openPage();
    await user.type(screen.getByLabelText("Clé API Anthropic"), "court");
    await user.click(card("Anthropic").getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("La clé est trop courte.");
    expect(screen.getByLabelText("Clé API Anthropic")).toHaveValue("court");
  });

  it("n'offre la suppression que pour une clé saisie ici", async () => {
    mockBackend();
    await openPage();
    expect(card("Anthropic").getByRole("button", { name: "Supprimer" })).toBeInTheDocument();
    expect(card("OpenAI").queryByRole("button", { name: "Supprimer" })).not.toBeInTheDocument();
    expect(card("OpenAI").getByText("fichier .env")).toBeInTheDocument();
    expect(card("GLM (Z.ai)").queryByRole("button", { name: "Supprimer" })).not.toBeInTheDocument();
  });

  it("supprime une clé saisie ici puis recharge la liste", async () => {
    const backend = mockBackend();
    server.use(
      http.delete(`${BASE}/api-keys/anthropic`, () => {
        backend.keys = backend.keys.map((k) =>
          k.provider === "anthropic" ? { ...k, source: null, last4: null } : k,
        );
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = await openPage();
    await user.click(card("Anthropic").getByRole("button", { name: "Supprimer" }));
    expect(await card("Anthropic").findByText("Aucune clé enregistrée")).toBeInTheDocument();
  });

  it("applique un préréglage : PUT complet sans vision_enabled", async () => {
    const backend = mockBackend();
    const user = await openPage();
    await user.click(screen.getByRole("button", { name: "Tout GLM" }));
    expect(await screen.findByRole("button", { name: "Tout GLM", pressed: true })).toBeVisible();
    expect(backend.puts).toHaveLength(1);
    const body = backend.puts[0]!;
    expect(body.tiers).toEqual(modelsFixture.presets.all_glm);
    expect(body).not.toHaveProperty("vision_enabled");
    expect(body.availability).not.toHaveProperty("weekly_budget_minutes");
    expect(body.brief_time).toBe("07:00");
    expect(body.reminder_delays_days).toEqual([7, 14, 21]);
  });

  it("change un seul niveau et passe en « Personnalisé »", async () => {
    const backend = mockBackend();
    const user = await openPage();
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Modèle (Rapide)" }),
      "claude-sonnet-5-5",
    );
    await waitFor(() =>
      expect(screen.getByText("Personnalisé")).toHaveAttribute("aria-current", "true"),
    );
    expect(backend.puts[0]!.tiers).toEqual({
      ...settingsFixture.tiers,
      rapide: { provider: "anthropic", model: "claude-sonnet-5-5" },
    });
  });

  it("affiche l'erreur du serveur quand l'enregistrement des niveaux échoue", async () => {
    mockBackend();
    server.use(
      http.put(BASE, () =>
        HttpResponse.json(
          { error: { code: "invalid", message: "Réglages refusés.", details: null } },
          { status: 422 },
        ),
      ),
    );
    const user = await openPage();
    await user.click(screen.getByRole("button", { name: "Tout OpenAI" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Réglages refusés.");
  });

  it("avertit quand le niveau vision n'a pas de vision", async () => {
    mockBackend({ settings: { ...settingsFixture, vision_enabled: false } });
    await openPage();
    expect(screen.getByRole("note")).toHaveTextContent("la capture du design du CV est désactivée");
  });

  it("n'avertit pas quand la vision est disponible", async () => {
    mockBackend();
    await openPage();
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });

  it("affiche l'erreur de chargement et permet de réessayer", async () => {
    server.use(
      http.get(BASE, () =>
        HttpResponse.json(
          { error: { code: "boom", message: "Panne du serveur.", details: null } },
          { status: 500 },
        ),
      ),
      http.get(`${BASE}/api-keys`, () => HttpResponse.json(apiKeysFixture)),
      http.get(`${BASE}/models`, () => HttpResponse.json(modelsFixture)),
    );
    const user = renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent("Panne du serveur.");
    mockBackend();
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("heading", { name: "Clés API" })).toBeInTheDocument();
  });

  it("affiche un état vide sans fournisseur", async () => {
    mockBackend({ keys: [], models: { ...modelsFixture, providers: [] } });
    renderPage();
    expect(
      await screen.findByRole("heading", { name: "Aucun fournisseur disponible" }),
    ).toBeInTheDocument();
  });
});
