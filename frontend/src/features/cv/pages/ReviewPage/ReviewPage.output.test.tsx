import { screen, waitFor } from "@testing-library/react";
import { delay, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { ReviewPage } from "./ReviewPage";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { sessionOut } from "@/test/councilApi";
import { recordPosts } from "@/test/councilHarness";
import { refusal, reviewOut, versionOut } from "@/test/cvApi";
import { renderCv } from "@/test/cvHarness";
import { askOutput } from "@/test/cvReviewKit";

/** Monte la revue `rv1` (session `r1`) avec les routes de `cvApi`. */
function renderReview(api: Parameters<typeof renderCv>[3] = {}) {
  return renderCv(
    "/career/cv/reviews/:reviewId",
    "/career/cv/reviews/rv1",
    (createSocket) => <ReviewPage pollMs={40} createSocket={createSocket} />,
    api,
  );
}

const exceeded = versionOut({ status: "pages_exceeded", page_count: 2, indicators: null });

describe("ReviewPage: the output question", () => {
  beforeEach(() => useSessionStore.getState().reset("r1"));

  it("shows the three buttons once the question is asked, even after a reload", async () => {
    const { sockets } = renderReview();
    await screen.findByRole("heading", { level: 1, name: "Revue du CV" });
    expect(screen.queryByRole("button", { name: "Générer le PDF" })).not.toBeInTheDocument();
    // Un rechargement rouvre le flux : la question est rejouée et les boutons reviennent.
    await askOutput(sockets);
    expect(screen.getByRole("button", { name: "Voir le rapport" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Générer le PDF" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Terminer" })).toBeEnabled();
  });

  it("generates once on a double click, and greys the buttons while it renders", async () => {
    let started = false;
    const { sockets, user, state } = renderReview({
      review: () =>
        HttpResponse.json(
          started
            ? reviewOut({
                waiting_output: false,
                versions: [versionOut({ status: "rendering", page_count: null, indicators: null })],
              })
            : reviewOut(),
        ),
      generate: async () => {
        await delay(60);
        started = true;
        return HttpResponse.json({ version_id: "v1" }, { status: 202 });
      },
    });
    await askOutput(sockets);
    await user.dblClick(screen.getByRole("button", { name: "Générer le PDF" }));
    expect(await screen.findByText("Génération du PDF en cours…")).toBeInTheDocument();
    expect(state.generates).toHaveLength(1);
    expect(state.generates[0]).toEqual({ allow_extra_pages: false });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Générer le PDF" })).toBeDisabled(),
    );
  });

  it("says a generation is already running when the back answers 409", async () => {
    const { sockets, user } = renderReview({
      generate: () =>
        refusal(409, "generation_in_progress", "Déjà en cours.", { version_id: "v1" }),
    });
    await askOutput(sockets);
    await user.click(screen.getByRole("button", { name: "Générer le PDF" }));
    expect(
      await screen.findByText("Un PDF est déjà en cours de génération pour cette revue."),
    ).toBeInTheDocument();
  });

  it("previews the latest version and links its PDF under the CV_… name", async () => {
    renderReview({
      reviews: [reviewOut({ versions: [versionOut()], waiting_output: false })],
    });
    expect(await screen.findByAltText("Page 1 sur 1 du CV")).toHaveAttribute(
      "src",
      expect.stringContaining("/api/v1/cv/versions/v1/pages/1"),
    );
    const link = screen.getByRole("link", {
      name: "Télécharger CV_Camille_Exemple_Societe_Fictive.pdf",
    });
    expect(link).toHaveAttribute("href", expect.stringContaining("/api/v1/cv/versions/v1/pdf"));
    expect(link).toHaveAttribute("download", "CV_Camille_Exemple_Societe_Fictive.pdf");
    // Les indicateurs « après » sont ceux de cette version.
    expect(screen.getByText(/Couverture des exigences : 50 % → 75 %/)).toBeInTheDocument();
  });

  it("offers one more page when the CV is too long, then regenerates with it", async () => {
    const { sockets, user, state } = renderReview({
      reviews: [reviewOut({ versions: [exceeded] })],
    });
    await askOutput(sockets);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Le CV ciblé fait 2 pages, ton CV d'origine 1 page.",
    );
    await user.click(screen.getByRole("button", { name: "Autoriser une page de plus" }));
    await waitFor(() => expect(state.generates).toHaveLength(1));
    expect(state.generates[0]).toEqual({ allow_extra_pages: true });
  });

  it("never says « 0 pages » when the rendered page count is missing", async () => {
    const unknown = versionOut({
      status: "pages_exceeded",
      page_count: null,
      original_page_count: 2,
      indicators: null,
    });
    const { sockets } = renderReview({ reviews: [reviewOut({ versions: [unknown] })] });
    await askOutput(sockets);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Le CV ciblé est plus long que ton CV d'origine (2 pages).");
    expect(alert).not.toHaveTextContent("0 page");
  });

  it("says why a rendering failed and lets the user try again", async () => {
    const failed = versionOut({
      status: "failed",
      page_count: null,
      failure_reason: "Le rendu a échoué.",
      indicators: null,
    });
    const { sockets, user, state } = renderReview({ reviews: [reviewOut({ versions: [failed] })] });
    await askOutput(sockets);
    expect(await screen.findByText("Le rendu a échoué.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Réessayer la génération" }));
    await waitFor(() => expect(state.generates).toHaveLength(1));
  });

  it("answers « Terminer » through the session, never through the generate route", async () => {
    const { sockets, user, state } = renderReview();
    const resumes = recordPosts("/sessions/r1/resume", 200, sessionOut("r1", "running"));
    await askOutput(sockets);
    await user.click(screen.getByRole("button", { name: "Terminer" }));
    await waitFor(() => expect(resumes).toHaveLength(1));
    expect(resumes[0]).toEqual({ interrupt_id: "o1", value: "finish" });
    expect(state.generates).toHaveLength(0);
  });

  it("answers « Voir le rapport » through the session and shows the report", async () => {
    const { sockets, user } = renderReview();
    const resumes = recordPosts("/sessions/r1/resume", 200, sessionOut("r1", "running"));
    await askOutput(sockets);
    await user.click(screen.getByRole("button", { name: "Voir le rapport" }));
    await waitFor(() => expect(resumes).toHaveLength(1));
    expect(resumes[0]).toEqual({ interrupt_id: "o1", value: "report" });
    expect(screen.getByRole("heading", { name: "Rapport" })).toBeInTheDocument();
  });

  it("report button moves focus to the report title", async () => {
    const { sockets, user } = renderReview();
    recordPosts("/sessions/r1/resume", 200, sessionOut("r1", "running"));
    await askOutput(sockets);
    await user.click(screen.getByRole("button", { name: "Voir le rapport" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Rapport" })).toHaveFocus());
  });
});
