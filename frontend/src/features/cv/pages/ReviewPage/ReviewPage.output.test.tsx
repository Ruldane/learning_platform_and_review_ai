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

/** Render review `rv1` (session `r1`) using the `cvApi` handlers. */
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
    await screen.findByRole("heading", { level: 1, name: "CV review" });
    expect(screen.queryByRole("button", { name: "Generate PDF" })).not.toBeInTheDocument();
    // Reloading reopens the stream and replays the question with its buttons.
    await askOutput(sockets);
    expect(screen.getByRole("button", { name: "View the report" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Generate PDF" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Finish" })).toBeEnabled();
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
    await user.dblClick(screen.getByRole("button", { name: "Generate PDF" }));
    expect(await screen.findByText("Generating PDF…")).toBeInTheDocument();
    expect(state.generates).toHaveLength(1);
    expect(state.generates[0]).toEqual({ allow_extra_pages: false });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Generate PDF" })).toBeDisabled(),
    );
  });

  it("says a generation is already running when the back answers 409", async () => {
    const { sockets, user } = renderReview({
      generate: () =>
        refusal(409, "generation_in_progress", "Already in progress.", { version_id: "v1" }),
    });
    await askOutput(sockets);
    await user.click(screen.getByRole("button", { name: "Generate PDF" }));
    expect(
      await screen.findByText("A PDF is already being generated for this review."),
    ).toBeInTheDocument();
  });

  it("previews the latest version and links its PDF under the CV_… name", async () => {
    renderReview({
      reviews: [reviewOut({ versions: [versionOut()], waiting_output: false })],
    });
    expect(await screen.findByAltText("Page 1 of 1 of the CV")).toHaveAttribute(
      "src",
      expect.stringContaining("/api/v1/cv/versions/v1/pages/1"),
    );
    const link = screen.getByRole("link", {
      name: "Download CV_Camille_Exemple_Societe_Fictive.pdf",
    });
    expect(link).toHaveAttribute("href", expect.stringContaining("/api/v1/cv/versions/v1/pdf"));
    expect(link).toHaveAttribute("download", "CV_Camille_Exemple_Societe_Fictive.pdf");
    // The after indicators belong to this version.
    expect(screen.getByText(/Requirement coverage: 50% → 75%/)).toBeInTheDocument();
  });

  it("offers one more page when the CV is too long, then regenerates with it", async () => {
    const { sockets, user, state } = renderReview({
      reviews: [reviewOut({ versions: [exceeded] })],
    });
    await askOutput(sockets);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The targeted CV is 2 pages, your original CV 1 page.",
    );
    await user.click(screen.getByRole("button", { name: "Allow one more page" }));
    await waitFor(() => expect(state.generates).toHaveLength(1));
    expect(state.generates[0]).toEqual({ allow_extra_pages: true });
  });

  it("never says 0 pages when the rendered page count is missing", async () => {
    const unknown = versionOut({
      status: "pages_exceeded",
      page_count: null,
      original_page_count: 2,
      indicators: null,
    });
    const { sockets } = renderReview({ reviews: [reviewOut({ versions: [unknown] })] });
    await askOutput(sockets);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("The targeted CV is longer than your original CV (2 pages).");
    expect(alert).not.toHaveTextContent("0 page");
  });

  it("says why a rendering failed and lets the user try again", async () => {
    const failed = versionOut({
      status: "failed",
      page_count: null,
      failure_reason: "Rendering failed.",
      indicators: null,
    });
    const { sockets, user, state } = renderReview({ reviews: [reviewOut({ versions: [failed] })] });
    await askOutput(sockets);
    expect(await screen.findByText("Rendering failed.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry generation" }));
    await waitFor(() => expect(state.generates).toHaveLength(1));
  });

  it("submits Finish through the session", async () => {
    const { sockets, user, state } = renderReview();
    const resumes = recordPosts("/sessions/r1/resume", 200, sessionOut("r1", "running"));
    await askOutput(sockets);
    await user.click(screen.getByRole("button", { name: "Finish" }));
    await waitFor(() => expect(resumes).toHaveLength(1));
    expect(resumes[0]).toEqual({ interrupt_id: "o1", value: "finish" });
    expect(state.generates).toHaveLength(0);
  });

  it("submits View the report through the session and shows the report", async () => {
    const { sockets, user } = renderReview();
    const resumes = recordPosts("/sessions/r1/resume", 200, sessionOut("r1", "running"));
    await askOutput(sockets);
    await user.click(screen.getByRole("button", { name: "View the report" }));
    await waitFor(() => expect(resumes).toHaveLength(1));
    expect(resumes[0]).toEqual({ interrupt_id: "o1", value: "report" });
    expect(screen.getByRole("heading", { name: "Report" })).toBeInTheDocument();
  });

  it("report button moves focus to the report title", async () => {
    const { sockets, user } = renderReview();
    recordPosts("/sessions/r1/resume", 200, sessionOut("r1", "running"));
    await askOutput(sockets);
    await user.click(screen.getByRole("button", { name: "View the report" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Report" })).toHaveFocus());
  });
});
