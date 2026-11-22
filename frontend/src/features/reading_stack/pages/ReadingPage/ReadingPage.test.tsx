import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { ReadingPage } from "./ReadingPage";

const api = "http://localhost:8000/api/v1/reading-stack";
const article = {
  id: "article",
  kind: "article",
  title: "Un article d’essai",
  url: "https://example.org/article",
  summary: "Un sujet suivi.",
  text: "Le texte lisible de l’article.",
  reason: "Python",
  company: null,
  created_at: "2026-11-22T07:30:00Z",
  read_at: null as string | null,
};

describe("ReadingPage", () => {
  it("opens an article and reflects the saved read state", async () => {
    let read = false;
    const detail = () => ({ ...article, read_at: read ? article.created_at : null });
    server.use(
      http.get(api, () =>
        HttpResponse.json({
          items: read ? [] : [detail()],
          unread_count: Number(!read),
          next_offset: null,
        }),
      ),
      http.get(`${api}/article`, () => HttpResponse.json(detail())),
      http.patch(`${api}/article`, async ({ request }) => {
        expect(await request.json()).toEqual({ read: true });
        read = true;
        return HttpResponse.json(detail());
      }),
    );
    const { user } = renderRoutes(
      [{ path: "/memoire/lecture/:itemId?", element: <ReadingPage /> }],
      "/memoire/lecture",
    );
    await user.click(await screen.findByRole("link", { name: article.title }));
    expect(await screen.findByText(article.text)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Marquer comme lu" }));
    expect(await screen.findByRole("button", { name: "Marquer comme non lu" })).toBeEnabled();
  });
});
