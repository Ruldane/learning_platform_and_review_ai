import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { API } from "@/test/councilApi";
import { apiError } from "@/test/councilHarness";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { ReviewsPage } from "./ReviewsPage";

const card = (id: string, front: string, back: string, skill: string | null = "REST") => ({
  id,
  front,
  back,
  skill,
});

const queue = (over: Record<string, unknown> = {}) => ({
  cards: [card("c1", "Que fait GET ?", "Il lit."), card("c2", "Que fait PUT ?", "Il remplace.")],
  reviewed_today: 4,
  daily_cards: 30,
  remaining_due: 0,
  ...over,
});

type Reply = () => Response | Promise<Response>;

function setup(due: Record<string, unknown> | Reply = queue()) {
  server.use(
    http.get(`${API}/flashcards/due`, () =>
      typeof due === "function" ? due() : HttpResponse.json(due),
    ),
  );
  const router = createMemoryRouter(
    [
      { path: "/etudier/revisions", element: <ReviewsPage /> },
      { path: "/etudier/quiz", element: <p>Liste des quiz</p> },
    ],
    { initialEntries: ["/etudier/revisions"] },
  );
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { router, user: userEvent.setup() };
}

/** Enregistre les avis envoyés ; `reply` choisit la réponse pour chaque fiche. */
function recordReviews(reply: (cardId: string) => Response = () => reviewOut("c1")) {
  const sent: { card: string; body: unknown }[] = [];
  server.use(
    http.post(`${API}/flashcards/:cardId/review`, async ({ request, params }) => {
      const cardId = String(params.cardId);
      sent.push({ card: cardId, body: await request.json() });
      return reply(cardId);
    }),
  );
  return sent;
}

const reviewOut = (cardId: string, over: Record<string, unknown> = {}) =>
  HttpResponse.json({
    card_id: cardId,
    step: 1,
    due_date: "2026-11-18",
    demoted_skill: null,
    ...over,
  });

describe("ReviewsPage", () => {
  it("reviews due cards one after the other", async () => {
    const sent = recordReviews((id) => reviewOut(id));
    const { user } = setup();
    expect(await screen.findByText("Que fait GET ?")).toBeInTheDocument();
    expect(screen.getByText("2 fiches à réviser")).toBeInTheDocument();
    expect(screen.getByText("Revues aujourd'hui : 4 sur 30")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Voir la réponse/ }));
    await user.click(screen.getByRole("button", { name: /Su/ }));
    expect(await screen.findByText("Que fait PUT ?")).toBeInTheDocument();
    expect(screen.getByText("Revues aujourd'hui : 5 sur 30")).toBeInTheDocument();
    expect(sent).toEqual([{ card: "c1", body: { result: "ok" } }]);
  });

  it("reviews due cards and skips a 409", async () => {
    const sent = recordReviews((id) =>
      id === "c1"
        ? HttpResponse.json(apiError("card_not_due", "Cette fiche a déjà été revue."), {
            status: 409,
          })
        : reviewOut(id),
    );
    const { user } = setup();
    await screen.findByText("Que fait GET ?");
    await user.click(screen.getByRole("button", { name: /Voir la réponse/ }));
    await user.click(screen.getByRole("button", { name: /Raté/ }));
    expect(await screen.findByText("Que fait PUT ?")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(sent[0]).toEqual({ card: "c1", body: { result: "fail" } });
  });

  it("answers with the keyboard and sends one review for a fast double press", async () => {
    const sent = recordReviews((id) => reviewOut(id));
    const { user } = setup();
    await screen.findByText("Que fait GET ?");
    await user.keyboard(" ");
    await user.keyboard("22"); // le second 2 tombe sur la fiche suivante, encore au recto : sans effet
    expect(await screen.findByText("Que fait PUT ?")).toBeInTheDocument();
    expect(sent).toEqual([{ card: "c1", body: { result: "ok" } }]);
  });

  it("keeps the card and shows the error when the review fails", async () => {
    recordReviews(() => HttpResponse.json(apiError("boom", "Panne du serveur."), { status: 500 }));
    const { user } = setup();
    await screen.findByText("Que fait GET ?");
    await user.click(screen.getByRole("button", { name: /Voir la réponse/ }));
    await user.click(screen.getByRole("button", { name: /Su/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Panne du serveur.");
    expect(screen.getByText("Que fait GET ?")).toBeInTheDocument();
  });

  it("tells when a card demotes a skill", async () => {
    recordReviews((id) => reviewOut(id, { demoted_skill: "REST" }));
    const { user } = setup();
    await screen.findByText("Que fait GET ?");
    await user.click(screen.getByRole("button", { name: /Voir la réponse/ }));
    await user.click(screen.getByRole("button", { name: /Raté/ }));
    expect(
      await screen.findByText(/La compétence « REST » repasse à « En cours »/),
    ).toBeInTheDocument();
  });

  it("ends on an empty state with an action, and says how many cards wait for later", async () => {
    recordReviews((id) => reviewOut(id));
    const { router, user } = setup(
      queue({ cards: [card("c1", "Que fait GET ?", "Il lit.")], remaining_due: 3 }),
    );
    await screen.findByText("Que fait GET ?");
    expect(
      screen.getByText("3 autres fiches seront proposées les jours suivants."),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Voir la réponse/ }));
    await user.click(screen.getByRole("button", { name: /Su/ }));
    expect(
      await screen.findByRole("heading", { name: "Plus aucune fiche à réviser" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Voir les quiz" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/etudier/quiz"));
  });

  it("has an empty state when nothing is due", async () => {
    setup(queue({ cards: [] }));
    expect(
      await screen.findByRole("heading", { name: "Plus aucune fiche à réviser" }),
    ).toBeInTheDocument();
  });

  it("announces the loading", () => {
    setup(() => new Promise<Response>(() => {}));
    expect(screen.getByRole("status")).toHaveTextContent("Chargement des fiches…");
  });

  it("shows an error with a retry button", async () => {
    let calls = 0;
    const { user } = setup(() => {
      calls += 1;
      return calls === 1
        ? HttpResponse.json(apiError("boom", "Panne du serveur."), { status: 500 })
        : HttpResponse.json(queue());
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("Panne du serveur.");
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByText("Que fait GET ?")).toBeInTheDocument();
  });
});
