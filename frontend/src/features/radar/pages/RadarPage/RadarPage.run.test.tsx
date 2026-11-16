import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { councilEvents } from "@/test/councilEvents";
import { offerOut, radarRun, radarSession, trendOut } from "@/test/radarApi";
import { openStream, renderRadar } from "@/test/radarHarness";
import { sessionOut } from "@/test/councilApi";
import { apiError } from "@/test/councilHarness";
import { HttpResponse } from "msw";
import { RadarPage } from "./RadarPage";

const setup = (api: Parameters<typeof renderRadar>[1] = {}, path?: string) =>
  renderRadar((createSocket) => <RadarPage createSocket={createSocket} />, api, path);

const RUNNING = radarRun("r9", {
  status: "running",
  finished_at: null,
  ranking: [],
  offers: [],
  blocked_domains: [],
});

describe("RadarPage : lancer et suivre un relevé", () => {
  it("launches a first run from the proposed values, follows it live, then shows the result", async () => {
    const { user, state, finish, sockets, router } = setup();
    expect(
      await screen.findByText("Aucun relevé pour l'instant", { selector: "h2" }),
    ).toBeVisible();
    expect(screen.getByLabelText("Poste visé")).toHaveValue("Data engineer");
    expect(screen.getByLabelText("Zone")).toHaveValue("France");

    await user.clear(screen.getByLabelText("Poste visé"));
    await user.type(screen.getByLabelText("Poste visé"), "Analyste données");
    await user.click(screen.getByRole("button", { name: "Lancer un relevé" }));

    expect(state.bodies).toEqual([{ role: "Analyste données", zone: "France" }]);
    await waitFor(() => expect(router.state.location.pathname).toBe("/carriere/radar/new1"));
    expect(await screen.findByRole("heading", { name: "Relevé en cours" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Relevé en cours…" })).toBeDisabled();

    const stream = await openStream(sockets, "sess-new1");
    const events = councilEvents("sess-new1");
    stream.push(events.message("m1", "J'ai trouvé 52 pages d'offres à lire.", "scout"));
    stream.push(events.message("m2", "Je classe les compétences demandées.", "analyst"));
    expect(await screen.findByText("J'ai trouvé 52 pages d'offres à lire.")).toBeVisible();
    expect(screen.getByText("Je classe les compétences demandées.")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Compétences les plus demandées" })).toBeNull();

    finish("new1", {
      ranking: [trendOut("SQL", 1, 0.62)],
      read_count: 47,
      blocked_count: 6,
      analyzed: 41,
    });
    stream.push(events.completed());
    expect(await screen.findByText("47 offres lues · 6 bloquées · 41 analysées")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Compétences les plus demandées" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Lancer un relevé" })).toBeEnabled();
  });

  it("follows a run that is already in progress: found by its subject, then its result", async () => {
    const { finish, sockets, router } = setup({
      runs: [RUNNING],
      sessions: [sessionOut("sess-r9", "running", radarSession("r9"))],
    });
    await waitFor(() => expect(router.state.location.pathname).toBe("/carriere/radar/r9"));
    expect(await screen.findByRole("heading", { name: "Relevé en cours" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Relevé en cours…" })).toBeDisabled();

    const stream = await openStream(sockets, "sess-r9");
    finish("r9", { ranking: [trendOut("Python", 1, 0.5)], analyzed: 41 });
    stream.push(councilEvents("sess-r9").completed());
    expect(await screen.findByText("47 offres lues · 6 bloquées · 41 analysées")).toBeVisible();
    expect(screen.getByText("Python")).toBeVisible();
  });

  it("follows the open run on a 409 radar_in_progress instead of starting another", async () => {
    const { user, state, sockets, router } = setup({ runs: [radarRun("r1")] });
    await screen.findByText("47 offres lues · 6 bloquées · 41 analysées");
    // Un relevé démarre ailleurs (le lundi planifié, un autre onglet) après l'ouverture de la page.
    state.runs.unshift(RUNNING);
    state.sessions.push(sessionOut("sess-r9", "running", radarSession("r9")));

    await user.click(screen.getByRole("button", { name: "Lancer un relevé" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/carriere/radar/r9"));
    expect(await screen.findByText("Un relevé était déjà en cours : on le suit.")).toBeVisible();
    await openStream(sockets, "sess-r9");
    expect(state.runs.filter((run) => run.status === "running")).toHaveLength(1);
  });

  it("says on the role field that a role is required (409 radar_role_required)", async () => {
    const { user } = setup({
      startReply: () =>
        HttpResponse.json(apiError("radar_role_required", "Indique le poste visé."), {
          status: 409,
        }),
    });
    await user.click(await screen.findByRole("button", { name: "Lancer un relevé" }));
    expect(await screen.findByLabelText("Poste visé")).toHaveAccessibleDescription(
      "Indique le poste visé pour lancer un relevé.",
    );
  });

  it("names the refused field of a 422 without echoing a value", async () => {
    const { user } = setup({
      startReply: () =>
        HttpResponse.json(apiError("validation_error", "Requête invalide.", { fields: ["zone"] }), {
          status: 422,
        }),
    });
    await user.click(await screen.findByRole("button", { name: "Lancer un relevé" }));
    expect(await screen.findByLabelText("Zone")).toHaveAccessibleDescription(
      "Cette zone n'est pas acceptée : il faut entre 2 et 120 caractères.",
    );
    expect(screen.getByLabelText("Poste visé")).toBeValid();
  });

  it("does not send a role or a zone of one character", async () => {
    const { user, state } = setup({ defaults: { role: "D", zone: "France" } });
    await user.click(await screen.findByRole("button", { name: "Lancer un relevé" }));
    expect(screen.getByLabelText("Poste visé")).toBeInvalid();
    expect(state.bodies).toEqual([]);
  });

  it("keeps the offers of two postings that share a link", async () => {
    setup({
      runs: [
        radarRun("r1", {
          offers: [
            offerOut("https://example.org/jobs/1", { title: "Data engineer Paris" }),
            offerOut("https://example.org/jobs/1", { title: "Data engineer Lyon" }),
          ],
        }),
      ],
    });
    const list = await screen.findByRole("list", { name: "Offres du relevé" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(2);
  });
});
