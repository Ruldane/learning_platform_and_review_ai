import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { DossierPage } from "./DossierPage";

const dossier = {
  id: "d1",
  program_id: "p1",
  chapter: "Bases de données",
  issue: {
    repository: "orga-fictive/biblio",
    number: 7,
    title: "Tests pandas",
    body: "Cas limites",
    url: "https://github.com/orga-fictive/biblio/issues/7",
    skills: ["pandas"],
  },
  status: "draft",
  base: "main",
};
const api = `${apiBaseUrl}/api/v1/contributions/d1`;

it("demande une confirmation explicite avant de préparer le lien GitHub", async () => {
  const requests: unknown[] = [];
  server.use(
    http.get(api, () => HttpResponse.json(dossier)),
    http.post(`${api}/publication`, async ({ request }) => {
      requests.push(await request.json());
      return HttpResponse.json({
        ...dossier,
        status: "confirmed",
        publication_url: "https://github.com/orga-fictive/biblio/compare/main...camille:tests",
      });
    }),
  );
  const { user } = renderRoutes(
    [{ path: "/skills/contributions/:id", element: <DossierPage /> }],
    "/skills/contributions/d1",
  );
  await user.type(await screen.findByLabelText("GitHub account"), "camille");
  await user.type(screen.getByLabelText("Branch to propose"), "tests");
  await user.type(screen.getByLabelText("Pull request description"), "Ajout de tests");
  const prepare = screen.getByRole("button", { name: "Prepare the pull request" });
  expect(prepare).toHaveAttribute("aria-disabled", "true");
  await user.click(prepare);
  expect(requests).toEqual([]);
  expect(screen.queryByRole("link", { name: "Open GitHub to publish" })).toBeNull();

  await user.click(screen.getByRole("checkbox", { name: "I confirm the text and branches." }));
  await user.click(prepare);
  expect(await screen.findByRole("link", { name: "Open GitHub to publish" })).toHaveAttribute(
    "href",
    "https://github.com/orga-fictive/biblio/compare/main...camille:tests",
  );
  expect(requests).toEqual([
    {
      confirm: true,
      author: "camille",
      head: "tests",
      title: "Tests pandas",
      body: "Ajout de tests",
    },
  ]);
});
