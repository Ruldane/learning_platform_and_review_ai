import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { ReviewPage } from "./ReviewPage";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { councilEvents } from "@/test/councilEvents";
import { modificationOut, refusal, reviewOut } from "@/test/cvApi";
import { openStream, renderCv } from "@/test/cvHarness";

/** Monte la revue `rv1` (session `r1`) avec les routes de `cvApi`. */
function renderReview(api: Parameters<typeof renderCv>[3] = {}) {
  return renderCv(
    "/carriere/cv/revues/:reviewId",
    "/carriere/cv/revues/rv1",
    (createSocket) => <ReviewPage pollMs={40} createSocket={createSocket} />,
    api,
  );
}

describe("ReviewPage: reading and deciding", () => {
  beforeEach(() => useSessionStore.getState().reset("r1"));

  it("reads the whole review on one page", async () => {
    const { sockets } = renderReview();
    expect(
      await screen.findByRole("heading", { level: 1, name: "Revue du CV" }),
    ).toBeInTheDocument();
    const stream = await openStream(sockets, "r1");
    stream.push(councilEvents("r1").message("m1", "Je lis ton CV comme un ATS.", "ats_reader"));
    expect(await screen.findByText("Je lis ton CV comme un ATS.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Indicateurs" })).toBeInTheDocument();
    expect(screen.getByText(/Couverture des exigences : 50 %/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Modifications proposées" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Rapport" })).toBeInTheDocument();
    expect(screen.getByText("Logiciel de recrutement détecté : Greenhouse")).toBeInTheDocument();
    expect(
      screen.getByText(/Mots clés de l'offre à appuyer par un fait ou à acquérir : Kubernetes/),
    ).toBeInTheDocument();
  });

  it("decides one modification and quotes the profile fact it rests on", async () => {
    const { user, state } = renderReview({
      profiles: [
        {
          draft: null,
          session_id: null,
          source_document_id: null,
          validated: {
            version: 1,
            status: "validated",
            source: "january",
            created_at: "2026-11-10T10:00:00Z",
            dropped: [],
            data: {
              identity: { name: "Camille Exemple" },
              experiences: [
                {
                  id: "e1",
                  role: "Data engineer",
                  company: "Société Fictive",
                  achievements: [{ id: "a1x", text: "Pipelines de 2 To par jour" }],
                },
              ],
            },
          },
        },
      ],
    });
    const first = (await screen.findAllByRole("article"))[0]!;
    expect(
      await within(first).findByText("Pipelines de 2 To par jour", { selector: "li" }),
    ).toBeInTheDocument();
    await user.click(within(first).getByRole("button", { name: "Accepter" }));
    await waitFor(() => expect(state.patches).toHaveLength(1));
    expect(state.patches[0]).toEqual({ id: "m1", body: { status: "accepted", confirm: false } });
  });

  it("accepts every proposed modification at once, never the ones to confirm", async () => {
    const accepted = reviewOut({
      modifications: [modificationOut("m1", { status: "accepted" }), reviewOut().modifications[1]],
    });
    let done = false;
    const { user, state } = renderReview({
      review: () => HttpResponse.json(done ? accepted : reviewOut()),
      patchBulk: () => {
        done = true;
        return HttpResponse.json({ updated: 1, skipped: ["m2"] });
      },
    });
    await user.click(await screen.findByRole("button", { name: "Tout accepter" }));
    await waitFor(() => expect(state.bulks).toHaveLength(1));
    expect(state.bulks[0]).toEqual({ ids: ["m1"], status: "accepted" });
    expect(await screen.findByText(/1 modification à confirmer une par une/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tout accepter" })).toBeDisabled();
  });

  it("accepts a modification to confirm only with the confirmation", async () => {
    const { user, state } = renderReview();
    await screen.findAllByRole("article");
    const toConfirm = screen.getAllByRole("article")[1]!;
    expect(within(toConfirm).getByText("Outil absent : Kubernetes.")).toBeInTheDocument();
    await user.click(
      within(toConfirm).getByRole("checkbox", { name: "Je confirme que c'est vrai" }),
    );
    await user.click(within(toConfirm).getByRole("button", { name: "Accepter" }));
    await waitFor(() => expect(state.patches).toHaveLength(1));
    expect(state.patches[0]).toEqual({ id: "m2", body: { status: "accepted", confirm: true } });
  });

  it("sends the rewritten text with the decision", async () => {
    const { user, state } = renderReview();
    const first = (await screen.findAllByRole("article"))[0]!;
    await user.click(within(first).getByRole("button", { name: "Modifier" }));
    const field = within(first).getByLabelText("Texte modifié");
    await user.clear(field);
    await user.type(field, "Pipelines de 2 To");
    await user.click(within(first).getByRole("button", { name: "Enregistrer et accepter" }));
    await waitFor(() => expect(state.patches).toHaveLength(1));
    expect(state.patches[0]).toEqual({
      id: "m1",
      body: { status: "accepted", after: "Pipelines de 2 To", confirm: false },
    });
  });

  it("tells that a profile draft is waiting and leads to the profile page", async () => {
    const { user } = renderReview({
      patchModification: () => refusal(409, "profile_draft_pending", "Un brouillon attend.", null),
    });
    await screen.findAllByRole("article");
    const toConfirm = screen.getAllByRole("article")[1]!;
    await user.click(
      within(toConfirm).getByRole("checkbox", { name: "Je confirme que c'est vrai" }),
    );
    await user.click(within(toConfirm).getByRole("button", { name: "Accepter" }));
    expect(
      await screen.findByText(
        "Un brouillon de ton profil attend ta validation : valide-le avant de confirmer ce fait.",
      ),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Valider mon profil" }));
    expect(await screen.findByText("Page du profil")).toBeInTheDocument();
  });

  it("shows a readable error when a decision is refused", async () => {
    const { user } = renderReview({
      patchModification: () => refusal(409, "review_closed", "Revue terminée."),
    });
    const first = (await screen.findAllByRole("article"))[0]!;
    await user.click(within(first).getByRole("button", { name: "Refuser" }));
    expect(
      await screen.findByText(
        "Cette revue est terminée : lance une nouvelle revue pour un nouveau PDF.",
      ),
    ).toBeInTheDocument();
  });

  it("freezes the decisions once the review is done", async () => {
    renderReview({ reviews: [reviewOut({ status: "done", waiting_output: false })] });
    expect(
      await screen.findByText(/La revue est terminée : les décisions sont figées/),
    ).toBeInTheDocument();
    const [first] = await screen.findAllByRole("article");
    expect(within(first!).getByRole("button", { name: "Accepter" })).toBeDisabled();
  });
});

describe("ReviewPage: states", () => {
  it("shows a loading state, then the review", async () => {
    renderReview();
    expect(screen.getByText("Chargement de la revue…")).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { level: 1, name: "Revue du CV" }),
    ).toBeInTheDocument();
  });

  it("offers an action when the review does not exist", async () => {
    const { user } = renderReview({
      review: () => refusal(404, "review_not_found", "Introuvable."),
    });
    expect(await screen.findByText("Revue introuvable")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Voir mes versions" }));
    expect(await screen.findByText("Page des versions")).toBeInTheDocument();
  });

  it("shows an error with « Réessayer »", async () => {
    let failing = true;
    const { user } = renderReview({
      review: () =>
        failing ? HttpResponse.json({}, { status: 500 }) : HttpResponse.json(reviewOut()),
    });
    expect(await screen.findByRole("alert", {}, { timeout: 3000 })).toBeInTheDocument();
    failing = false;
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(
      await screen.findByRole("heading", { level: 1, name: "Revue du CV" }),
    ).toBeInTheDocument();
  });
});
