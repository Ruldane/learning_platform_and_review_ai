import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { memoryBackend, readHandlers } from "../fixtures";
import { useMemoryItem } from "./useMemoryItem";

describe("useMemoryItem", () => {
  it("loads the detail with chunks, neighbors and journal", async () => {
    server.use(...readHandlers(memoryBackend()));
    const { result } = renderHook(() => useMemoryItem("i1"), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.data?.title).toBe("Attention"));
    expect(result.current.data?.writes[0]?.author).toBe("archivist");
    expect(result.current.data?.chunks).toHaveLength(1);
  });

  it("makes no call without an id", () => {
    const backend = memoryBackend();
    server.use(...readHandlers(backend));
    const { result } = renderHook(() => useMemoryItem(null), { wrapper: createQueryWrapper() });
    expect(result.current.fetchStatus).toBe("idle");
    expect(backend.requests).toHaveLength(0);
  });

  it("fails with the server message when the item is gone", async () => {
    server.use(...readHandlers(memoryBackend()));
    const { result } = renderHook(() => useMemoryItem("zzz"), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("Élément introuvable.");
  });
});
