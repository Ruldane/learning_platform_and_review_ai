import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { modelsFixture } from "../fixtures";
import { useModels } from "./useModels";

describe("useModels", () => {
  it("charge les fournisseurs et les préréglages", async () => {
    server.use(
      http.get(`${apiBaseUrl}/api/v1/settings/models`, () => HttpResponse.json(modelsFixture)),
    );
    const { result } = renderHook(() => useModels(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.data?.providers).toHaveLength(3));
    expect(Object.keys(result.current.data?.presets ?? {})).toHaveLength(4);
  });
});
