import { act, screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { useLocation } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { API, lessonOut } from "@/test/lessonsApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { LessonPage } from "./LessonPage";

vi.mock("mermaid", () => ({ default: { initialize: vi.fn(), render: vi.fn() } }));

function Arrived() {
  const { state } = useLocation();
  return <p>Arrivé : {JSON.stringify(state)}</p>;
}

function setup(lesson: Record<string, unknown> = lessonOut()) {
  server.use(http.get(`${API}/lessons/l1`, () => HttpResponse.json(lesson)));
  return renderRoutes(
    [
      { path: "/apprendre/lecons/:lessonId", element: <LessonPage /> },
      { path: "/etudier/session", element: <Arrived /> },
    ],
    "/apprendre/lecons/l1",
  );
}

describe("LessonPage: étudier avec le tuteur", () => {
  it("asks the tutor about a selected passage through the navigation state", async () => {
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
    await user.click(screen.getByRole("button", { name: "Demander au tuteur" }));
    expect(router.state.location.pathname).toBe("/etudier/session");
    expect(router.state.location.state).toEqual({
      lessonId: "l1",
      question: "Une variable nomme une valeur.",
    });
    window.getSelection()!.removeAllRanges();
  });

  it("links a ready lesson to a guided session on it", async () => {
    setup();
    expect(await screen.findByRole("link", { name: "Étudier cette leçon" })).toHaveAttribute(
      "href",
      "/etudier/session?lecon=l1",
    );
  });

  it("does not offer to study a lesson that is not ready", async () => {
    setup(lessonOut({ status: "pending", markdown: "" }));
    await screen.findByRole("link", { name: "Toutes les leçons" });
    expect(screen.queryByRole("link", { name: "Étudier cette leçon" })).not.toBeInTheDocument();
  });
});
