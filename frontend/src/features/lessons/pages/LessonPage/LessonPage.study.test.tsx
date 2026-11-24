import { act, screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { API, lessonOut } from "@/test/lessonsApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import type { LessonPassage } from "@/shared/lib/lessonPassage";
import { LessonPage } from "./LessonPage";

vi.mock("mermaid", () => ({ default: { initialize: vi.fn(), render: vi.fn() } }));

function Conversation({
  passage,
  onClose,
}: {
  passage: LessonPassage | null;
  onClose: () => void;
}) {
  return (
    <section role="dialog" aria-label="Professor">
      <p>{passage?.text}</p>
      <button type="button" onClick={onClose}>
        Close conversation
      </button>
    </section>
  );
}

function setup(lesson: Record<string, unknown> = lessonOut()) {
  server.use(http.get(`${API}/lessons/l1`, () => HttpResponse.json(lesson)));
  return renderRoutes(
    [
      {
        path: "/apprendre/lecons/:lessonId",
        element: <LessonPage conversationPanel={Conversation} />,
      },
    ],
    "/apprendre/lecons/l1",
  );
}

describe("LessonPage: studying with the tutor", () => {
  it("opens the selected passage in the lesson and restores focus on close", async () => {
    const { router, user } = setup();
    const body = await screen.findByTestId("lesson-body");
    const text = within(body).getByText("Une variable nomme une valeur.");
    const range = document.createRange();
    range.selectNodeContents(text);
    window.getSelection()!.removeAllRanges();
    window.getSelection()!.addRange(range);
    act(() => {
      document.dispatchEvent(new Event("selectionchange"));
    });
    const ask = screen.getByRole("button", { name: "Ask the professor" });
    ask.focus();
    await user.keyboard("{Enter}");
    expect(router.state.location.pathname).toBe("/apprendre/lecons/l1");
    const dialog = await screen.findByRole("dialog", { name: "Professor" });
    expect(within(dialog).getByText("Une variable nomme une valeur.")).toBeVisible();
    await user.click(within(dialog).getByRole("button", { name: "Close conversation" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open the conversation with the professor" }),
    ).toHaveFocus();
    window.getSelection()!.removeAllRanges();
  });

  it("links a ready lesson to a guided session on it", async () => {
    setup();
    expect(await screen.findByRole("link", { name: "Study this lesson" })).toHaveAttribute(
      "href",
      "/etudier/session?lecon=l1",
    );
  });

  it("does not offer to study a lesson that is not ready", async () => {
    setup(lessonOut({ status: "pending", markdown: "" }));
    await screen.findByRole("link", { name: "All lessons" });
    expect(screen.queryByRole("link", { name: "Study this lesson" })).not.toBeInTheDocument();
  });
});
