import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DuplicateAlert } from "./DuplicateAlert";
import type { DuplicateAlertView } from "./DuplicateAlert";

const CERTAIN: DuplicateAlertView = {
  level: "certain",
  applicationId: "a1",
  company: "Acme",
  title: "Data engineer",
  status: "applied",
  message:
    "Attention, tu as déjà postulé chez Acme pour le poste Data engineer le 3 novembre (statut : Postulée).",
};
const PROBABLE: DuplicateAlertView = {
  level: "probable",
  applicationId: "a2",
  company: "Acme",
  title: "Data engineer (H/F)",
  status: "to_apply",
  message: "Attention, tu as déjà une fiche chez Acme pour le poste Data engineer (H/F).",
};
const INFO: DuplicateAlertView = {
  level: "info",
  applicationId: "a3",
  company: "Acme",
  title: "Analyste",
  status: "applied",
  message: "Pour info : tu as postulé chez Acme il y a 12 jours, pour le poste Analyste.",
};

function setup(alerts: DuplicateAlertView[]) {
  const handlers = { onOpen: vi.fn(), onDistinct: vi.fn(), onCancel: vi.fn() };
  render(<DuplicateAlert alerts={alerts} {...handlers} />);
  return handlers;
}

describe("DuplicateAlert", () => {
  it("shows the server message of the strongest alert, whatever the order", () => {
    setup([PROBABLE, CERTAIN]);
    const alert = screen.getByRole("alert");
    expect(within(alert).getByText(CERTAIN.message)).toBeInTheDocument();
  });

  it("says the level in words, not only with a colour", () => {
    setup([CERTAIN]);
    expect(screen.getByText("Doublon certain")).toBeInTheDocument();
  });

  it.each([
    ["certain", "Doublon certain"],
    ["probable", "Doublon probable"],
    ["possible", "Doublon possible"],
    ["info", "Pour info"],
  ] as const)("says the level in words for %s", (level, words) => {
    setup([{ ...PROBABLE, level }]);
    expect(screen.getByText(words)).toBeInTheDocument();
  });

  it("lists the other alerts with their level in words", () => {
    setup([CERTAIN, PROBABLE, INFO]);
    const others = screen.getByRole("list", { name: "Autres fiches proches" });
    const items = within(others).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Acme, Data engineer (H/F) (À postuler) : Doublon probable");
    expect(items[1]).toHaveTextContent("Acme, Analyste (Postulée) : Pour info");
  });

  it("offers the three choices of the spec and each calls its handler", async () => {
    const user = userEvent.setup();
    const handlers = setup([PROBABLE, CERTAIN]);
    await user.click(screen.getByRole("button", { name: "Ouvrir la fiche existante" }));
    await user.click(screen.getByRole("button", { name: "C'est un autre poste" }));
    await user.click(screen.getByRole("button", { name: "Annuler" }));
    expect(handlers.onOpen).toHaveBeenCalledWith("a1");
    expect(handlers.onDistinct).toHaveBeenCalledTimes(1);
    expect(handlers.onCancel).toHaveBeenCalledTimes(1);
  });

  it("renders an info alert as a simple note, with no choice", () => {
    setup([INFO]);
    expect(screen.getByRole("note")).toHaveTextContent(INFO.message);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("renders nothing when there is no alert", () => {
    const { container } = render(
      <DuplicateAlert alerts={[]} onOpen={vi.fn()} onDistinct={vi.fn()} onCancel={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
