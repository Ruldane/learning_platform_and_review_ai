import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { DuplicateView } from "../viewTypes";
import { DuplicateNotice } from "./DuplicateNotice";

const make = (level: DuplicateView["level"], postingId = "p1"): DuplicateView => ({
  level,
  postingId,
  title: "Développeuse front",
  company: "Société Fictive",
  createdAt: "2026-11-03T12:00:00Z",
});

function setup(duplicates: DuplicateView[]) {
  const onOpen = vi.fn();
  const onDistinct = vi.fn();
  render(<DuplicateNotice duplicates={duplicates} onOpen={onOpen} onDistinct={onDistinct} />);
  return { onOpen, onDistinct };
}

describe("DuplicateNotice", () => {
  it("renders nothing without duplicate", () => {
    const { container } = render(
      <DuplicateNotice duplicates={[]} onOpen={vi.fn()} onDistinct={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("says the day for a certain duplicate, without any button", () => {
    setup([make("certain")]);
    expect(screen.getByText("Tu as déjà ajouté cette offre le 03/11.")).toBeInTheDocument();
    expect(screen.getByText(/Développeuse front \(Société Fictive\)/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("offers both actions for a probable duplicate", async () => {
    const { onOpen, onDistinct } = setup([make("probable", "p7")]);
    expect(screen.getByText("Offre très proche d'une offre déjà ajoutée.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ouvrir" }));
    expect(onOpen).toHaveBeenCalledExactlyOnceWith("p7");
    await userEvent.click(screen.getByRole("button", { name: "Ce sont deux offres distinctes" }));
    expect(onDistinct).toHaveBeenCalledExactlyOnceWith("p7");
  });

  it("only mentions a possible duplicate", () => {
    setup([make("possible")]);
    expect(screen.getByText("Cette offre ressemble à une offre déjà ajoutée.")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("describes each button with the offer it concerns", () => {
    setup([make("probable", "p1"), { ...make("probable", "p2"), title: "Autre poste" }]);
    const [first, second] = screen.getAllByRole("button", { name: "Ouvrir" });
    expect(first).toHaveAccessibleDescription(/Développeuse front/);
    expect(second).toHaveAccessibleDescription(/Autre poste/);
  });
});
