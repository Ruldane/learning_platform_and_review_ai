import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { settingsFixture } from "../fixtures";
import { useSettings } from "./useSettings";

describe("useSettings", () => {
  it("charge les réglages", async () => {
    server.use(http.get(`${apiBaseUrl}/api/v1/settings`, () => HttpResponse.json(settingsFixture)));
    const { result } = renderHook(() => useSettings(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.data?.brief_time).toBe("07:00"));
  });

  it("passe en erreur avec le message du serveur", async () => {
    server.use(
      http.get(`${apiBaseUrl}/api/v1/settings`, () =>
        HttpResponse.json(
          { error: { code: "boom", message: "Panne.", details: null } },
          { status: 500 },
        ),
      ),
    );
    const { result } = renderHook(() => useSettings(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("Panne.");
  });
});
