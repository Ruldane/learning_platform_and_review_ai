import { QueryClient } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { useTestApiKey } from "./useTestApiKey";

describe("useTestApiKey", () => {
  it("renvoie le résultat du test et rafraîchit les clés (dernier test mémorisé)", async () => {
    server.use(
      http.post(`${apiBaseUrl}/api/v1/settings/api-keys/anthropic/test`, () =>
        HttpResponse.json({ ok: true, message: "Clé valide." }),
      ),
    );
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useTestApiKey(), { wrapper: createQueryWrapper(client) });
    let outcome: unknown = null;
    await act(async () => {
      outcome = await result.current.mutateAsync("anthropic");
    });
    expect(outcome).toEqual({ ok: true, message: "Clé valide." });
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ["api-keys"] }));
  });
});
