import { QueryClient } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { apiKeysFixture } from "../fixtures";
import { useSaveApiKey } from "./useSaveApiKey";

const URL = `${apiBaseUrl}/api/v1/settings/api-keys`;

describe("useSaveApiKey", () => {
  it("envoie la clé puis invalide les clés et les modèles", async () => {
    let received: unknown = null;
    server.use(
      http.post(URL, async ({ request }) => {
        received = await request.json();
        return HttpResponse.json(apiKeysFixture[0]);
      }),
    );
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useSaveApiKey(), { wrapper: createQueryWrapper(client) });
    await act(() => result.current.mutateAsync({ provider: "anthropic", key: "sk-ant-1234" }));
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ["api-keys"] }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["models"] });
    expect(received).toEqual({ provider: "anthropic", key: "sk-ant-1234" });
  });

  it("ne met pas la clé dans le cache de requêtes", async () => {
    server.use(http.post(URL, () => HttpResponse.json(apiKeysFixture[0])));
    const client = new QueryClient();
    const { result } = renderHook(() => useSaveApiKey(), { wrapper: createQueryWrapper(client) });
    await act(() =>
      result.current.mutateAsync({ provider: "anthropic", key: "sk-ant-secret-1234" }),
    );
    const cache = JSON.stringify(
      client
        .getQueryCache()
        .getAll()
        .map((query) => [query.queryKey, query.state.data]),
    );
    expect(cache).not.toContain("sk-ant-secret");
  });

  it("remonte l'erreur du serveur en français", async () => {
    server.use(
      http.post(URL, () =>
        HttpResponse.json(
          { error: { code: "invalid_key", message: "La clé est trop courte.", details: null } },
          { status: 422 },
        ),
      ),
    );
    const { result } = renderHook(() => useSaveApiKey(), { wrapper: createQueryWrapper() });
    await act(async () => {
      await result.current.mutateAsync({ provider: "anthropic", key: "court" }).catch(() => null);
    });
    await waitFor(() => expect(result.current.error?.message).toBe("La clé est trop courte."));
  });
});
