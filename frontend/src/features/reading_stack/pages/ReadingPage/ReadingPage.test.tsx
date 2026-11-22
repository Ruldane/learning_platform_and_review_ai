import { fireEvent, screen } from "@testing-library/react";
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
  it("refuses an oversized selection, then submits the shortened passage verbatim", async () => {
    const valid = "y".repeat(1199) + "🌱";
    const text = valid + "z";
    const calls: unknown[] = [];
    server.use(
      http.get(api, () =>
        HttpResponse.json({ items: [article], unread_count: 1, next_offset: null }),
      ),
      http.get(api + "/article", () => HttpResponse.json({ ...article, text })),
      http.post(api + "/article/cards", async ({ request }) => {
        calls.push(await request.json());
        return HttpResponse.json({ count: 1 });
      }),
    );
    const { user } = renderRoutes(
      [{ path: "/memoire/lecture/:itemId?", element: <ReadingPage /> }],
      "/memoire/lecture/article",
    );
    const readable = await screen.findByText(text);
    const select = (end: number) => {
      const range = document.createRange();
      range.setStart(readable.firstChild!, 0);
      range.setEnd(readable.firstChild!, end);
      const selection = document.getSelection()!;
      selection.removeAllRanges();
      selection.addRange(range);
      fireEvent(document, new Event("selectionchange"));
    };
    const button = screen.getByRole("button", { name: "Créer une fiche de ce passage" });
    select(text.length);
    expect(screen.getByText(/1\s?200 caractères/)).toBeVisible();
    expect(button).toBeDisabled();
    expect(calls).toEqual([]);

    select(valid.length);
    expect(button).toBeEnabled();
    await user.click(button);
    expect(await screen.findByText("La fiche est prête à réviser.")).toBeVisible();
    expect(calls).toEqual([{ passage: valid }]);
  });
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
