import { QueryClient } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { useDeleteApiKey } from "./useDeleteApiKey";

describe("useDeleteApiKey", () => {
  it("supprime la clé du fournisseur puis invalide les clés et les modèles", async () => {
    let deleted = "";
    server.use(
      http.delete(`${apiBaseUrl}/api/v1/settings/api-keys/:provider`, ({ params }) => {
        deleted = String(params.provider);
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useDeleteApiKey(), { wrapper: createQueryWrapper(client) });
    await act(() => result.current.mutateAsync("openai"));
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ["api-keys"] }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["models"] });
    expect(deleted).toBe("openai");
  });
});
