import { QueryClient } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { applicationOut, detailOut } from "@/test/applicationsApi";
import { API } from "@/test/councilApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { useCreateFromPosting } from "./useCreateFromPosting";

describe("useCreateFromPosting", () => {
  it("makes the applications read again after a creation (the board and the badge stay right)", async () => {
    server.use(
      http.post(`${API}/applications`, () =>
        HttpResponse.json(
          { application: detailOut(applicationOut({ id: "n1" })), info: [] },
          { status: 201 },
        ),
      ),
    );
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    client.setQueryData(["applications", "list"], [applicationOut()]);
    const { result } = renderHook(() => useCreateFromPosting("p1"), {
      wrapper: createQueryWrapper(client),
    });
    await act(async () => {
      await result.current.create();
    });
    await waitFor(() =>
      expect(client.getQueryState(["applications", "list"])?.isInvalidated).toBe(true),
    );
  });
});
