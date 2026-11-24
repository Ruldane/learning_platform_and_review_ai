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

describe("RadarPage launch and live updates", () => {
  it("launches a first run from the proposed values, follows it live, then shows the result", async () => {
    const { user, state, finish, sockets, router } = setup();
    expect(
      await screen.findByRole("heading", { name: "No scans yet" }),
    ).toBeVisible();
    expect(screen.getByLabelText("Target role")).toHaveValue("Data engineer");
    expect(screen.getByLabelText("Area")).toHaveValue("France");

    await user.clear(screen.getByLabelText("Target role"));
    await user.type(screen.getByLabelText("Target role"), "Analyste données");
    await user.click(screen.getByRole("button", { name: "Run a scan" }));

    expect(state.bodies).toEqual([{ role: "Analyste données", zone: "France" }]);
    await waitFor(() => expect(router.state.location.pathname).toBe("/carriere/radar/new1"));
    const title = await screen.findByRole("heading", { name: "Scan in progress" });
    expect(title).toBeVisible();
    expect(title).toHaveFocus(); // Focus moves to the scan as it replaces the form.
    expect(screen.getByRole("button", { name: "Scan in progress…" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );

    const stream = await openStream(sockets, "sess-new1");
    // The launch response is the only source of this session ID.
    expect(state.sessionReads).toBe(0);
    const events = councilEvents("sess-new1");
    stream.push(events.message("m1", "I found 52 job postings to read.", "scout"));
    stream.push(events.message("m2", "I’m ranking the requested skills.", "analyst"));
    expect(await screen.findByText("I found 52 job postings to read.")).toBeVisible();
    expect(screen.getByText("I’m ranking the requested skills.")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Most in-demand skills" })).toBeNull();

    finish("new1", {
      ranking: [trendOut("SQL", 1, 0.62)],
      read_count: 47,
      blocked_count: 6,
      analyzed: 41,
    });
    stream.push(events.completed());
    expect(await screen.findByText("47 postings read · 6 blocked · 41 analyzed")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Most in-demand skills" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Run a scan" })).toHaveAttribute(
      "aria-disabled",
      "false",
    );
  });

  it("follows a run that is already in progress: found by its subject, then its result", async () => {
    const { finish, sockets, router } = setup({
      runs: [RUNNING],
      sessions: [sessionOut("sess-r9", "running", radarSession("r9"))],
    });
    await waitFor(() => expect(router.state.location.pathname).toBe("/carriere/radar/r9"));
    expect(await screen.findByRole("heading", { name: "Scan in progress" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Scan in progress…" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );

    const stream = await openStream(sockets, "sess-r9");
    finish("r9", { ranking: [trendOut("Python", 1, 0.5)], analyzed: 41 });
    stream.push(councilEvents("sess-r9").completed());
    expect(await screen.findByText("47 postings read · 6 blocked · 41 analyzed")).toBeVisible();
    expect(screen.getByText("Python")).toBeVisible();
  });

  it("follows the open run on a 409 radar_in_progress instead of starting another", async () => {
    const { user, state, sockets, router } = setup({ runs: [radarRun("r1")] });
    await screen.findByText("47 postings read · 6 blocked · 41 analyzed");
    // Another tab or the scheduler starts a scan after the page opens.
    state.runs.unshift(RUNNING);
    state.sessions.push(sessionOut("sess-r9", "running", radarSession("r9")));

    await user.click(screen.getByRole("button", { name: "Run a scan" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/carriere/radar/r9"));
    expect(await screen.findByText("A scan was already in progress: following it.")).toBeVisible();
    await openStream(sockets, "sess-r9");
    expect(state.runs.filter((run) => run.status === "running")).toHaveLength(1);
  });

  it("says on the role field that a role is required (409 radar_role_required)", async () => {
    const { user } = setup({
      startReply: () =>
        HttpResponse.json(apiError("radar_role_required", "Enter a target role."), {
          status: 409,
        }),
    });
    await user.click(await screen.findByRole("button", { name: "Run a scan" }));
    expect(await screen.findByLabelText("Target role")).toHaveAccessibleDescription(
      "Enter the target role to run a scan.",
    );
  });

  it("names the refused field of a 422 without echoing a value", async () => {
    const { user } = setup({
      startReply: () =>
        HttpResponse.json(apiError("validation_error", "Invalid request.", { fields: ["zone"] }), {
          status: 422,
        }),
    });
    await user.click(await screen.findByRole("button", { name: "Run a scan" }));
    expect(await screen.findByLabelText("Area")).toHaveAccessibleDescription(
      "This area isn’t accepted: it must be between 2 and 120 characters.",
    );
    expect(screen.getByLabelText("Target role")).toBeValid();
  });

  it("does not send a role or a zone of one character", async () => {
    const { user, state } = setup({ defaults: { role: "D", zone: "France" } });
    await user.click(await screen.findByRole("button", { name: "Run a scan" }));
    expect(screen.getByLabelText("Target role")).toBeInvalid();
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
    const list = await screen.findByRole("list", { name: "Scan postings" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(2);
  });
});
