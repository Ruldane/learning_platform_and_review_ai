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
    expect(within(await row("Additionner")).getByText("À faire")).toBeInTheDocument();
    expect(within(await row("Trier une liste")).getByText("Réussi")).toBeInTheDocument();
    expect(within(await row("Lire un CSV")).getByText("En cours")).toBeInTheDocument();
    expect(
      within(await row("Trier une liste")).getByText(/Généré · Sujet : tri/),
    ).toBeInTheDocument();
    expectCoherentOutline();
  });

  it("starts a new session on an exercise and opens it", async () => {
    const { user, calls } = renderHome({ exercises, sessions });
    await user.click(
      within(await row("Additionner")).getByRole("button", { name: "Commencer : Additionner" }),
    );
    expect(await screen.findByText("Séance ouverte")).toBeInTheDocument();
    expect(calls.sessions).toEqual([{ exercise_id: "e1" }]);
  });

  it("resumes the existing session instead of creating another", async () => {
    const { user, calls, router } = renderHome({ exercises, sessions });
    await user.click(
      within(await row("Lire un CSV")).getByRole("button", { name: "Reprendre : Lire un CSV" }),
    );
    await waitFor(() => expect(router.state.location.pathname).toBe("/code/s3"));
    expect(calls.sessions).toEqual([]);
  });

  it("opens a free session, and lists the previous ones", async () => {
    const { user, calls } = renderHome({ exercises, sessions });
    expect(await screen.findByText("Brouillon")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Ouvrir une séance libre" }));
    expect(await screen.findByText("Séance ouverte")).toBeInTheDocument();
    expect(calls.sessions).toEqual([{ exercise_id: null }]);
  });

  it("creates an exercise with its starter code and tests, then announces it", async () => {
    const { user, calls } = renderHome({ exercises: [] });
    await screen.findByText(/Aucun exercice pour l'instant/);
    await user.type(screen.getByRole("textbox", { name: "Titre" }), "Doubler");
    await user.type(screen.getByRole("textbox", { name: "Énoncé" }), "Double un nombre.");
    await user.type(screen.getByRole("textbox", { name: /Code de départ/ }), "x = 1");
    await user.type(screen.getByRole("textbox", { name: /Tests/ }), "def test_x(): pass");
    await user.click(screen.getByRole("button", { name: "Ajouter l'exercice" }));
    expect(await screen.findByText("Exercice ajouté.")).toBeInTheDocument();
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
    await user.type(await screen.findByRole("textbox", { name: "Sujet" }), "les tuples");
    await user.click(screen.getByRole("button", { name: "Générer" }));
    await waitFor(() =>
      expect(calls.generated).toEqual([{ topic: "les tuples", level: "beginner" }]),
    );
    expect(await screen.findByText("L'exercice est en cours d'écriture…")).toBeInTheDocument();
    await waitFor(() => expect(sockets.sockets.length).toBeGreaterThan(0));
    act(() => {
      sockets.last().open().push(councilEvents("g1").completed());
    });
    expect(
      await screen.findByText("L'exercice est prêt : il apparaît dans la liste."),
    ).toBeInTheDocument();
  });
});
