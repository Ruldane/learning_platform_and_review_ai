import { QueryClient } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API, programOut } from "@/test/programApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { programKeys } from "../queryKeys";
import type { ProgramOut } from "../types";
import { useTaskMutations } from "./useTaskMutations";

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(programKeys.detail("p1"), programOut() as unknown as ProgramOut);
  const hook = renderHook(() => useTaskMutations("p1"), { wrapper: createQueryWrapper(client) });
  const dateOf = (id: string) =>
    client
      .getQueryData<ProgramOut>(programKeys.detail("p1"))
      ?.weeks.flatMap((week) => week.modules.flatMap((module) => module.tasks))
      .find((task) => task.id === id)?.planned_date;
  return { client, hook, dateOf };
}

const OVER = {
  error: {
    code: "week_over_budget",
    message: "Semaine 2 : 760 min prévues, 714 au plus.",
    details: { week_rank: 2, planned_minutes: 760, cap_minutes: 714 },
  },
};

describe("useTaskMutations", () => {
  it("moves a task: patches the day, shows it at once and reads the program again", async () => {
    let body: unknown = null;
    server.use(
      http.patch(`${API}/tasks/t1`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({});
      }),
    );
    const { client, hook, dateOf } = setup();
    act(() => hook.result.current.move("t1", "2026-11-18"));
    await waitFor(() => expect(dateOf("t1")).toBe("2026-11-18"));
    await waitFor(() =>
      expect(client.getQueryState(programKeys.detail("p1"))?.isInvalidated).toBe(true),
    );
    expect(body).toEqual({ planned_date: "2026-11-18" });
  });

  it("puts the task back and says the server's reason when the move is refused", async () => {
    server.use(
      http.patch(`${API}/tasks/t1`, () => HttpResponse.json(OVER, { status: 422 })),
      http.get(`${API}/programs/p1`, () => HttpResponse.json(programOut())),
    );
    const { hook, dateOf } = setup();
    act(() => hook.result.current.move("t1", "2026-11-24"));
    await waitFor(() =>
      expect(hook.result.current.error).toBe("Semaine 2 : 760 min prévues, 714 au plus."),
    );
    expect(dateOf("t1")).toBe("2026-11-16");
  });

  it("toggles a task as done and deletes one", async () => {
    const bodies: unknown[] = [];
    server.use(
      http.patch(`${API}/tasks/t1`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json({});
      }),
      http.patch(`${API}/programs/p1`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(programOut());
      }),
      http.get(`${API}/programs/p1`, () => HttpResponse.json(programOut())),
    );
    const { hook } = setup();
    act(() => hook.result.current.toggleDone("t1", true));
    await waitFor(() => expect(bodies).toHaveLength(1));
    act(() => hook.result.current.remove("t2"));
    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies).toEqual([{ status: "done" }, { delete_task_ids: ["t2"] }]);
  });

  it("adds a task to the module of the chosen week, and rejects when refused", async () => {
    const bodies: unknown[] = [];
    let refuse = true;
    server.use(
      http.patch(`${API}/programs/p1`, async ({ request }) => {
        bodies.push(await request.json());
        return refuse ? HttpResponse.json(OVER, { status: 422 }) : HttpResponse.json(programOut());
      }),
      http.get(`${API}/programs/p1`, () => HttpResponse.json(programOut())),
    );
    const { hook } = setup();
    const input = {
      title: "Écrire un test",
      type: "pratiquer" as const,
      minutes: 30,
      doneCriterion: "Le test passe.",
      plannedDate: "2026-11-25",
    };
    await act(async () => {
      await expect(hook.result.current.add(input)).rejects.toBeDefined();
    });
    expect(hook.result.current.addError).toBe("Semaine 2 : 760 min prévues, 714 au plus.");
    refuse = false;
    await act(async () => {
      await hook.result.current.add(input);
    });
    expect(hook.result.current.addError).toBeNull();
    expect(bodies[1]).toEqual({
      add_tasks: [
        {
          module_id: "m2",
          title: "Écrire un test",
          type: "pratiquer",
          minutes: 30,
          done_criterion: "Le test passe.",
          planned_date: "2026-11-25",
        },
      ],
    });
  });
});
