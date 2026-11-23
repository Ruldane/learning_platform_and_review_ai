import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { BrainConversation } from "./BrainConversation";

const url = "http://localhost:8000/api/v1/brain/conversation";

describe("BrainConversation", () => {
  it("asks the librarian and opens the referenced memory item", async () => {
    const question = "Où sont mes notes sur la recherche ?";
    let asked = false;
    server.use(
      http.get("http://localhost:8000/api/v1/conversations/brain", () => HttpResponse.json([])),
    );
    server.use(
      http.get(url, () =>
        HttpResponse.json(
          asked
            ? {
                id: "cerveau",
                turns: [
                  {
                    id: "tour-1",
                    request_id: "req",
                    session_id: "session-1",
                    status: "completed",
                    question,
                    answer: "Voici ton document sur la recherche.",
                    passage: null,
                    passage_occurrence: null,
                    sources: [
                      { kind: "memory", id: "note-1", title: "Recherche locale", excerpt: null },
                    ],
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
              }
            : null,
        ),
      ),
    );
    server.use(
      http.post(`${url}/messages`, async ({ request }) => {
        expect(request.headers.get("X-Tremplin-Run")).toBe("openai");
        const payload = await request.json();
        expect(payload).toMatchObject({ question, strong: false });
        expect(payload).not.toHaveProperty("passage");
        asked = true;
        return HttpResponse.json({ session_id: "session-1" }, { status: 202 });
      }),
    );
    const { user, router } = renderRoutes(
      [
        { path: "/memoire/cerveau", element: <BrainConversation /> },
        { path: "/memoire", element: <p>Document ouvert</p> },
      ],
      "/memoire/cerveau",
    );

    const input = await screen.findByRole("textbox", { name: "Ta question au Cerveau" });
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Qui fait tourner les agents pour ce lancement" }),
      "openai",
    );
    await user.type(input, `${question}{Enter}`);
    const thread = screen.getByRole("log", { name: "Conversation avec le bibliothécaire" });
    expect(await within(thread).findByText("Voici ton document sur la recherche.")).toBeVisible();
    await user.click(within(thread).getByRole("link", { name: "Recherche locale" }));
    expect(router.state.location.search).toBe("?item=note-1");
  });
});
