import { act, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { councilEvents } from "@/test/councilEvents";
import { exerciseOut, sessionSummary } from "@/test/ideApi";
import { expectCoherentOutline } from "@/test/headingOutline";
import { renderHome } from "../../ideTestkit";

const exercises = [
  exerciseOut({ id: "e1", title: "Additionner" }),
  exerciseOut({ id: "e2", title: "Trier une liste", origin: "generated", topic: "tri" }),
  exerciseOut({ id: "e3", title: "Lire un CSV" }),
];
const sessions = [
  sessionSummary({ id: "s2", exercise_id: "e2", passed: true, title: "Trier une liste" }),
  sessionSummary({ id: "s3", exercise_id: "e3", passed: false, title: "Lire un CSV" }),
  sessionSummary({ id: "s4", exercise_id: null, title: "Brouillon" }),
];

const row = async (title: string) => screen.findByRole("article", { name: title });

describe("IdeHomePage", () => {
  it("lists exercises with status", async () => {
    renderHome({ exercises, sessions });
    expect(within(await row("Additionner")).getByText("To do")).toBeInTheDocument();
    expect(within(await row("Trier une liste")).getByText("Passed")).toBeInTheDocument();
    expect(within(await row("Lire un CSV")).getByText("In progress")).toBeInTheDocument();
    expect(
      within(await row("Trier une liste")).getByText(/Generated · Topic: tri/),
    ).toBeInTheDocument();
    expectCoherentOutline();
  });

  it("starts a new session on an exercise and opens it", async () => {
    const { user, calls } = renderHome({ exercises, sessions });
    await user.click(
      within(await row("Additionner")).getByRole("button", { name: "Start: Additionner" }),
    );
    expect(await screen.findByText("Session opened")).toBeInTheDocument();
    expect(calls.sessions).toEqual([{ exercise_id: "e1" }]);
  });

  it("resumes the existing session instead of creating another", async () => {
    const { user, calls, router } = renderHome({ exercises, sessions });
    await user.click(
      within(await row("Lire un CSV")).getByRole("button", { name: "Resume: Lire un CSV" }),
    );
    await waitFor(() => expect(router.state.location.pathname).toBe("/code/s3"));
    expect(calls.sessions).toEqual([]);
  });

  it("opens a free session, and lists the previous ones", async () => {
    const { user, calls } = renderHome({ exercises, sessions });
    expect(await screen.findByText("Brouillon")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open a free session" }));
    expect(await screen.findByText("Session opened")).toBeInTheDocument();
    expect(calls.sessions).toEqual([{ exercise_id: null }]);
  });

  it("creates an exercise with its starter code and tests, then announces it", async () => {
    const { user, calls } = renderHome({ exercises: [] });
    await screen.findByText(/No exercises yet/);
    await user.type(screen.getByRole("textbox", { name: "Title" }), "Doubler");
    await user.type(screen.getByRole("textbox", { name: "Prompt" }), "Double un nombre.");
    await user.type(screen.getByRole("textbox", { name: /Starter code/ }), "x = 1");
    await user.type(screen.getByRole("textbox", { name: /Tests/ }), "def test_x(): pass");
    await user.click(screen.getByRole("button", { name: "Add exercise" }));
    expect(await screen.findByText("Exercise added.")).toBeInTheDocument();
    expect(calls.exercises).toEqual([
      {
        title: "Doubler",
        statement: "Double un nombre.",
        files: { "main.py": "x = 1", "test_main.py": "def test_x(): pass" },
        entry: "main.py",
      },
    ]);
  });

  it("generates an exercise and follows the agents until it is ready", async () => {
    const { user, calls, sockets } = renderHome({ exercises: [] });
    await user.type(await screen.findByRole("textbox", { name: "Topic" }), "les tuples");
    await user.click(screen.getByRole("button", { name: "Generate" }));
    await waitFor(() =>
      expect(calls.generated).toEqual([{ topic: "les tuples", level: "beginner" }]),
    );
    expect(await screen.findByText("The exercise is being written…")).toBeInTheDocument();
    await waitFor(() => expect(sockets.sockets.length).toBeGreaterThan(0));
    act(() => {
      sockets.last().open().push(councilEvents("g1").completed());
    });
    expect(
      await screen.findByText("The exercise is ready: it appears in the list."),
    ).toBeInTheDocument();
  });
});
