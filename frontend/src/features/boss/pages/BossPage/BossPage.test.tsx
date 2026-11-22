import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { API } from "@/test/councilApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { BossPage } from "./BossPage";

const program = "programme-test";
const route = `/apprendre/programme/${program}/boss`;
const path = `${API}/boss/programs/${program}`;

it("reprend le besoin modifié et permet d’ouvrir le projet remis", async () => {
  server.use(
    http.get(path, () =>
      HttpResponse.json({
        program_id: program,
        title: "Parcours Python",
        eligible: true,
        attempt: {
          id: "defi-test",
          ide_session_id: "projet-test",
          state: "building",
          started_at: "2026-11-22T13:00:00Z",
          deadline_at: "2026-11-22T13:30:00Z",
          server_time: "2026-11-22T13:10:00Z",
          submitted_at: null,
          proof_recorded: false,
          brief: "Classe les demandes en respectant l’arrivée.",
          client_change: {
            at: "2026-11-22T13:10:00Z",
            requirement: "Les urgences passent en premier.",
          },
          grade: null,
        },
      }),
    ),
  );

  renderRoutes([{ path: "/apprendre/programme/:programId/boss", element: <BossPage /> }], route);
  expect(
    await screen.findByRole("heading", { name: "Changement demandé par le client" }),
  ).toBeVisible();
  expect(screen.getByText("Les urgences passent en premier.")).toBeVisible();
  expect(screen.getByRole("link", { name: "Ouvrir le projet Python" })).toHaveAttribute(
    "href",
    "/code/projet-test",
  );
  expect(screen.getByRole("button", { name: "Remettre les fichiers sauvegardés" })).toBeEnabled();
});
