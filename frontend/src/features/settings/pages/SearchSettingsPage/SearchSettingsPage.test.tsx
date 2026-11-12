import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { searchUsageFixture, settingsFixture } from "../../fixtures";
import { SearchSettingsPage } from "./SearchSettingsPage";

const API = `${apiBaseUrl}/api/v1`;
const stored = {
  ...settingsFixture,
  excluded_domains: ["pinterest.com"],
  preferred_domains: ["wikipedia.org"],
  availability: { ...settingsFixture.availability!, weekday_minutes: 90 },
};

function setup(options: { usage?: unknown; put?: (body: unknown) => Response } = {}) {
  const puts: unknown[] = [];
  server.use(
    http.get(`${API}/settings`, () => HttpResponse.json(stored)),
    http.get(`${API}/research/usage`, () => HttpResponse.json(options.usage ?? searchUsageFixture)),
    http.put(`${API}/settings`, async ({ request }) => {
      const body = await request.json();
      puts.push(body);
      return options.put?.(body) ?? HttpResponse.json({ ...stored, ...(body as object) });
    }),
  );
  const view = renderRoutes(
    [{ path: "/reglages/recherche", element: <SearchSettingsPage /> }],
    "/reglages/recherche",
  );
  return { puts, ...view };
}

const group = (name: string) => within(screen.getByRole("group", { name }));

describe("SearchSettingsPage", () => {
  it("saves languages and domains with a full PUT", async () => {
    const { puts, user } = setup();
    await user.click(await screen.findByRole("checkbox", { name: "Espagnol" }));
    await user.type(group("Domaines exclus").getByLabelText("Ajouter un domaine"), "example.com");
    await user.click(group("Domaines exclus").getByRole("button", { name: "Ajouter" }));
    expect(puts).toEqual([]); // rien n'est enregistré avant le bouton
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));

    expect(await screen.findByText("Réglages enregistrés.")).toBeInTheDocument();
    expect(puts).toHaveLength(1);
    expect(puts[0]).toMatchObject({
      search_languages: ["fr", "en", "es"],
      excluded_domains: ["pinterest.com", "example.com"],
      preferred_domains: ["wikipedia.org"],
      search_provider_order: ["searxng", "brave"],
      search_max_queries: 12,
      search_max_pages: 30,
      tiers: settingsFixture.tiers,
      availability: { weekday_minutes: 90 },
      brief_time: "07:00",
    });
    expect(puts[0]).not.toHaveProperty("vision_enabled");
  });

  it("saves edited caps and a reordered provider list", async () => {
    const { puts, user } = setup();
    const queries = await screen.findByLabelText("Requêtes par session");
    await user.clear(queries);
    await user.type(queries, "20");
    await user.click(screen.getByRole("button", { name: "Descendre SearXNG" }));
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    await waitFor(() => expect(puts).toHaveLength(1));
    expect(puts[0]).toMatchObject({
      search_max_queries: 20,
      search_provider_order: ["brave", "searxng"],
    });
  });

  it("refuses to save an invalid cap, even with Enter, and keeps the error", async () => {
    const { puts, user } = setup();
    const queries = await screen.findByLabelText("Requêtes par session");
    await user.clear(queries);
    await user.type(queries, "60{Enter}"); // « 6 » est valide, « 60 » ne l'est pas
    expect(puts).toEqual([]);
    expect(queries).toHaveValue(60);
    expect(screen.getByRole("alert")).toHaveTextContent("Entre 1 et 50.");
    expect(screen.getByRole("button", { name: "Enregistrer" })).toBeDisabled();
    expect(screen.queryByText("Réglages enregistrés.")).not.toBeInTheDocument();

    await user.clear(queries);
    await user.type(queries, "20");
    expect(screen.getByRole("button", { name: "Enregistrer" })).toBeEnabled();
  });

  it("keeps the input and shows the error when saving fails, then saves on retry", async () => {
    let failing = true;
    const { puts, user } = setup({
      put: () =>
        failing
          ? HttpResponse.json(
              { error: { code: "boom", message: "Panne.", details: null } },
              { status: 500 },
            )
          : HttpResponse.json(stored),
    });
    await user.click(await screen.findByRole("checkbox", { name: "Allemand" }));
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Panne.");
    expect(screen.getByRole("checkbox", { name: "Allemand" })).toBeChecked();
    expect(screen.queryByText("Réglages enregistrés.")).not.toBeInTheDocument();

    failing = false;
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByText("Réglages enregistrés.")).toBeInTheDocument();
    expect(puts).toHaveLength(2);
  });

  it("disables saving until something changes", async () => {
    const { user } = setup();
    const save = await screen.findByRole("button", { name: "Enregistrer" });
    expect(save).toBeDisabled();
    await user.click(screen.getByRole("checkbox", { name: "Italien" }));
    expect(save).toBeEnabled();
    await user.click(screen.getByRole("checkbox", { name: "Italien" }));
    expect(save).toBeDisabled();
  });

  it("greys Brave without a key", async () => {
    setup({ usage: { brave: { has_key: false, used: 0, cap: 900, month: "2026-11" } } });
    expect(
      await screen.findByText("Ajoutez une clé Brave dans Modèles et clés"),
    ).toBeInTheDocument();
    expect(screen.getByText("Brave inactif (aucune clé)")).toBeInTheDocument();
    for (const button of screen.getAllByRole("button", { name: /^(Monter|Descendre) / })) {
      expect(button).toBeDisabled();
    }
  });

  it("shows the Brave usage of the month", async () => {
    setup();
    expect(await screen.findByText("120 / 900 requêtes en novembre 2026")).toBeInTheDocument();
  });

  it("shows an error with a retry when the usage cannot be read", async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/settings`, () => HttpResponse.json(stored)),
      http.get(`${API}/research/usage`, () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json(
              { error: { code: "boom", message: "Panne.", details: null } },
              { status: 500 },
            )
          : HttpResponse.json(searchUsageFixture);
      }),
    );
    const { user } = renderRoutes([{ path: "/r", element: <SearchSettingsPage /> }], "/r");
    expect(await screen.findByText("Panne.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("button", { name: "Enregistrer" })).toBeInTheDocument();
  });

  it("shows a loading state first", () => {
    setup();
    expect(screen.getByText("Chargement des réglages de recherche…")).toBeInTheDocument();
  });
});
