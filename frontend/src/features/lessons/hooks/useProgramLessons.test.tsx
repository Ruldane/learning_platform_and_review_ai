import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { API, lessonSummary } from "@/test/lessonsApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { useProgramLessons } from "./useProgramLessons";

describe("useProgramLessons", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("reads the lessons again while one is being written, then stops", async () => {
    let reads = 0;
    server.use(
      http.get(`${API}/programs/p1/lessons`, () => {
        reads += 1;
        const status = reads === 1 ? "generating" : "ready";
        return HttpResponse.json([lessonSummary({ status })]);
      }),
    );
    const { result } = renderHook(() => useProgramLessons("p1"), {
      wrapper: createQueryWrapper(),
    });
    await waitFor(() => expect(result.current.data?.[0]?.status).toBe("generating"));
    await act(() => vi.advanceTimersByTimeAsync(5000));
    await waitFor(() => expect(result.current.data?.[0]?.status).toBe("ready"));
    await act(() => vi.advanceTimersByTimeAsync(60_000));
    expect(reads).toBe(2);
  });
});
