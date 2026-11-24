import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API, lessonSummary } from "@/test/lessonsApi";
import { summaryOut } from "@/test/programApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { LessonsPage } from "./LessonsPage";

const routes = [
  { path: "/learn/lessons", element: <LessonsPage /> },
  { path: "/learn/lessons/:lessonId", element: <h1>Leçon ouverte</h1> },
  { path: "/learn/programs/:programId", element: <h1>Programme ouvert</h1> },
  { path: "/learn/council", element: <h1>Conseil ouvert</h1> },
];

function setup(lessons: Record<string, unknown>[], programs: unknown[] = [summaryOut()]) {
  server.use(
    http.get(`${API}/programs`, () => HttpResponse.json(programs)),
    http.get(`${API}/programs/p1/lessons`, () => HttpResponse.json(lessons)),
  );
  return renderRoutes(routes, "/learn/lessons");
}

describe("LessonsPage", () => {
  it("lists the lessons of the latest program by week, with their state", async () => {
    const { router, user } = setup([
      lessonSummary(),
      lessonSummary({ id: "l2", title: "Les fichiers CSV", week_rank: 2, status: "generating" }),
      lessonSummary({ id: "l3", title: "Les dates", week_rank: 3, status: "pending" }),
      lessonSummary({ id: "l4", title: "Les API", week_rank: 3, status: "failed" }),
    ]);
    const week2 = await screen.findByRole("region", { name: "Week 2" });
    expect(within(week2).getByText("Being prepared")).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Week 3" })).getByText("Upcoming"),
    ).toBeInTheDocument();
    expect(screen.getByText("Retry scheduled")).toBeInTheDocument();
    expect(screen.getByText("1,400 words")).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Read “Les variables et les types”" }));
    expect(router.state.location.pathname).toBe("/learn/lessons/l1");
  });

  it("explains that lessons come with the validated program", async () => {
    const { router, user } = setup([]);
    expect(await screen.findByText("No lessons yet")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "View the program" }));
    expect(router.state.location.pathname).toBe("/learn/programs/p1");
  });

  it("sends to the council when there is no program", async () => {
    const { router, user } = setup([], []);
    expect(await screen.findByText("No program yet")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open the Council" }));
    expect(router.state.location.pathname).toBe("/learn/council");
  });

  it("offers Retry when the lessons cannot be read", async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/programs`, () => HttpResponse.json([summaryOut()])),
      http.get(`${API}/programs/p1/lessons`, () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json({}, { status: 500 })
          : HttpResponse.json([lessonSummary()]);
      }),
    );
    const { user } = renderRoutes(routes, "/learn/lessons");
    await user.click(await screen.findByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Les variables et les types")).toBeInTheDocument();
  });

  it("lets her pick another program", async () => {
    server.use(
      http.get(`${API}/programs`, () =>
        HttpResponse.json([summaryOut({ id: "p2", title: "Bases du ML" }), summaryOut()]),
      ),
      http.get(`${API}/programs/p2/lessons`, () =>
        HttpResponse.json([lessonSummary({ id: "l9", title: "La régression" })]),
      ),
      http.get(`${API}/programs/p1/lessons`, () => HttpResponse.json([lessonSummary()])),
    );
    const { router, user } = renderRoutes(routes, "/learn/lessons");
    expect(await screen.findByText("La régression")).toBeInTheDocument();
    const picker = screen.getByRole("combobox", { name: "Program" });
    expect(picker).toHaveValue("p2");
    await user.selectOptions(picker, "Python pour la data");
    expect(await screen.findByText("Les variables et les types")).toBeInTheDocument();
    expect(screen.queryByText("La régression")).not.toBeInTheDocument();
    expect(router.state.location.search).toBe("?program=p1");
  });

  it("hides the picker with a single program", async () => {
    setup([lessonSummary()]);
    expect(await screen.findByText("Les variables et les types")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Program" })).not.toBeInTheDocument();
  });

  it("marks a lesson finished once its module tasks are done in the program", async () => {
    setup([
      lessonSummary({ done_tasks: 3, total_tasks: 3, completed: true }),
      lessonSummary({ id: "l2", title: "Les fichiers CSV", done_tasks: 1 }),
    ]);
    const [finished, started] = (await screen.findAllByRole("listitem")) as [
      HTMLElement,
      HTMLElement,
    ];
    expect(within(finished).getByText("Completed")).toBeInTheDocument();
    expect(within(started).queryByText("Completed")).not.toBeInTheDocument();
    expect(within(started).getByText("1 / 3 tasks done")).toBeInTheDocument();
  });
});
