import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { useHealth } from "./useHealth";

const HEALTH_URL = `${apiBaseUrl}/api/v1/health`;

describe("useHealth", () => {
  it("charge le rapport de santé", async () => {
    server.use(http.get(HEALTH_URL, () => HttpResponse.json({ status: "ok", checks: {} })));
    const { result } = renderHook(() => useHealth(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.data?.status).toBe("ok"));
  });

  it("passe en erreur si le serveur est injoignable", async () => {
    server.use(http.get(HEALTH_URL, () => HttpResponse.error()));
    const { result } = renderHook(() => useHealth(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
