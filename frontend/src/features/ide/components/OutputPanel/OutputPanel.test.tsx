import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { OutputView } from "../viewTypes";
import { OutputPanel } from "./OutputPanel";

const view = (over: Partial<OutputView> = {}): OutputView => ({
  runId: null,
  kind: null,
  origin: "app",
  status: "idle",
  output: "",
  exitCode: null,
  durationMs: null,
  truncated: false,
  error: null,
  ...over,
});

describe("OutputPanel", () => {
  it("is read-only: no field, no keyboard entry for the program", () => {
    render(<OutputPanel view={view()} />);
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.getByText(/ne lit pas le clavier/)).toBeInTheDocument();
    expect(screen.getByText("Rien n'a été exécuté. Appuie sur Ctrl+Entrée.")).toBeInTheDocument();
  });

  it("writes the state of each end in words", () => {
    const { rerender } = render(
      <OutputPanel
        view={view({ runId: "r1", kind: "run", status: "done", exitCode: 0, durationMs: 120 })}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Terminé (code 0, 120 ms).");
    rerender(<OutputPanel view={view({ runId: "r1", kind: "run", status: "timeout" })} />);
    expect(screen.getByRole("status")).toHaveTextContent("Arrêté : le temps maximal est dépassé.");
    rerender(
      <OutputPanel view={view({ runId: "r1", kind: "check", status: "done", exitCode: 1 })} />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Vérification échouée.");
    rerender(
      <OutputPanel view={view({ runId: "r1", kind: "check", status: "done", exitCode: 0 })} />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Vérification réussie");
  });

  it("shows the output, the truncation notice and an error", () => {
    render(
      <OutputPanel
        view={view({
          runId: "r1",
          kind: "run",
          status: "done",
          exitCode: 0,
          output: "Bonjour\n",
          truncated: true,
          error: "La sortie n'a pas pu être relue.",
        })}
      />,
    );
    expect(screen.getByRole("log", { name: "Sortie du programme" }).textContent).toBe("Bonjour\n");
    expect(screen.getByText(/La sortie est tronquée/)).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("La sortie n'a pas pu être relue.");
  });

  it("takes the focus when a run starts, and only then", () => {
    const { rerender } = render(<OutputPanel view={view()} />);
    const region = screen.getByRole("region", { name: "Sortie" });
    expect(region).not.toHaveFocus();
    rerender(<OutputPanel view={view({ runId: "r1", kind: "run", status: "running" })} />);
    expect(region).toHaveFocus();
  });
});
