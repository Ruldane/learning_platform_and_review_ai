import { screen, within } from "@testing-library/react";
import { http, HttpResponse, ws } from "msw";
import { describe, expect, it } from "vitest";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { sessionOut } from "@/test/councilApi";
import { OffersConversation } from "./OffersConversation";

const API = "http://localhost:8000/api/v1/conversations/offers";
const SESSION = "http://localhost:8000/api/v1/sessions/offers-session";
const stream = ws.link("ws://localhost:8000/api/v1/sessions/offers-session/stream");
const usage = {
  thread_tokens: 20,
  thread_token_limit: 100_000,
  day_tokens: 20,
  day_token_limit: 300_000,
  turns: 1,
  turn_limit: 100,
};
const updated_at = "2026-11-24T10:00:00Z";
const question = "When did I add the Northwind offer?";
const saved = { id: "old-chat", title: "Northwind search", updated_at };

function setup() {
  let created = false;
  let sent = false;
  server.use(
    stream.addEventListener("connection", () => undefined),
    http.get(SESSION, () => HttpResponse.json(sessionOut("offers-session", "completed"))),
    http.get(API, () =>
      HttpResponse.json(
        created ? [{ id: "new-chat", title: question, updated_at }, saved] : [saved],
      ),
    ),
    http.get(`${API}/old-chat`, () => HttpResponse.json({ id: saved.id, turns: [], usage })),
    http.post(API, () => {
      created = true;
      return HttpResponse.json({ id: "new-chat", turns: [], usage }, { status: 201 });
    }),
    http.post(`${API}/new-chat/messages`, async ({ request }) => {
      expect(await request.json()).toMatchObject({ question, strong: false });
      sent = true;
      return HttpResponse.json({ session_id: "offers-session" }, { status: 202 });
    }),
    http.get(`${API}/new-chat`, () =>
      HttpResponse.json({
        id: "new-chat",
        usage,
        turns: sent
          ? [
              {
                id: "turn",
                request_id: "request",
                session_id: "offers-session",
                status: "completed",
                question,
                answer: "You added it on 2 November.",
                passage: null,
                passage_occurrence: null,
                sources: [
                  { kind: "posting", id: "northwind", title: "Northwind offer" },
                  { kind: "application", id: "application-1", title: "Northwind application" },
                ],
              },
            ]
          : [],
      }),
    ),
  );
  return renderRoutes(
    [{ path: "/career/postings", element: <OffersConversation /> }],
    "/career/postings",
  );
}

describe("OffersConversation", () => {
  it("opens the saved chats, creates a chat, reads a reply, and restores focus", async () => {
    const { user } = setup();
    const trigger = screen.getByRole("button", { name: "Ask about offers" });
    await user.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Offers chat" });
    await within(dialog).findByRole("button", { name: "Open Northwind search" });
    await user.click(within(dialog).getByRole("button", { name: "New chat" }));
    const input = await within(dialog).findByRole("textbox", {
      name: "Your question about offers",
    });
    await user.type(input, `${question}{Enter}`);
    const answer = await within(dialog).findByText("You added it on 2 November.");
    expect(answer).toBeVisible();
    expect(within(dialog).getByRole("link", { name: "Northwind offer" })).toHaveAttribute(
      "href",
      "/career/postings/northwind",
    );
    expect(within(dialog).getByRole("link", { name: "Northwind application" })).toHaveAttribute(
      "href",
      "/applications/application-1",
    );
    await user.click(within(dialog).getByRole("button", { name: "Open Northwind search" }));
    expect(within(dialog).queryByText("You added it on 2 November.")).not.toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    await user.click(trigger);
    expect(await screen.findByText("You added it on 2 November.")).toBeVisible();
  });
});
