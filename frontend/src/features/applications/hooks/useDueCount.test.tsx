import { renderHook, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { applicationsApi } from "@/test/applicationsApi";
import { API } from "@/test/councilApi";
import { apiError } from "@/test/councilHarness";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { useDueCount } from "./useDueCount";

describe("useDueCount", () => {
  it("is the number of due reminders from the indicators", async () => {
    server.use(...applicationsApi({ stats: { due_reminders: 3 } }).handlers);
    const { result } = renderHook(() => useDueCount(), { wrapper: createQueryWrapper() });
    expect(result.current).toBeUndefined();
    await waitFor(() => expect(result.current).toBe(3));
  });

  it("stays unknown when the indicators cannot be read, so no badge is shown", async () => {
    let asked = false;
    server.use(
      http.get(`${API}/applications/stats`, () => {
        asked = true;
        return HttpResponse.json(apiError("internal_error", "Panne."), { status: 500 });
      }),
    );
    const { result } = renderHook(() => useDueCount(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(asked).toBe(true));
    expect(result.current).toBeUndefined();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
