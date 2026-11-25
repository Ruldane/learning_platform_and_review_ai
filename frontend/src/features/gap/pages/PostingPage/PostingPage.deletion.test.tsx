import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { API } from "@/test/councilApi";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { gapOut, postingOut, postingsApi, refusal } from "@/test/postingsApi";
import { renderPosting } from "@/test/postingsHarness";
import { server } from "@/test/server";
import { gapKeys } from "../../queryKeys";
import { PostingPage } from "./PostingPage";

function setup(api: Parameters<typeof postingsApi>[0] = {}) {
  return renderPosting((createSocket) => <PostingPage createSocket={createSocket} />, api);
}

const REMOVE = "Delete posting";
const CONFIRM = "Yes, delete";
const OPEN_REVIEW = "Open CV review";

describe("PostingPage deletion", () => {
  beforeEach(() => useSessionStore.getState().reset("a1"));
  afterEach(() => useSessionStore.getState().reset("a1"));

  it("says that CV reviews and generated PDFs go too when the posting has a review", async () => {
    const { user } = setup({ postings: [postingOut({ has_review: true })] });
    await user.click(await screen.findByRole("button", { name: REMOVE }));
    expect(
      screen.getByText(/along with its CV reviews and the PDFs generated for it/),
    ).toBeVisible();
  });

  it("keeps the short sentence when the posting has no review", async () => {
    const { user } = setup();
    await user.click(await screen.findByRole("button", { name: REMOVE }));
    expect(screen.getByText("The posting and its analysis will be erased.")).toBeVisible();
    expect(screen.queryByText(/CV reviews/)).toBeNull();
  });

  it("asks to finish the review first and links to it (409 review_in_progress)", async () => {
    const { user } = setup({
      postings: [postingOut({ has_review: true })],
      remove: () => refusal(409, "review_in_progress", "Server message."),
    });
    await user.click(await screen.findByRole("button", { name: REMOVE }));
    await user.click(screen.getByRole("button", { name: CONFIRM }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "First finish the CV review for this posting.",
    );
    expect(screen.getByRole("link", { name: OPEN_REVIEW })).toHaveAttribute(
      "href",
      "/career/cv/reviews/new/p1",
    );
  });

  it("asks to retry in a moment while an analysis is open (409 analysis_in_progress)", async () => {
    const { user } = setup({
      remove: () => refusal(409, "analysis_in_progress", "Server message."),
    });
    await user.click(await screen.findByRole("button", { name: REMOVE }));
    await user.click(screen.getByRole("button", { name: CONFIRM }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This posting is being analyzed: try again in a moment.",
    );
    expect(screen.queryByRole("link", { name: OPEN_REVIEW })).toBeNull();
  });

  it("says a committee or interview is running, with no review link (409 posting_has_running_work)", async () => {
    const { user } = setup({
      remove: () => refusal(409, "posting_has_running_work", "Server message."),
    });
    await user.click(await screen.findByRole("button", { name: REMOVE }));
    await user.click(screen.getByRole("button", { name: CONFIRM }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "A committee or interview is in progress for this posting: try again once it's done.",
    );
    expect(screen.queryByRole("link", { name: OPEN_REVIEW })).toBeNull();
  });

  it("starts clean on the duplicate opened from the page (no leftover deletion prompt)", async () => {
    const duplicate = {
      level: "probable",
      posting_id: "p7",
      title: "Ingénieur données",
      company: "Société Fictive",
      created_at: "2026-11-01T10:00:00Z",
    };
    const posting7 = postingOut({ id: "p7", title: "Ingénieur données" });
    const { handlers } = postingsApi({ postings: [postingOut({ duplicates: [duplicate] })] });
    server.use(
      ...handlers,
      http.get(`${API}/postings/p7`, () => HttpResponse.json(posting7)),
      http.get(`${API}/postings/p7/gap`, () => HttpResponse.json(gapOut({ posting_id: "p7" }))),
    );
    // L'offre p7 est déjà en cache (vue plus tôt) : la page ne repasse pas par « Chargement ».
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: Infinity } },
    });
    client.setQueryData(gapKeys.posting("p7"), posting7);
    const router = createMemoryRouter(
      [{ path: "/career/postings/:postingId", element: <PostingPage /> }],
      { initialEntries: ["/career/postings/p1"] },
    );
    render(
      <QueryClientProvider client={client}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: REMOVE }));
    expect(screen.getByRole("group", { name: "Delete this posting?" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Open" }));
    expect(
      await screen.findByRole("heading", { level: 1, name: "Ingénieur données" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Delete this posting?" })).toBeNull();
    expect(screen.getByRole("button", { name: REMOVE })).toBeInTheDocument();
  });
});
