import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { initialSessionState } from "@/shared/realtime/sessionReducer";
import type { DraftsRegeneration } from "../../../hooks/useRegenerateDrafts";
import type { useProjectRun } from "../../../hooks/useProjectRun";
import { RegenerateDrafts } from "./RegenerateDrafts";

type Run = ReturnType<typeof useProjectRun>;

/** Un suivi de session réduit à ce que le composant lit (le fil lui-même se teste ailleurs). */
const runOf = (status: string, over: boolean) =>
  ({
    stream: { status, connection: "open", view: initialSessionState, pendingInterrupt: null },
    actions: {},
    over,
  }) as unknown as Run;

const regeneration = (over: Partial<DraftsRegeneration> = {}): DraftsRegeneration => ({
  regenerate: vi.fn(),
  pending: false,
  sessionId: null,
  rereading: false,
  error: null,
  ...over,
});

const REGENERATE = { name: "Régénérer les brouillons" };
const FAILED = /n'ont pas pu être écrits/;

describe("RegenerateDrafts", () => {
  it("offers the button alone before any attempt", () => {
    render(<RegenerateDrafts regeneration={regeneration()} run={runOf("idle", false)} />);
    expect(screen.getByRole("button", REGENERATE)).toBeVisible();
    expect(screen.queryByText(FAILED)).toBeNull();
    // Rien n'a été demandé : le bouton ne prend pas le focus de lui-même.
    expect(screen.getByRole("button", REGENERATE)).not.toHaveFocus();
  });

  it("follows the writing, and its title takes the focus from the button that is gone", () => {
    render(
      <RegenerateDrafts
        regeneration={regeneration({ sessionId: "s1" })}
        run={runOf("running", false)}
      />,
    );
    expect(screen.queryByRole("button", REGENERATE)).toBeNull();
    expect(screen.getByRole("heading", { name: "Brouillons en cours d'écriture" })).toHaveFocus();
  });

  it.each(["failed", "cancelled", "completed"])(
    "says so and gives the focus back to the button when the writing ends %s without drafts",
    (status) => {
      render(
        <RegenerateDrafts
          regeneration={regeneration({ sessionId: "s1" })}
          run={runOf(status, true)}
        />,
      );
      expect(screen.getByText(FAILED)).toBeVisible();
      expect(screen.getByRole("button", REGENERATE)).toHaveFocus();
    },
  );

  it("says nothing while the project is read again: the drafts may be arriving", () => {
    render(
      <RegenerateDrafts
        regeneration={regeneration({ sessionId: "s1", rereading: true })}
        run={runOf("completed", true)}
      />,
    );
    expect(screen.queryByText(FAILED)).toBeNull();
  });

  it("shows the refusal under the button", () => {
    render(
      <RegenerateDrafts
        regeneration={regeneration({ error: "Panne du serveur." })}
        run={runOf("idle", false)}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Panne du serveur.");
  });
});
