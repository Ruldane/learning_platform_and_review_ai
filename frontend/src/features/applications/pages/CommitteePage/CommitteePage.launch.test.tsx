import { screen, waitFor } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { openStream } from "@/test/applicationsHarness";
import { committeeOut, runningCommittee } from "@/test/committeeApi";
import { API } from "@/test/councilApi";
import { councilEvents } from "@/test/councilEvents";
import { apiError } from "@/test/councilHarness";
import { versionOut } from "@/test/cvFixtures";
import { server } from "@/test/server";
import { setup, SESSION } from "./committeeTestkit";

const refuse = (status: number, code: string, details?: Record<string, unknown>) => () =>
  HttpResponse.json(apiError(code, "Refus.", details), { status });

describe("CommitteePage, starting and rerunning", () => {
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
    const select = await screen.findByRole("combobox", { name: "Résumé version to be judged" });
    const options = Array.from((select as HTMLSelectElement).options).map((o) => o.text);
    expect(options).toEqual(["Version 2", "Version 1"]);
    expect(select).toHaveValue("v1");
  });

  it("proposes the latest ready version when the one sent with the application is not ready", async () => {
    setup({ versions: [versionOut({ id: "v2", number: 2 })] });
    expect(
      await screen.findByRole("combobox", { name: "Résumé version to be judged" }),
    ).toHaveValue("v2");
  });

  it("says when no version is ready, and links to the versions", async () => {
    setup({ versions: [versionOut({ id: "v1", status: "rendering" })] });
    expect(await screen.findByText(/No ready résumé version for this posting/)).toBeVisible();
    expect(screen.getByRole("link", { name: "See résumé versions" })).toHaveAttribute(
      "href",
      "/career/cv/versions",
    );
    expect(screen.queryByRole("button", { name: /committee/i })).toBeNull();
  });

  it("invites to run the committee again after a new version, then judges the new one", async () => {
    const view = setup({
      runs: [committeeOut()],
      versions: [versionOut({ id: "v2", number: 2 }), versionOut({ id: "v1", number: 1 })],
    });
    expect(await screen.findByText("Last committee: résumé version 1.")).toBeVisible();
    expect(screen.getByText(/A newer résumé version exists/)).toBeVisible();
    await view.user.selectOptions(
      screen.getByRole("combobox", { name: "Résumé version to be judged" }),
      "v2",
    );
    await view.user.click(screen.getByRole("button", { name: "Rerun the committee" }));
    await waitFor(() => expect(view.committee.state.starts).toEqual([{ cv_version_id: "v2" }]));
    await openStream(view.sockets, SESSION);
    expect(await screen.findByText("The committee is deliberating…")).toBeVisible();
    expect(screen.queryByText(/A newer résumé version/)).toBeNull();
  });

  it("does not say a newer version exists when the latest one was judged", async () => {
    setup({
      runs: [committeeOut({ cv_version_id: "v2" })],
      versions: [versionOut({ id: "v2", number: 2 })],
    });
    await screen.findByText("Last committee: résumé version 2.");
    expect(screen.queryByText(/A newer résumé version/)).toBeNull();
  });

  it("follows the committee that is already open instead of failing (409 committee_in_progress)", async () => {
    const view = setup({ start: refuse(409, "committee_in_progress", { run_id: "c9" }) });
    await screen.findByRole("button", { name: "Run the committee" });
    // A committee started elsewhere after the list loaded.
    view.committee.runs.unshift(runningCommittee({ id: "c9", session_id: "cm-s1" }));
    await view.user.click(screen.getByRole("button", { name: "Run the committee" }));
    const stream = await openStream(view.sockets, "cm-s1");
    expect(
      await screen.findByText(
        "A committee was already running for this posting: you're following it here.",
      ),
    ).toBeVisible();
    expect(await screen.findByText("The committee is deliberating…")).toBeVisible();
    expect(screen.queryByRole("alert")).toBeNull();
    // The notice disappears when the committee finishes.
    view.committee.finish("c9");
    stream.push(councilEvents("cm-s1").completed());
    expect(await screen.findByText("The committee says:")).toBeVisible();
    expect(screen.queryByText(/following it here/)).toBeNull();
  });

  it("keeps the launch button disabled between the 202 and the first reading of the new committee", async () => {
    const view = setup();
    await screen.findByRole("button", { name: "Run the committee" });
    server.use(
      http.get(`${API}/committee/:id`, async () => {
        await delay(400);
        return HttpResponse.json(runningCommittee({ id: "c1-new", session_id: SESSION }));
      }),
    );
    await view.user.click(screen.getByRole("button", { name: "Run the committee" }));
    // The 202 makes Rerun visible while the first fetch is still pending.
    expect(await screen.findByRole("button", { name: "Rerun the committee" })).toBeDisabled();
    expect(screen.queryByText("The committee is deliberating…")).toBeNull();
    expect(await screen.findByText("The committee is deliberating…")).toBeVisible();
    expect(screen.getByRole("button", { name: "Rerun the committee" })).toBeDisabled();
  });

  it("says that the PDF of the version is not rendered yet (409 version_not_ready)", async () => {
    const view = setup({ start: refuse(409, "version_not_ready") });
    await view.user.click(await screen.findByRole("button", { name: "Run the committee" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This version's PDF isn't rendered yet",
    );
    expect(screen.getByRole("button", { name: "Run the committee" })).toBeEnabled();
  });

  it("says that the version or the offer is gone (404)", async () => {
    const view = setup({ start: refuse(404, "version_not_found") });
    await view.user.click(await screen.findByRole("button", { name: "Run the committee" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This résumé version no longer exists",
    );
  });

  it("links to the profile when none is validated (409 profile_required)", async () => {
    const view = setup({ start: refuse(409, "profile_required") });
    await view.user.click(await screen.findByRole("button", { name: "Run the committee" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("No validated master profile");
    expect(screen.getByRole("link", { name: "Open my profile" })).toHaveAttribute(
      "href",
      "/career/profile",
    );
  });

  it("says that the agents are unavailable (503) and keeps the choice", async () => {
    const view = setup({ start: refuse(503, "engine_unavailable") });
    await view.user.click(await screen.findByRole("button", { name: "Run the committee" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The agents aren't available",
    );
    expect(screen.getByRole("button", { name: "Run the committee" })).toBeEnabled();
  });

  it("says a stopped committee ended before its verdict and offers to run it again", async () => {
    setup({
      runs: [
        committeeOut({ status: "stopped", verdict: null, votes: [], objections: [], changes: [] }),
      ],
    });
    expect(
      await screen.findByText(/The committee was stopped before its verdict\. You can rerun it\./),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Rerun the committee" })).toBeEnabled();
  });
});
