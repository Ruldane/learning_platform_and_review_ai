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

describe("PostingPage deletion", () => {
  beforeEach(() => useSessionStore.getState().reset("a1"));
  afterEach(() => useSessionStore.getState().reset("a1"));

  it("says that CV reviews and generated PDFs go too when the posting has a review", async () => {
    const { user } = setup({ postings: [postingOut({ has_review: true })] });
    await user.click(await screen.findByRole("button", { name: "Supprimer l'offre" }));
    expect(
      screen.getByText(/ainsi que ses revues de CV et les PDF générés pour cette offre/),
    ).toBeVisible();
  });

  it("keeps the short sentence when the posting has no review", async () => {
    const { user } = setup();
    await user.click(await screen.findByRole("button", { name: "Supprimer l'offre" }));
    expect(screen.getByText("L'offre et son analyse seront effacées.")).toBeVisible();
    expect(screen.queryByText(/revues de CV/)).toBeNull();
  });

  it("asks to finish the review first and links to it (409 review_in_progress)", async () => {
    const { user } = setup({
      postings: [postingOut({ has_review: true })],
      remove: () => refusal(409, "review_in_progress", "Message du serveur."),
    });
    await user.click(await screen.findByRole("button", { name: "Supprimer l'offre" }));
    await user.click(screen.getByRole("button", { name: "Oui, supprimer" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Termine d'abord la revue de CV de cette offre.",
    );
    expect(screen.getByRole("link", { name: "Ouvrir la revue de CV" })).toHaveAttribute(
      "href",
      "/carriere/cv/revue/nouvelle/p1",
    );
  });

  it("asks to retry in a moment while an analysis is open (409 analysis_in_progress)", async () => {
    const { user } = setup({
      remove: () => refusal(409, "analysis_in_progress", "Message du serveur."),
    });
    await user.click(await screen.findByRole("button", { name: "Supprimer l'offre" }));
    await user.click(screen.getByRole("button", { name: "Oui, supprimer" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Une analyse de cette offre est en cours : réessaie dans un instant.",
    );
    expect(screen.queryByRole("link", { name: "Ouvrir la revue de CV" })).toBeNull();
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
      [{ path: "/carriere/offres/:postingId", element: <PostingPage /> }],
      { initialEntries: ["/carriere/offres/p1"] },
    );
    render(
      <QueryClientProvider client={client}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Supprimer l'offre" }));
    expect(screen.getByRole("group", { name: "Supprimer cette offre ?" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Ouvrir" }));
    expect(
      await screen.findByRole("heading", { level: 1, name: "Ingénieur données" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Supprimer cette offre ?" })).toBeNull();
    expect(screen.getByRole("button", { name: "Supprimer l'offre" })).toBeInTheDocument();
  });
});
