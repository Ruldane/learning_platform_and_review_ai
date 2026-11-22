import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { LessonConversation } from "./LessonConversation";

const lessonId = "510ee442-9357-4ae3-88b3-93225564babc";
const api = `http://localhost:8000/api/v1/lessons/${lessonId}/conversation`;

function setup() {
  const close = vi.fn();
  const { user } = renderRoutes(
    [
      {
        path: "/lecon",
        element: (
          <LessonConversation
            lessonId={lessonId}
            passage={{ text: "Une valeur.", occurrence: 1 }}
            onClose={close}
          />
        ),
      },
    ],
    "/lecon",
  );
  return { close, user };
}

describe("LessonConversation", () => {
  it("reloads the thread and links to a cited memory item", async () => {
    server.use(
      http.get(api, () =>
        HttpResponse.json({
          id: "fil",
          lesson_id: lessonId,
          turns: [
            {
              id: "tour",
              request_id: "requete",
              session_id: "session",
              question: "Que représente la valeur ?",
              passage: "Une valeur.",
              answer:
                "C’est le **contenu** de la variable. [Lien produit par le modèle](https://example.org)",
              status: "completed",
              sources: [{ kind: "memory", id: "mem1", title: "Note de cours", excerpt: null }],
            },
          ],
          usage: {
            thread_tokens: 12,
            thread_token_limit: 100000,
            day_tokens: 34,
            day_token_limit: 300000,
            turns: 1,
            turn_limit: 100,
          },
        }),
      ),
    );
    const { user, close } = setup();
    const panel = screen.getByRole("dialog", { name: "Professeur" });
    expect(within(panel).getByRole("heading", { name: "Professeur" })).toHaveFocus();
    expect(await within(panel).findByText("contenu")).toBeVisible();
    expect(within(panel).getByText("Que représente la valeur ?")).toBeVisible();
    expect(within(panel).queryByRole("link", { name: "Lien produit par le modèle" })).toBeNull();
    expect(within(panel).getByRole("link", { name: "Note de cours" })).toHaveAttribute(
      "href",
      "/memoire?item=mem1",
    );
    await user.keyboard("{Escape}");
    expect(close).toHaveBeenCalledOnce();
  });

  it("keeps a rejected question and reuses its request ID when sending again", async () => {
    const incoming: unknown[] = [];
    server.use(http.get(api, () => HttpResponse.json(null)));
    server.use(
      http.post(`${api}/messages`, async ({ request }) => {
        incoming.push(await request.json());
        return HttpResponse.error();
      }),
    );
    const { user } = setup();
    const input = await screen.findByRole("textbox", { name: "Ta question" });
    await user.type(input, "Comment ?{Enter}");
    await screen.findByRole("alert");
    expect(input).toHaveValue("Comment ?");
    await user.click(screen.getByRole("button", { name: "Envoyer" }));
    await waitFor(() => expect(incoming).toHaveLength(2));
    expect(incoming[0]).toMatchObject({
      question: "Comment ?",
      passage: "Une valeur.",
      passage_occurrence: 1,
      strong: false,
    });
    expect(incoming[0]).toHaveProperty("request_id", expect.any(String));
    expect(incoming[1]).toEqual(incoming[0]);
  });
});
