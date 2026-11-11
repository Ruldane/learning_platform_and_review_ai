import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { documentOut, memoryBackend, readHandlers } from "../fixtures";
import { hasDocumentInFlight, useDocuments } from "./useDocuments";

describe("useDocuments", () => {
  it("loads the rows", async () => {
    server.use(...readHandlers(memoryBackend({ documents: [documentOut()] })));
    const { result } = renderHook(() => useDocuments(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.data?.[0]?.name).toBe("cours.pdf"));
  });

  it("polls only while a document is queued or processing", () => {
    expect(hasDocumentInFlight([{ status: "queued" }])).toBe(true);
    expect(hasDocumentInFlight([{ status: "indexed" }, { status: "processing" }])).toBe(true);
    expect(hasDocumentInFlight([{ status: "indexed" }, { status: "error" }])).toBe(false);
    expect(hasDocumentInFlight(undefined)).toBe(false);
  });
});
