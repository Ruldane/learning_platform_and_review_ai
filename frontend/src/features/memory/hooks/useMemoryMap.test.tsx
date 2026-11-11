import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { mapOut, memoryBackend, readHandlers } from "../fixtures";
import { useMemoryMap } from "./useMemoryMap";

describe("useMemoryMap", () => {
  it("returns the points and the truncated flag", async () => {
    server.use(...readHandlers(memoryBackend({ map: { ...mapOut, truncated: true } })));
    const { result } = renderHook(() => useMemoryMap(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.data?.points).toHaveLength(2));
    expect(result.current.data?.truncated).toBe(true);
    expect(result.current.data?.points[0]).toEqual({
      item_id: "i1",
      title: "Attention",
      kind: "acquis",
      x: 0.2,
      y: -0.3,
    });
  });
});
