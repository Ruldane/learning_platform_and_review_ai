import { act, screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { postingOut, postingsApi, refusal, summaryOut } from "@/test/postingsApi";
import { PostingsPage } from "./PostingsPage";

function setup(api: Parameters<typeof postingsApi>[0] = {}, pollMs?: number) {
  const postings = postingsApi(api);
  server.use(...postings.handlers);
  const view = renderRoutes(
    [
      { path: "/carriere/offres", element: <PostingsPage pollMs={pollMs} /> },
      { path: "/carriere/offres/:postingId", element: <p>Posting detail</p> },
    ],
    "/carriere/offres",
  );
  return { ...view, state: postings.state };
}

const linkField = () => screen.getByRole("textbox", { name: "Posting link" });
const POSTINGS = "Added postings";
const ANALYZE = "Analyze posting";

describe("PostingsPage", () => {
  it("lists the postings with their title, company and score", async () => {
    setup({
      lists: [
        [
          summaryOut(),
          summaryOut({ id: "p2", title: null, company: null, score: null, status: "rejected" }),
        ],
      ],
    });
    const list = await screen.findByRole("list", { name: POSTINGS });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(within(items[0]!).getByRole("link", { name: "Ingénieure données" })).toHaveAttribute(
      "href",
      "/carriere/offres/p1",
    );
    expect(within(items[0]!).getByText("Société Fictive")).toBeInTheDocument();
    expect(within(items[0]!).getByText("Match: 62/100")).toBeInTheDocument();
    expect(within(items[1]!).getByText("Rejected: this isn't a job posting")).toBeInTheDocument();
  });

  it("opens the page of a new posting (201)", async () => {
    const { user, router, state } = setup();
    await screen.findByRole("list", { name: POSTINGS });
    await user.type(linkField(), "https://example.org/jobs/9");
    await user.click(screen.getByRole("button", { name: ANALYZE }));
    expect(await screen.findByText("Posting detail")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/carriere/offres/p9");
    expect(state.created).toEqual([{ url: "https://example.org/jobs/9" }]);
  });

  it("falls back to the text tab when the link cannot be read", async () => {
    const { user } = setup({
      create: () => refusal(422, "posting_unreadable", "Server message.", { fields: ["url"] }),
    });
    await screen.findByRole("list", { name: POSTINGS });
    await user.type(linkField(), "https://example.org/jobs/connexion");
    await user.click(screen.getByRole("button", { name: ANALYZE }));
    const message = await screen.findByRole("alert");
    expect(message).toHaveTextContent("Paste the posting text instead.");
    expect(screen.getByRole("tab", { name: "Text" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("textbox", { name: "Posting text" })).toBeVisible();
    expect(screen.queryByText("https://example.org/jobs/connexion")).toBeNull();
  });

  it.each([
    ["posting_source", "Provide either the posting link or its text"],
    ["posting_too_short", "This text is too short"],
    ["invalid_url", "This link isn't a valid web address."],
    ["url_forbidden", "This link isn't allowed"],
  ])("explains %s in English", async (code, text) => {
    const { user } = setup({ create: () => refusal(422, code, "Server message.") });
    await screen.findByRole("list", { name: POSTINGS });
    await user.type(linkField(), "x");
    await user.click(screen.getByRole("button", { name: ANALYZE }));
    expect(await screen.findByRole("alert")).toHaveTextContent(text);
  });

  it("says a posting is already there (200), with a link and no duplicate in the list", async () => {
    const { user, state } = setup({
      create: () =>
        HttpResponse.json(
          { created: false, posting: postingOut(), session_id: null },
          { status: 200 },
        ),
    });
    await screen.findByRole("list", { name: POSTINGS });
    await user.type(linkField(), "https://example.org/jobs/1");
    await user.click(screen.getByRole("button", { name: ANALYZE }));
    expect(await screen.findByText("You already added this posting on 03/11.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open posting" })).toHaveAttribute(
      "href",
      "/carriere/offres/p1",
    );
    expect(state.created).toHaveLength(1);
    await waitFor(() => expect(state.reads.list).toBeGreaterThanOrEqual(2));
    const items = within(screen.getByRole("list", { name: POSTINGS })).getAllByRole("listitem");
    expect(items).toHaveLength(1);
  });

  it("offers to add a first posting from the empty state", async () => {
    const { user } = setup({ lists: [[]] });
    expect(await screen.findByText("No postings yet")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Add a posting" }));
    expect(linkField()).toHaveFocus();
  });

  it("shows a retryable error", async () => {
    let failing = true;
    const { user } = setup({
      list: () =>
        failing
          ? refusal(500, "internal_error", "The server is unavailable.")
          : HttpResponse.json([summaryOut()]),
    });
    expect(await screen.findByText("The server is unavailable.")).toBeInTheDocument();
    failing = false;
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("list", { name: POSTINGS })).toBeInTheDocument();
  });
});

describe("PostingsPage while a posting is analysed", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("rereads the list every three seconds until the analysis is over", async () => {
    const { state } = setup({
      lists: [
        [summaryOut({ id: "p2", title: null, company: null, score: null, status: "analyzing" })],
        [summaryOut({ id: "p2", status: "ready" })],
      ],
    });
    expect(await screen.findByText("Analyzing…")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(3100));
    expect(await screen.findByText("Match: 62/100")).toBeInTheDocument();
    expect(screen.queryByText("Analyzing…")).toBeNull();
    const reads = state.reads.list;
    await act(() => vi.advanceTimersByTimeAsync(9000));
    expect(state.reads.list).toBe(reads);
  });
});
