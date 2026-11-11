import { QueryClient } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { apiKeysFixture } from "../fixtures";
import { useKeyActions } from "./useKeyActions";

const URL = `${apiBaseUrl}/api/v1/settings/api-keys`;
const track = <T,>(action: () => Promise<T>) => action();

describe("useKeyActions", () => {
  it("ne garde pas la clé en mémoire une fois enregistrée", async () => {
    server.use(http.post(URL, () => HttpResponse.json(apiKeysFixture[0])));
    const client = new QueryClient();
    const { result } = renderHook(() => useKeyActions(track), {
      wrapper: createQueryWrapper(client),
    });
    await act(() => result.current.onSave("anthropic", "sk-ant-secret-1234"));
    const kept = () =>
      JSON.stringify(
        client
          .getMutationCache()
          .getAll()
          .map((mutation) => mutation.state.variables ?? null),
      );
    await waitFor(() => expect(kept()).not.toContain("sk-ant-secret"));
  });

  it("rejette quand l'enregistrement échoue", async () => {
    server.use(
      http.post(URL, () =>
        HttpResponse.json(
          { error: { code: "invalid_key", message: "La clé est trop courte.", details: null } },
          { status: 422 },
        ),
      ),
    );
    const { result } = renderHook(() => useKeyActions(track), { wrapper: createQueryWrapper() });
    await expect(result.current.onSave("anthropic", "court")).rejects.toThrow("trop courte");
  });

  it("garde le résultat d'un test par fournisseur, puis l'oublie après une suppression", async () => {
    server.use(
      http.post(`${URL}/anthropic/test`, () =>
        HttpResponse.json({ ok: true, message: "Clé valide." }),
      ),
      http.delete(`${URL}/anthropic`, () => new HttpResponse(null, { status: 204 })),
    );
    const { result } = renderHook(() => useKeyActions(track), { wrapper: createQueryWrapper() });
    act(() => result.current.onTest("anthropic"));
    await waitFor(() =>
      expect(result.current.testResults.anthropic).toEqual({ ok: true, message: "Clé valide." }),
    );
    act(() => result.current.onDelete("anthropic"));
    await waitFor(() => expect(result.current.testResults.anthropic).toBeUndefined());
  });
});
