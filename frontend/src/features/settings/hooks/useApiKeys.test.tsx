import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { apiKeysFixture } from "../fixtures";
import { useApiKeys } from "./useApiKeys";

describe("useApiKeys", () => {
  it("charge les clés (4 derniers caractères seulement)", async () => {
    server.use(
      http.get(`${apiBaseUrl}/api/v1/settings/api-keys`, () => HttpResponse.json(apiKeysFixture)),
    );
    const { result } = renderHook(() => useApiKeys(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.data).toHaveLength(3));
    expect(result.current.data?.[0]?.last4).toBe("9876");
  });
});
