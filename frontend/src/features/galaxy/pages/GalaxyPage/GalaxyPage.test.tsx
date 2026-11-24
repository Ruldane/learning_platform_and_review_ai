import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, expect, it, vi } from "vitest";
import { API } from "@/test/councilApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { GalaxyPage } from "./GalaxyPage";

const route = "/skills/galaxy";
const routes = [{ path: route, element: <GalaxyPage /> }];
const empty = { nodes: [], edges: [], target_label: null };

afterEach(() => vi.restoreAllMocks());

it("rend un état vide sans projection de données inventées", async () => {
  server.use(http.get(`${API}/galaxy`, () => HttpResponse.json(empty)));
  renderRoutes(routes, route);
  expect(await screen.findByText("Aucune compétence ni note active à afficher.")).toBeVisible();
});

it("ouvre le chapitre lié depuis la sélection au clavier", async () => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  server.use(
    http.get(`${API}/galaxy`, () =>
      HttpResponse.json({
        nodes: [
          {
            id: "skill:python",
            title: "Python",
            kind: "skill",
            level: "declared",
            gap: 2,
            domain: "Données",
            action: { kind: "lesson", ref: "lecon-test" },
          },
        ],
        edges: [],
        target_label: "Programme fictif",
      }),
    ),
  );
  const { user } = renderRoutes(routes, route);
  const node = await screen.findByRole("button", { name: "Python Compétence" });
  node.focus();
  await user.keyboard("{Enter}");
  expect(node).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByText("Écart de 2 niveaux")).toBeVisible();
  expect(screen.getByRole("link", { name: "Ouvrir le chapitre" })).toHaveAttribute(
    "href",
    "/learn/lessons/lecon-test",
  );
});

it("distingue les homonymes et garde le sujet hors de l’adresse de training", async () => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  server.use(
    http.get(`${API}/galaxy`, () =>
      HttpResponse.json({
        ...empty,
        nodes: [
          {
            id: "skill:1",
            title: "Python",
            kind: "skill",
            action: { kind: "training", ref: "identifiant" },
          },
          { id: "note:1", title: "Python", kind: "note", action: { kind: "note", ref: "note" } },
        ],
      }),
    ),
  );
  const { user } = renderRoutes(routes, route);
  const skill = await screen.findByRole("button", { name: "Python Compétence" });
  expect(screen.getByRole("button", { name: "Python Note du Cerveau" })).toBeVisible();
  await user.click(skill);
  expect(screen.getByRole("link", { name: "Ouvrir l’entraînement" })).toHaveAttribute(
    "href",
    "/study/training?skill=identifiant",
  );
});
