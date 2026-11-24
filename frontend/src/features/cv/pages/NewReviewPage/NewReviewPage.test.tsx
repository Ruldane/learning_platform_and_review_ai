import { screen } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { refusal } from "@/test/cvApi";
import { renderCv } from "@/test/cvHarness";
import { NewReviewPage } from "./NewReviewPage";

function setup(api: Parameters<typeof renderCv>[3] = {}, runSource?: string) {
  return renderCv(
    "/career/cv/reviews/new/:postingId",
    { pathname: "/career/cv/reviews/new/p1", state: { runSource } },
    () => <NewReviewPage />,
    api,
  );
}

describe("NewReviewPage", () => {
  it("starts the review once and opens it", async () => {
    const sources: (string | null)[] = [];
    const { state } = setup(
      {
        startReview: (request) => {
          sources.push(request.headers.get("X-Tremplin-Run"));
          return HttpResponse.json({ review_id: "rv1", session_id: "r1" }, { status: 202 });
        },
      },
      "codex",
    );
    expect(await screen.findByText("Page de la revue")).toBeInTheDocument();
    expect(state.starts).toBe(1);
    expect(sources).toEqual(["codex"]);
  });

  it("says to validate the profile first, with the way to do it", async () => {
    const { user } = setup({
      startReview: () => refusal(409, "profile_required", "Aucun profil validé."),
    });
    expect(await screen.findByText("Valide ton profil d'abord")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Valider mon profil" }));
    expect(await screen.findByText("Page du profil")).toBeInTheDocument();
  });

  it("says to create a template first, with the way to do it", async () => {
    const { user } = setup({
      startReview: () => refusal(409, "template_required", "Aucun modèle actif."),
    });
    expect(await screen.findByText("Crée ton modèle de CV d'abord")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Créer mon modèle" }));
    expect(await screen.findByText("Page des modèles")).toBeInTheDocument();
  });

  it("sends back to the posting while it is not analysed", async () => {
    const { user } = setup({
      startReview: () => refusal(409, "posting_not_ready", "Offre pas prête."),
    });
    expect(await screen.findByText("L'offre n'est pas encore analysée")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Voir l'offre" }));
    expect(await screen.findByText("Page de l'offre")).toBeInTheDocument();
  });

  it("opens the review already in progress for this posting", async () => {
    setup({
      startReview: () =>
        refusal(409, "review_in_progress", "Une revue est en cours.", { review_id: "rv1" }),
    });
    expect(await screen.findByText("Page de la revue")).toBeInTheDocument();
  });

  it("shows an error with « Réessayer » and starts again", async () => {
    let failing = true;
    const { user, state } = setup({
      startReview: () =>
        failing
          ? refusal(503, "engine_unavailable", "Moteur indisponible.")
          : HttpResponse.json({ review_id: "rv1", session_id: "r1" }, { status: 202 }),
    });
    expect(
      await screen.findByText(
        "Le moteur d'agents n'est pas disponible : réessaie dans un instant.",
      ),
    ).toBeInTheDocument();
    failing = false;
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByText("Page de la revue")).toBeInTheDocument();
    expect(state.starts).toBe(2);
  });
});
