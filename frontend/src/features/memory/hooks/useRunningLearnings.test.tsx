import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { memoryBackend, readHandlers, sessionOut } from "../fixtures";
import { useRunningLearnings } from "./useRunningLearnings";

describe("useRunningLearnings", () => {
  it("asks only for the running Archiviste sessions, once", async () => {
    const backend = memoryBackend({ sessions: [sessionOut()] });
    server.use(...readHandlers(backend));
    const { result } = renderHook(() => useRunningLearnings(), { wrapper: createQueryWrapper() });
    await waitFor(() =>
      expect(result.current.data).toEqual([{ documentId: "d1", sessionId: "s1" }]),
    );
    const calls = backend.requests.filter((r) => r.url.pathname.endsWith("/sessions"));
    expect(calls).toHaveLength(1);
    expect(calls[0]?.url.searchParams.get("graph")).toBe("learned_document");
    expect(calls[0]?.url.searchParams.get("status")).toBe("running");
  });

  it("keeps only the sessions that follow a document", async () => {
    const backend = memoryBackend({
      sessions: [
        sessionOut({ id: "s1", subject_id: "d1" }),
        sessionOut({ id: "s2", subject_type: "goal", subject_id: "g1" }),
        sessionOut({ id: "s3", subject_id: null }),
        sessionOut({ id: "s4", subject_type: null, subject_id: null }),
      ],
    });
    server.use(...readHandlers(backend));
    const { result } = renderHook(() => useRunningLearnings(), { wrapper: createQueryWrapper() });
    await waitFor(() =>
      expect(result.current.data).toEqual([{ documentId: "d1", sessionId: "s1" }]),
    );
  });
});
