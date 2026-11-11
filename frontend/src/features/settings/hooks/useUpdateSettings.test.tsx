import { QueryClient } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { settingsFixture } from "../fixtures";
import { readTiers } from "../tierChoices";
import { buildUserSettings } from "../userSettings";
import { useUpdateSettings } from "./useUpdateSettings";

describe("useUpdateSettings", () => {
  it("envoie PUT /settings puis invalide les réglages", async () => {
    let received: unknown = null;
    server.use(
      http.put(`${apiBaseUrl}/api/v1/settings`, async ({ request }) => {
        received = await request.json();
        return HttpResponse.json(settingsFixture);
      }),
    );
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useUpdateSettings(), {
      wrapper: createQueryWrapper(client),
    });
    const body = buildUserSettings(settingsFixture, readTiers(settingsFixture.tiers));
    await act(() => result.current.mutateAsync(body));
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ["settings"] }));
    expect(received).toEqual(body);
  });
});
