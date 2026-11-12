import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { searchUsageFixture } from "../fixtures";
import { useSearchUsage } from "./useSearchUsage";

const URL = `${apiBaseUrl}/api/v1/research/usage`;

describe("useSearchUsage", () => {
  it("reads the Brave usage of the month as a gauge view", async () => {
    server.use(http.get(URL, () => HttpResponse.json(searchUsageFixture)));
    const { result } = renderHook(() => useSearchUsage(), { wrapper: createQueryWrapper() });
    await waitFor(() =>
      expect(result.current.data).toEqual({
        hasKey: true,
        used: 120,
        cap: 900,
        month: "2026-11",
      }),
    );
  });

  it("fails with the server message", async () => {
    server.use(
      http.get(URL, () =>
        HttpResponse.json(
          { error: { code: "boom", message: "Panne.", details: null } },
          { status: 500 },
        ),
      ),
    );
    const { result } = renderHook(() => useSearchUsage(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("Panne.");
  });
});
