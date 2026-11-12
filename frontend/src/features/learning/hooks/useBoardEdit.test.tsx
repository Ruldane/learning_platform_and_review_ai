import type { QueryClient } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API, boardOut } from "@/test/councilApi";
import { createQueryWrapper, createTestQueryClient } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { learningKeys } from "../queryKeys";
import { useBoardEdit } from "./useBoardEdit";

const edit = { scene: { type: "excalidraw" }, note: "Ajouté : « Docker »" };

function setup(client: QueryClient = createTestQueryClient()) {
  return renderHook(() => useBoardEdit("g1"), { wrapper: createQueryWrapper(client) });
}

describe("useBoardEdit", () => {
  it("posts the scene and the note, and adds the saved state to the board list", async () => {
    const bodies: unknown[] = [];
    server.use(
      http.post(`${API}/boards/b1/edits`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(boardOut("b2", { author: "user" }), { status: 201 });
      }),
    );
    const client = createTestQueryClient();
    client.setQueryData(learningKeys.boards("g1"), [boardOut("b1")]);
    const { result } = setup(client);
    await act(() => result.current.send("b1", edit));
    expect(bodies).toEqual([edit]);
    const cached = client.getQueryData<{ id: string }[]>(learningKeys.boards("g1"));
    expect(cached?.map((b) => b.id)).toEqual(["b1", "b2"]);
  });

  it("rejects and exposes the French message when the board is refused", async () => {
    server.use(
      http.post(`${API}/boards/b1/edits`, () =>
        HttpResponse.json(
          {
            error: { code: "board_too_large", message: "Tableau trop volumineux.", details: null },
          },
          { status: 413 },
        ),
      ),
    );
    const { result } = setup();
    await act(async () => {
      await expect(result.current.send("b1", edit)).rejects.toThrow();
    });
    await waitFor(() => expect(result.current.error).toBe("Tableau trop volumineux."));
  });
});
