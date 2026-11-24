import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import {
  analyzingPosting,
  gapOut,
  gapRow,
  postingOut,
  postingsApi,
  refusal,
} from "@/test/postingsApi";
import { renderPosting } from "@/test/postingsHarness";
import { PostingPage } from "./PostingPage";

function setup(api: Parameters<typeof postingsApi>[0] = {}) {
  return renderPosting((createSocket) => <PostingPage createSocket={createSocket} />, api);
}

const analyzing = analyzingPosting;
const ADD = "Add to schedule (1)";
const PYTHON = "Add Python to the schedule";
const REMOVE = "Delete posting";
const RESTART = "Restart analysis";
const OPEN_REPLAN = "Open replanning";
const DUPLICATE = "Very close to a posting you've already added.";

describe("PostingPage", () => {
  beforeEach(() => useSessionStore.getState().reset("a1"));
  afterEach(() => useSessionStore.getState().reset("a1"));

  it("shows the analysis, the score and the gap table of a ready posting", async () => {
    setup();
    expect(
      await screen.findByRole("heading", { level: 1, name: "Ingénieure données" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Société Fictive")).toBeInTheDocument();
    expect(await screen.findByText("62/100")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Gap with the posting" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review my CV for this posting" })).toHaveAttribute(
      "href",
      "/carriere/cv/revue/nouvelle/p1",
    );
  });

  it("posting title rendered once", async () => {
    setup();
    await screen.findByRole("region", { name: "Posting analysis" });
    expect(screen.getAllByRole("heading", { name: "Ingénieure données" })).toHaveLength(1);
  });

  it("offers only the rows that are really missing and sends the ticked skills", async () => {
    const { user, state } = setup();
    const python = await screen.findByRole("checkbox", { name: PYTHON });
    expect(screen.queryByRole("checkbox", { name: "Add SQL to the schedule" })).toBeNull();
    expect(screen.queryByRole("checkbox", { name: "Add Go to the schedule" })).toBeNull();
    expect(screen.getByText("Already acquired")).toBeInTheDocument();
    await user.click(python);
    await user.click(screen.getByRole("checkbox", { name: "Add Docker to the schedule" }));
    await user.click(screen.getByRole("button", { name: "Add to schedule (2)" }));
    expect(await screen.findByText(/Replanning started/)).toBeInTheDocument();
    expect(state.plans).toEqual([{ skills: ["Python", "Docker"] }]);
    await user.click(screen.getByRole("link", { name: OPEN_REPLAN }));
    expect(await screen.findByText("Replan")).toBeInTheDocument();
  });

  it("explains that an approved program is needed and offers to create a goal", async () => {
    const { user } = setup({
      plan: () => refusal(409, "no_program", "Server message."),
    });
    await user.click(await screen.findByRole("checkbox", { name: PYTHON }));
    await user.click(screen.getByRole("button", { name: ADD }));
    expect(await screen.findByRole("alert")).toHaveTextContent("an approved program yet");
    await user.click(screen.getByRole("link", { name: "Create a goal" }));
    expect(await screen.findByText("Goals")).toBeInTheDocument();
  });

  it("adds a row outside the scope to the chosen validated program", async () => {
    const { user, state } = setup({
      gaps: [gapOut({ rows: [gapRow("SAP", { action: "out_of_scope" })] })],
      programs: [
        { id: "draft", title: "Un brouillon", status: "draft" },
        { id: "training", title: "Systèmes de données", status: "validated" },
      ],
    });
    await user.click(await screen.findByRole("checkbox", { name: "Add SAP to the schedule" }));
    await screen.findByRole("option", { name: "Systèmes de données" });
    expect(screen.queryByRole("option", { name: "Un brouillon" })).toBeNull();
    await user.selectOptions(screen.getByRole("combobox", { name: "Target program" }), "training");
    const gap = screen.getByRole("region", { name: "Gap with your profile" });
    await user.selectOptions(
      within(gap).getByRole("combobox", { name: "Who runs the agents for this launch" }),
      "openai",
    );
    expect(screen.getByRole("button", { name: /^I already know these/ })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: ADD }));
    await waitFor(() => expect(state.plans).toEqual([{ skills: ["SAP"], program_id: "training" }]));
    expect(state.planSources).toEqual(["openai"]);
  });

  it("links to the replan already open (409 replan_open)", async () => {
    const { user } = setup({
      plan: () => refusal(409, "replan_open", "Server message.", { session_id: "r1" }),
    });
    await user.click(await screen.findByRole("checkbox", { name: PYTHON }));
    await user.click(screen.getByRole("button", { name: ADD }));
    expect(await screen.findByText("A replanning is already open.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: OPEN_REPLAN })).toHaveAttribute(
      "href",
      "/apprendre/programme/pg1/replanification",
    );
  });

  it("rereads the table when a skill is no longer to add (422)", async () => {
    const { user, state } = setup({
      plan: () =>
        refusal(422, "gap_skill_unknown", "Server message.", { fields: ["skills.0"] }),
      gaps: [
        gapOut(),
        gapOut({ rows: [gapRow("Python", { action: "in_program", week: 2 }), gapRow("Docker")] }),
      ],
    });
    await user.click(await screen.findByRole("checkbox", { name: PYTHON }));
    await user.click(screen.getByRole("button", { name: ADD }));
    expect(await screen.findByRole("alert")).toHaveTextContent("no longer needs adding");
    await waitFor(() => expect(state.reads.gap).toBe(2));
    expect(await screen.findByText("In your program, week 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add to schedule" })).toBeDisabled();
  });

  it("shows probable duplicates and marks two postings as distinct", async () => {
    const duplicate = {
      level: "probable",
      posting_id: "p7",
      title: "Ingénieur données",
      company: "Société Fictive",
      created_at: "2026-11-01T10:00:00Z",
    };
    const { user, state } = setup({
      postings: [postingOut({ duplicates: [duplicate] }), postingOut()],
    });
    expect(await screen.findByText(DUPLICATE)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "These are two different postings" }));
    await waitFor(() => expect(state.distincts).toEqual([{ other_id: "p7" }]));
    await waitFor(() =>
      expect(screen.queryByText(DUPLICATE)).toBeNull(),
    );
  });

  it("confirms the deletion in the page, never with window.confirm", async () => {
    const confirm = vi.spyOn(window, "confirm");
    const { user, state } = setup();
    await user.click(await screen.findByRole("button", { name: REMOVE }));
    const ask = screen.getByRole("group", { name: "Delete this posting?" });
    expect(within(ask).getByRole("button", { name: "Cancel" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("group", { name: "Delete this posting?" })).toBeNull();
    expect(state.removed).toBe(0);
    await user.click(screen.getByRole("button", { name: REMOVE }));
    await user.click(screen.getByRole("button", { name: "Yes, delete" }));
    expect(await screen.findByText("Postings list")).toBeInTheDocument();
    expect(state.removed).toBe(1);
    expect(confirm).not.toHaveBeenCalled();
  });

  it("shows a rejected posting without relaunch", async () => {
    setup({
      postings: [
        postingOut({
          status: "rejected",
          title: null,
          analysis: null,
          failure_reason: "This text describes a company with no open role.",
        }),
      ],
    });
    expect(
      await screen.findByRole("heading", { name: "Rejected: this isn't a job posting" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("This text describes a company with no open role."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: RESTART })).toBeNull();
    expect(screen.getByRole("button", { name: REMOVE })).toBeInTheDocument();
  });

  it("relaunches an interrupted analysis", async () => {
    const { user, state } = setup({
      postings: [
        postingOut({
          status: "failed",
          analysis: null,
          failure_reason: "Posting analysis stopped. Restart the analysis.",
        }),
        analyzing(),
      ],
    });
    await user.click(await screen.findByRole("button", { name: RESTART }));
    expect(await screen.findByText("Analyzing…")).toBeInTheDocument();
    expect(state.relaunched).toBe(1);
  });

  it("follows the relaunch of an analysis already running (409 gap_in_progress)", async () => {
    const { user } = setup({
      postings: [postingOut({ status: "failed", analysis: null }), analyzing()],
      relaunch: () => refusal(409, "gap_in_progress", "This posting is already being analyzed."),
    });
    await user.click(await screen.findByRole("button", { name: RESTART }));
    expect(await screen.findByText("Analyzing…")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("waits for a gap being computed, then relaunches a failed one", async () => {
    const { user } = setup({ gaps: [gapOut({ status: "failed", score: null, rows: [] })] });
    expect(await screen.findByText("The gap couldn't be calculated.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: RESTART }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: RESTART })).toBeEnabled(),
    );
  });

  it("says when the posting does not exist", async () => {
    const { user } = setup({
      posting: () => refusal(404, "posting_not_found", "Posting not found."),
    });
    expect(await screen.findByText("Posting not found")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Back to postings" }));
    expect(await screen.findByText("Postings list")).toBeInTheDocument();
  });

  it("shows a retryable error", async () => {
    let failing = true;
    const { user } = setup({
      posting: () =>
        failing
          ? refusal(500, "internal_error", "The server is unavailable.")
          : HttpResponse.json(postingOut()),
    });
    expect(
      await screen.findByText("The server is unavailable.", {}, { timeout: 4000 }),
    ).toBeInTheDocument();
    failing = false;
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(
      await screen.findByRole("heading", { level: 1, name: "Ingénieure données" }),
    ).toBeInTheDocument();
  });
});
