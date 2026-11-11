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

/** Tout ce que le cache des mutations garde des variables (la clé ne doit pas y rester). */
const keptVariables = (client: QueryClient) =>
  JSON.stringify(
    client
      .getMutationCache()
      .getAll()
      .map((mutation) => mutation.state.variables ?? null),
  );

describe("useKeyActions", () => {
  it("ne garde pas la clé en mémoire une fois enregistrée", async () => {
    server.use(http.post(URL, () => HttpResponse.json(apiKeysFixture[0])));
    const client = new QueryClient();
    const { result } = renderHook(() => useKeyActions(track), {
      wrapper: createQueryWrapper(client),
    });
    await act(() => result.current.onSave("anthropic", "sk-ant-secret-1234"));
    await waitFor(() => expect(keptVariables(client)).not.toContain("sk-ant-secret"));
  });

  it("rejette quand l'enregistrement échoue, et ne garde pas la clé en mémoire non plus", async () => {
    server.use(
      http.post(URL, () =>
        HttpResponse.json(
          { error: { code: "invalid_key", message: "La clé est trop courte.", details: null } },
          { status: 422 },
        ),
      ),
    );
    const client = new QueryClient();
    const { result } = renderHook(() => useKeyActions(track), {
      wrapper: createQueryWrapper(client),
    });
    await expect(result.current.onSave("anthropic", "sk-ant-secret-1234")).rejects.toThrow(
      "trop courte",
    );
    await waitFor(() => expect(keptVariables(client)).not.toContain("sk-ant-secret"));
    await waitFor(() => expect(result.current.pendingProviders).toEqual([]));
  });

  it("garde l'état occupé de chaque enregistrement quand deux se chevauchent", async () => {
    const gates: Record<string, () => void> = {};
    server.use(
      http.post(URL, async ({ request }) => {
        const { provider } = (await request.json()) as { provider: string };
        await new Promise<void>((resolve) => {
          gates[provider] = resolve;
        });
        return HttpResponse.json(apiKeysFixture[0]);
      }),
    );
    const client = new QueryClient();
    const { result } = renderHook(() => useKeyActions(track), {
      wrapper: createQueryWrapper(client),
    });
    let first: Promise<void> = Promise.resolve();
    let second: Promise<void> = Promise.resolve();
    act(() => {
      first = result.current.onSave("anthropic", "sk-ant-secret-1111");
      second = result.current.onSave("glm", "sk-glm-secret-2222");
    });
    await waitFor(() => expect(Object.keys(gates)).toHaveLength(2));
    expect(result.current.pendingProviders).toEqual(["anthropic", "glm"]);

    await act(async () => {
      gates.anthropic?.();
      await first;
    });
    // La fin du premier enregistrement ne doit pas libérer le second, encore en vol.
    expect(result.current.pendingProviders).toEqual(["glm"]);

    await act(async () => {
      gates.glm?.();
      await second;
    });
    expect(result.current.pendingProviders).toEqual([]);
    await waitFor(() => expect(keptVariables(client)).not.toContain("secret"));
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
