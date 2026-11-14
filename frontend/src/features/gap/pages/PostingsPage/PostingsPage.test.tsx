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
      { path: "/carriere/offres/:postingId", element: <p>{"Page de l'offre"}</p> },
    ],
    "/carriere/offres",
  );
  return { ...view, state: postings.state };
}

const linkField = () => screen.getByRole("textbox", { name: "Lien de l'offre" });

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
    const list = await screen.findByRole("list", { name: "Offres ajoutées" });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(within(items[0]!).getByRole("link", { name: "Ingénieure données" })).toHaveAttribute(
      "href",
      "/carriere/offres/p1",
    );
    expect(within(items[0]!).getByText("Société Fictive")).toBeInTheDocument();
    expect(within(items[0]!).getByText("Match : 62/100")).toBeInTheDocument();
    expect(within(items[1]!).getByText("Refusée : ce n'est pas une offre")).toBeInTheDocument();
  });

  it("opens the page of a new posting (201)", async () => {
    const { user, router, state } = setup();
    await screen.findByRole("list", { name: "Offres ajoutées" });
    await user.type(linkField(), "https://example.org/jobs/9");
    await user.click(screen.getByRole("button", { name: "Analyser l'offre" }));
    expect(await screen.findByText("Page de l'offre")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/carriere/offres/p9");
    expect(state.created).toEqual([{ url: "https://example.org/jobs/9" }]);
  });

  it("falls back to the text tab when the link cannot be read", async () => {
    const { user } = setup({
      create: () => refusal(422, "posting_unreadable", "Message du serveur.", { fields: ["url"] }),
    });
    await screen.findByRole("list", { name: "Offres ajoutées" });
    await user.type(linkField(), "https://example.org/jobs/connexion");
    await user.click(screen.getByRole("button", { name: "Analyser l'offre" }));
    const message = await screen.findByRole("alert");
    expect(message).toHaveTextContent("Colle plutôt le texte de l'offre.");
    expect(screen.getByRole("tab", { name: "Texte" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("textbox", { name: "Texte de l'offre" })).toBeVisible();
    expect(screen.queryByText("https://example.org/jobs/connexion")).toBeNull();
  });

  it.each([
    ["posting_source", "Donne soit le lien de l'offre, soit son texte"],
    ["posting_too_short", "Ce texte est trop court"],
    ["invalid_url", "Ce lien n'est pas une adresse web valide."],
    ["url_forbidden", "Ce lien n'est pas autorisé"],
  ])("says %s in French", async (code, text) => {
    const { user } = setup({ create: () => refusal(422, code, "Message du serveur.") });
    await screen.findByRole("list", { name: "Offres ajoutées" });
    await user.type(linkField(), "x");
    await user.click(screen.getByRole("button", { name: "Analyser l'offre" }));
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
    await screen.findByRole("list", { name: "Offres ajoutées" });
    await user.type(linkField(), "https://example.org/jobs/1");
    await user.click(screen.getByRole("button", { name: "Analyser l'offre" }));
    expect(await screen.findByText("Tu as déjà ajouté cette offre le 03/11.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ouvrir l'offre" })).toHaveAttribute(
      "href",
      "/carriere/offres/p1",
    );
    expect(state.created).toHaveLength(1);
    await waitFor(() => expect(state.reads.list).toBeGreaterThanOrEqual(2));
    const items = within(screen.getByRole("list", { name: "Offres ajoutées" })).getAllByRole(
      "listitem",
    );
    expect(items).toHaveLength(1);
  });

  it("offers to add a first posting from the empty state", async () => {
    const { user } = setup({ lists: [[]] });
    expect(await screen.findByText("Aucune offre pour l'instant")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Ajouter une offre" }));
    expect(linkField()).toHaveFocus();
  });

  it("shows a retryable error", async () => {
    let failing = true;
    const { user } = setup({
      list: () =>
        failing
          ? refusal(500, "internal_error", "Panne du serveur.")
          : HttpResponse.json([summaryOut()]),
    });
    expect(await screen.findByText("Panne du serveur.")).toBeInTheDocument();
    failing = false;
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("list", { name: "Offres ajoutées" })).toBeInTheDocument();
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
    expect(await screen.findByText("Analyse en cours…")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(3100));
    expect(await screen.findByText("Match : 62/100")).toBeInTheDocument();
    expect(screen.queryByText("Analyse en cours…")).toBeNull();
    const reads = state.reads.list;
    await act(() => vi.advanceTimersByTimeAsync(9000));
    expect(state.reads.list).toBe(reads);
  });
});
