import { act, render, screen } from "@testing-library/react";
import { useEffect } from "react";
import { describe, expect, it, vi } from "vitest";
import { makeApplication } from "../fixtures";
import type { ApplicationView, StatusView } from "../viewTypes";
import { useBoardMoves } from "./useBoardMoves";

type Via = "menu" | "keyboard" | "pointer";
type Move = (id: string, status: StatusView, via: Via) => void;
const mover: { current: Move } = { current: () => undefined };
const call: Move = (id, status, via) => mover.current(id, status, via);

interface BoardProps {
  applications: ApplicationView[];
  onMove: () => void;
}

/** Un tableau minimal : une colonne par statut, la carte avec sa poignée et son bouton « Déplacer ». */
function Board({ applications, onMove }: BoardProps) {
  const { boardRef, move } = useBoardMoves(applications, onMove);
  useEffect(() => {
    mover.current = move;
  });
  return (
    <div ref={boardRef}>
      {(["to_apply", "applied"] as const).map((status) => (
        <div key={status} data-status={status}>
          {applications
            .filter((item) => item.status === status)
            .map((item) => (
              <div key={item.id} data-application-id={item.id}>
                <button data-drag-handle="">Poignée</button>
                <button aria-haspopup="menu">Menu</button>
              </div>
            ))}
        </div>
      ))}
    </div>
  );
}

const moved = (application: ApplicationView, status: StatusView) => ({ ...application, status });

describe("useBoardMoves focus", () => {
  it("gives the focus back to the drag handle after a keyboard drag", () => {
    const card = makeApplication({ id: "k", status: "to_apply" });
    const { rerender } = render(<Board applications={[card]} onMove={vi.fn()} />);
    act(() => call("k", "applied", "keyboard"));
    rerender(<Board applications={[moved(card, "applied")]} onMove={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Poignée" })).toHaveFocus();
  });

  it("gives the focus back to the move button after the menu", () => {
    const card = makeApplication({ id: "m", status: "to_apply" });
    const { rerender } = render(<Board applications={[card]} onMove={vi.fn()} />);
    act(() => call("m", "applied", "menu"));
    rerender(<Board applications={[moved(card, "applied")]} onMove={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Menu" })).toHaveFocus();
  });

  it("leaves the focus alone after a pointer drag", () => {
    const card = makeApplication({ id: "p", status: "to_apply" });
    const { rerender } = render(<Board applications={[card]} onMove={vi.fn()} />);
    act(() => call("p", "applied", "pointer"));
    rerender(<Board applications={[moved(card, "applied")]} onMove={vi.fn()} />);
    expect(document.body).toHaveFocus();
  });

  it("does not steal the focus on a later refresh when the move was refused", () => {
    const card = makeApplication({ id: "r", status: "to_apply" });
    const { rerender } = render(<Board applications={[card]} onMove={vi.fn()} />);
    act(() => call("r", "applied", "keyboard"));
    // Le serveur refuse : la carte reste dans sa colonne, la liste est relue.
    rerender(<Board applications={[{ ...card }]} onMove={vi.fn()} />);
    expect(document.body).toHaveFocus();
    // Un rafraîchissement plus tard qui la ferait changer de colonne ne vole pas le focus.
    rerender(<Board applications={[moved(card, "applied")]} onMove={vi.fn()} />);
    expect(document.body).toHaveFocus();
  });

  it("gives the focus back once more when the server refuses and the card returns to its column", () => {
    const card = makeApplication({ id: "z", status: "to_apply" });
    const { rerender } = render(<Board applications={[card]} onMove={vi.fn()} />);
    act(() => call("z", "applied", "keyboard"));
    rerender(<Board applications={[moved(card, "applied")]} onMove={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Poignée" })).toHaveFocus();
    // Le tableau a suivi tout de suite, puis le serveur refuse : la carte revient (autre nœud).
    rerender(<Board applications={[]} onMove={vi.fn()} />);
    expect(document.body).toHaveFocus();
    rerender(<Board applications={[{ ...card }]} onMove={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Poignée" })).toHaveFocus();
  });

  it("does not take the focus back on the return of a card when the user has moved on", () => {
    const card = makeApplication({ id: "y", status: "to_apply" });
    const { rerender } = render(
      <>
        <Board applications={[card]} onMove={vi.fn()} />
        <input aria-label="Ailleurs" />
      </>,
    );
    act(() => call("y", "applied", "keyboard"));
    rerender(
      <>
        <Board applications={[moved(card, "applied")]} onMove={vi.fn()} />
        <input aria-label="Ailleurs" />
      </>,
    );
    screen.getByLabelText("Ailleurs").focus();
    rerender(
      <>
        <Board applications={[{ ...card }]} onMove={vi.fn()} />
        <input aria-label="Ailleurs" />
      </>,
    );
    expect(screen.getByLabelText("Ailleurs")).toHaveFocus();
  });
});
