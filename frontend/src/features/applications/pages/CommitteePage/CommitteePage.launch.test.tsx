import { screen, waitFor } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { openStream } from "@/test/applicationsHarness";
import { committeeOut, runningCommittee } from "@/test/committeeApi";
import { API } from "@/test/councilApi";
import { apiError } from "@/test/councilHarness";
import { versionOut } from "@/test/cvFixtures";
import { server } from "@/test/server";
import { setup, SESSION } from "./committeeTestkit";

const refuse = (status: number, code: string, details?: Record<string, unknown>) => () =>
  HttpResponse.json(apiError(code, "Refus.", details), { status });

describe("CommitteePage, lancer et relancer", () => {
  beforeEach(() => {
    useSessionStore.getState().reset(SESSION);
    useSessionStore.getState().reset("cm-s1");
  });

  it("offers only the ready versions of the offer, the one sent with the application first", async () => {
    setup({
      versions: [
        versionOut({ id: "v3", number: 3, status: "rendering" }),
        versionOut({ id: "v2", number: 2 }),
        versionOut({ id: "v1", number: 1 }),
        versionOut({ id: "v0", number: 0, status: "failed" }),
      ],
    });
    const select = await screen.findByRole("combobox", { name: "Version du CV à faire juger" });
    const options = Array.from((select as HTMLSelectElement).options).map((o) => o.text);
    expect(options).toEqual(["Version 2", "Version 1"]);
    expect(select).toHaveValue("v1");
  });

  it("proposes the latest ready version when the one sent with the application is not ready", async () => {
    setup({ versions: [versionOut({ id: "v2", number: 2 })] });
    expect(
      await screen.findByRole("combobox", { name: "Version du CV à faire juger" }),
    ).toHaveValue("v2");
  });

  it("says when no version is ready, and links to the versions", async () => {
    setup({ versions: [versionOut({ id: "v1", status: "rendering" })] });
    expect(await screen.findByText(/Aucune version prête du CV pour cette offre/)).toBeVisible();
    expect(screen.getByRole("link", { name: "Voir les versions du CV" })).toHaveAttribute(
      "href",
      "/carriere/cv/versions",
    );
    expect(screen.queryByRole("button", { name: /comité/ })).toBeNull();
  });

  it("invites to run the committee again after a new version, then judges the new one", async () => {
    const view = setup({
      runs: [committeeOut()],
      versions: [versionOut({ id: "v2", number: 2 }), versionOut({ id: "v1", number: 1 })],
    });
    expect(await screen.findByText("Dernier comité : version 1 du CV.")).toBeVisible();
    expect(screen.getByText(/Une version plus récente du CV existe/)).toBeVisible();
    await view.user.selectOptions(
      screen.getByRole("combobox", { name: "Version du CV à faire juger" }),
      "v2",
    );
    await view.user.click(screen.getByRole("button", { name: "Relancer le comité" }));
    await waitFor(() => expect(view.committee.state.starts).toEqual([{ cv_version_id: "v2" }]));
    await openStream(view.sockets, SESSION);
    expect(await screen.findByText("Le comité délibère…")).toBeVisible();
    expect(screen.queryByText(/Une version plus récente/)).toBeNull();
  });

  it("does not say a newer version exists when the latest one was judged", async () => {
    setup({
      runs: [committeeOut({ cv_version_id: "v2" })],
      versions: [versionOut({ id: "v2", number: 2 })],
    });
    await screen.findByText("Dernier comité : version 2 du CV.");
    expect(screen.queryByText(/Une version plus récente/)).toBeNull();
  });

  it("follows the committee that is already open instead of failing (409 committee_in_progress)", async () => {
    const view = setup({ start: refuse(409, "committee_in_progress", { run_id: "c9" }) });
    await screen.findByRole("button", { name: "Lancer le comité" });
    // Un comité s'est ouvert ailleurs depuis la lecture de la liste.
    view.committee.runs.unshift(runningCommittee({ id: "c9", session_id: "cm-s1" }));
    await view.user.click(screen.getByRole("button", { name: "Lancer le comité" }));
    await openStream(view.sockets, "cm-s1");
    expect(
      await screen.findByText("Un comité était déjà en cours pour cette offre : tu le suis ici."),
    ).toBeVisible();
    expect(await screen.findByText("Le comité délibère…")).toBeVisible();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("keeps the launch button disabled between the 202 and the first reading of the new committee", async () => {
    const view = setup();
    await screen.findByRole("button", { name: "Lancer le comité" });
    server.use(
      http.get(`${API}/committee/:id`, async () => {
        await delay(400);
        return HttpResponse.json(runningCommittee({ id: "c1-new", session_id: SESSION }));
      }),
    );
    await view.user.click(screen.getByRole("button", { name: "Lancer le comité" }));
    // « Relancer » n'apparaît qu'une fois le 202 reçu : la première lecture, retardée, n'est pas là.
    expect(await screen.findByRole("button", { name: "Relancer le comité" })).toBeDisabled();
    expect(screen.queryByText("Le comité délibère…")).toBeNull();
    expect(await screen.findByText("Le comité délibère…")).toBeVisible();
    expect(screen.getByRole("button", { name: "Relancer le comité" })).toBeDisabled();
  });

  it("says that the PDF of the version is not rendered yet (409 version_not_ready)", async () => {
    const view = setup({ start: refuse(409, "version_not_ready") });
    await view.user.click(await screen.findByRole("button", { name: "Lancer le comité" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Le PDF de cette version n'est pas encore rendu",
    );
    expect(screen.getByRole("button", { name: "Lancer le comité" })).toBeEnabled();
  });

  it("says that the version or the offer is gone (404)", async () => {
    const view = setup({ start: refuse(404, "version_not_found") });
    await view.user.click(await screen.findByRole("button", { name: "Lancer le comité" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Cette version du CV n'existe plus");
  });

  it("links to the profile when none is validated (409 profile_required)", async () => {
    const view = setup({ start: refuse(409, "profile_required") });
    await view.user.click(await screen.findByRole("button", { name: "Lancer le comité" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Aucun profil maître validé");
    expect(screen.getByRole("link", { name: "Ouvrir mon profil" })).toHaveAttribute(
      "href",
      "/carriere/profil",
    );
  });

  it("says that the agents are unavailable (503) and keeps the choice", async () => {
    const view = setup({ start: refuse(503, "engine_unavailable") });
    await view.user.click(await screen.findByRole("button", { name: "Lancer le comité" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Les agents ne sont pas disponibles",
    );
    expect(screen.getByRole("button", { name: "Lancer le comité" })).toBeEnabled();
  });

  it("says a stopped committee ended before its verdict and offers to run it again", async () => {
    setup({
      runs: [
        committeeOut({ status: "stopped", verdict: null, votes: [], objections: [], changes: [] }),
      ],
    });
    expect(
      await screen.findByText(/Le comité a été arrêté avant son verdict\. Tu peux le relancer\./),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Relancer le comité" })).toBeEnabled();
  });
});
