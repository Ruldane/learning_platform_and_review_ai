import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { API } from "@/test/councilApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { ExpertDebatesPage } from "./ExpertDebatesPage";

const debate = {
  id: "debat-fictif",
  session_id: "session-fictive",
  question: "Quel tri choisir ?",
  status: "completed",
  created_at: "2026-11-22T14:00:00Z",
  judgment: null as string | null,
  speeches: [
    {
      role: "researcher",
      text: "Un résultat [1].",
      citations: [{ index: 1, title: "Une méthode", url: "https://example.test/methode" }],
    },
    {
      role: "practitioner",
      text: "Un exemple [2].",
      citations: [{ index: 2, title: "Un guide", url: "https://example.test/guide" }],
    },
  ],
};
const path = `${API}/expert-debates`;

it("attache les liens au bon expert et sauvegarde le jugement", async () => {
  let current = debate;
  server.use(
    http.get(path, () => HttpResponse.json([current])),
    http.get(`${path}/${debate.id}`, () => HttpResponse.json(current)),
    http.put(`${path}/${debate.id}/judgment`, async ({ request }) => {
      const { text } = (await request.json()) as { text: string };
      current = { ...current, judgment: text };
      return HttpResponse.json(current);
    }),
  );
  const routes = [{ path: "/study/debates/:debateId", element: <ExpertDebatesPage /> }];
  const { user } = renderRoutes(routes, `/study/debates/${debate.id}`);
  const researcher = await screen.findByRole("article", { name: "Chercheur" });
  expect(within(researcher).getByRole("link", { name: /Une méthode/ })).toHaveAttribute(
    "href",
    "https://example.test/methode",
  );
  expect(within(researcher).queryByRole("link", { name: /Un guide/ })).not.toBeInTheDocument();
  await user.type(
    screen.getByRole("textbox", { name: "Ton jugement" }),
    "Je retiens cette méthode.",
  );
  await user.click(screen.getByRole("button", { name: "Enregistrer mon jugement" }));
  expect(await screen.findByText("Jugement enregistré.")).toBeVisible();
  expect(current.judgment).toBe("Je retiens cette méthode.");
});
