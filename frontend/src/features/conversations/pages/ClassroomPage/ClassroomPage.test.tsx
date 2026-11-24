import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Link } from "react-router";
import { expect, it } from "vitest";
import type { components } from "@/shared/api/schema";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { ClassroomPage } from "./ClassroomPage";

const lesson = "/apprendre/lecons/l1";
const classroom = lesson + "/classe";
const endpoint = "http://localhost:8000/api/v1/lessons/l1/classroom";
const explanation = "La chaîne relie chaque résultat à l’étape suivante.";
const response: components["schemas"]["LessonConversationOut"] = {
  id: "classe",
  lesson_id: "l1",
  turns: [
    {
      id: "tour-1",
      request_id: "req-1",
      session_id: "session-1",
      question: explanation,
      answer: "Trois répliques",
      classmates: [
        { role: "beginner", answer: "Peux-tu donner un exemple ?" },
        { role: "peer", answer: "En quoi les étapes diffèrent-elles ?" },
        { role: "advanced", answer: "Quel cas limite mets-tu à l’épreuve ?" },
      ],
      status: "completed",
      passage: null,
      passage_occurrence: null,
      sources: [{ kind: "lesson", id: "l1", title: "Les chaînes", excerpt: null }],
    },
  ],
  usage: {
    thread_tokens: 20,
    thread_token_limit: 100_000,
    day_tokens: 20,
    day_token_limit: 300_000,
    turns: 1,
    turn_limit: 100,
  },
};

it("shows all three roles and keeps the lesson source on return", async () => {
  let sent = false;
  server.use(
    http.get(endpoint, () => HttpResponse.json(sent ? response : null)),
    http.post(endpoint + "/messages", async ({ request }) => {
      expect(await request.json()).toMatchObject({ question: explanation });
      sent = true;
      return HttpResponse.json({ session_id: "session-1" }, { status: 202 });
    }),
  );
  const { user, router } = renderRoutes(
    [
      { path: "/apprendre/lecons/:lessonId/classe", Component: ClassroomPage },
      { path: lesson, element: <Link to={classroom}>Reprendre la classe</Link> },
    ],
    classroom,
  );
  const input = await screen.findByRole("textbox", { name: "Your explanation" });
  await user.type(input, explanation + "{Enter}");
  const thread = screen.getByRole("log", { name: "Class discussion" });
  expect(await within(thread).findByText("Beginner classmate")).toBeVisible();
  expect(within(thread).getByText("Classmate at your level")).toBeVisible();
  expect(within(thread).getByText("Advanced classmate")).toBeVisible();
  await user.click(within(thread).getByRole("link", { name: "Les chaînes" }));
  expect(router.state.location.pathname).toBe(lesson);
  await user.click(screen.getByRole("link", { name: "Reprendre la classe" }));
  expect(await screen.findByText("Quel cas limite mets-tu à l’épreuve ?")).toBeVisible();
});
