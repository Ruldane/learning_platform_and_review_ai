import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import type { ReactNode } from "react";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { useResearchRun } from "./useResearchRun";

const API = `${apiBaseUrl}/api/v1/sessions`;

function setup(initial: string) {
  const fake = createFakeSocketServer();
  const Query = createQueryWrapper();
  const wrapper = ({ children }: { children: ReactNode }) => (
    <Query>
      <MemoryRouter initialEntries={[initial]}>{children}</MemoryRouter>
    </Query>
  );
  const view = renderHook(() => ({ run: useResearchRun(fake.factory), location: useLocation() }), {
    wrapper,
  });
  return { fake, ...view };
}

describe("useResearchRun", () => {
  afterEach(() => useSessionStore.getState().reset("s7"));

  it("starts a web_research session and keeps its id in the URL", async () => {
    const posted: unknown[] = [];
    server.use(
      http.post(API, async ({ request }) => {
        posted.push(await request.json());
        return HttpResponse.json({ session_id: "s7" }, { status: 201 });
      }),
    );
    const { result } = setup("/essai");
    expect(result.current.run.sessionId).toBeNull();

    act(() => result.current.run.start.mutate({ query: "rag", urls: [] }));
    await waitFor(() => expect(result.current.run.sessionId).toBe("s7"));
    expect(posted).toEqual([{ graph: "web_research", input: { query: "rag", urls: [] } }]);
    expect(result.current.location.search).toBe("?session=s7");
  });

  it("reads the session from the URL and leaves it on restart", async () => {
    const { result, fake } = setup("/essai?session=s7");
    expect(result.current.run.sessionId).toBe("s7");
    await waitFor(() => expect(fake.sockets).toHaveLength(1));
    act(() => result.current.run.restart());
    await waitFor(() => expect(result.current.run.sessionId).toBeNull());
    expect(result.current.location.search).toBe("");
  });
});
