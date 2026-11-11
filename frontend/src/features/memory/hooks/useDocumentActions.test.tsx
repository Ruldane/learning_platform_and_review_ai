import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { API, apiError, documentOut, sessionOut } from "../fixtures";
import { useDocumentActions } from "./useDocumentActions";

const created = (duplicate: boolean) => ({ document: documentOut(), duplicate });

/**
 * Sous jsdom, lire le corps d'une requête qui contient un `File` ne se termine jamais (jsdom et
 * undici ne partagent pas la classe `File`) : pour un fichier on ne regarde que l'en-tête.
 */
function captureMultipart(readBody: boolean) {
  const captured: { type: string; body: string } = { type: "", body: "" };
  server.use(
    http.post(`${API}/documents`, async ({ request }) => {
      captured.type = request.headers.get("content-type") ?? "";
      if (readBody) captured.body = await request.text();
      return HttpResponse.json(created(false), { status: 202 });
    }),
  );
  return captured;
}

describe("useDocumentActions", () => {
  beforeEach(() => server.use(http.get(`${API}/sessions`, () => HttpResponse.json([]))));

  it("sends a file as multipart and counts the success", async () => {
    const captured = captureMultipart(false);
    const { result } = renderHook(() => useDocumentActions(), { wrapper: createQueryWrapper() });
    const file = new File(["%PDF"], "cours.pdf", { type: "application/pdf" });
    act(() => result.current.upload.mutate({ kind: "file", file }));
    await waitFor(() => expect(result.current.sent).toBe(1));
    expect(captured.type).toMatch(/^multipart\/form-data; boundary=/);
    expect(result.current.duplicate).toBe(false);
  });

  it("sends a link as a form field", async () => {
    const captured = captureMultipart(true);
    const { result } = renderHook(() => useDocumentActions(), { wrapper: createQueryWrapper() });
    act(() => result.current.upload.mutate({ kind: "url", url: "https://exemple.fr/a" }));
    await waitFor(() => expect(result.current.sent).toBe(1));
    expect(captured.type).toMatch(/^multipart\/form-data; boundary=/);
    expect(captured.body).toContain('name="url"');
    expect(captured.body).toContain("https://exemple.fr/a");
  });

  it("sends pasted text as JSON to /documents/text, without an empty title", async () => {
    const bodies: unknown[] = [];
    server.use(
      http.post(`${API}/documents/text`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(created(true), { status: 200 });
      }),
    );
    const { result } = renderHook(() => useDocumentActions(), { wrapper: createQueryWrapper() });
    act(() => result.current.upload.mutate({ kind: "text", text: "Bonjour", title: "  " }));
    await waitFor(() => expect(result.current.sent).toBe(1));
    expect(bodies).toEqual([{ text: "Bonjour", title: null }]);
    expect(result.current.duplicate).toBe(true);
  });

  it("keeps the count still when the upload fails", async () => {
    server.use(
      http.post(`${API}/documents/text`, () => apiError("paste_too_long", "Texte trop long.", 413)),
    );
    const { result } = renderHook(() => useDocumentActions(), { wrapper: createQueryWrapper() });
    act(() => result.current.upload.mutate({ kind: "text", text: "x", title: "" }));
    await waitFor(() => expect(result.current.upload.isError).toBe(true));
    expect(result.current.sent).toBe(0);
    expect(result.current.upload.error?.message).toBe("Texte trop long.");
  });

  it("starts the Archiviste and tracks the session until it finishes", async () => {
    server.use(
      http.post(`${API}/documents/d1/learned`, () =>
        HttpResponse.json({ session_id: "s1" }, { status: 202 }),
      ),
      http.get(`${API}/documents`, () => HttpResponse.json([])),
    );
    const { result } = renderHook(() => useDocumentActions(), { wrapper: createQueryWrapper() });
    act(() => result.current.learn.mutate("d1"));
    await waitFor(() => expect(result.current.learnings).toHaveLength(1));
    expect(result.current.learnings[0]).toEqual({
      documentId: "d1",
      sessionId: "s1",
      finished: false,
    });
    expect(result.current.learningIds).toEqual(["d1"]);
    act(() => result.current.finishLearning("d1"));
    expect(result.current.learningIds).toEqual([]);
    expect(result.current.learnings[0]?.finished).toBe(true);
  });

  it("completes the learnings with the running sessions read from the server", async () => {
    server.use(http.get(`${API}/sessions`, () => HttpResponse.json([sessionOut()])));
    const { result } = renderHook(() => useDocumentActions(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.learnings).toHaveLength(1));
    expect(result.current.learnings[0]).toEqual({
      documentId: "d1",
      sessionId: "s1",
      finished: false,
    });
    expect(result.current.learningIds).toEqual(["d1"]);
    act(() => result.current.finishLearning("d1"));
    expect(result.current.learningIds).toEqual([]);
    expect(result.current.learnings[0]?.finished).toBe(true);
  });

  it("never overwrites a local entry with the session read from the server", async () => {
    server.use(
      http.get(`${API}/sessions`, () => HttpResponse.json([sessionOut({ id: "s-old" })])),
      http.post(`${API}/documents/d1/learned`, () =>
        HttpResponse.json({ session_id: "s-new" }, { status: 202 }),
      ),
      http.get(`${API}/documents`, () => HttpResponse.json([])),
    );
    const { result } = renderHook(() => useDocumentActions(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.learnings[0]?.sessionId).toBe("s-old"));
    act(() => result.current.learn.mutate("d1"));
    await waitFor(() => expect(result.current.learnings[0]?.sessionId).toBe("s-new"));
    expect(result.current.learnings).toHaveLength(1);
  });
});
