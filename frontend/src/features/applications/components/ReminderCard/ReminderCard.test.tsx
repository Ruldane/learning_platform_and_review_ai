import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { makeContact, makeReminder } from "../fixtures";
import type { ReminderView } from "../viewTypes";
import { ReminderCard } from "./ReminderCard";

function setup(reminder: ReminderView = makeReminder(), onCopy = vi.fn()) {
  const handlers = { onCopy, onDone: vi.fn(), onPostpone: vi.fn(), onIgnore: vi.fn() };
  render(<ReminderCard reminder={reminder} {...handlers} />);
  return handlers;
}

describe("ReminderCard", () => {
  it("shows who to contact with their role, the due date and the application", () => {
    setup();
    expect(screen.getByText("Camille Durand, Responsable data")).toBeInTheDocument();
    expect(screen.getByText("À faire le 12/11/2026")).toBeInTheDocument();
    expect(screen.getByText("Acme, poste Data engineer")).toBeInTheDocument();
    expect(screen.getByText("Relance LinkedIn à 7 jours")).toBeInTheDocument();
  });

  it("shows only the name when the contact has no role", () => {
    setup(makeReminder({ contact: makeContact({ name: "Sam", role: null }) }));
    expect(screen.getByText("Sam")).toBeInTheDocument();
  });

  it("offers a LinkedIn search that opens in a new tab when there is no contact", () => {
    setup(
      makeReminder({
        contact: null,
        linkedinSearchUrl: "https://www.linkedin.com/search/results/people/?keywords=Acme",
      }),
    );
    const link = screen.getByRole("link", { name: /Chercher sur LinkedIn/ });
    expect(link).toHaveAttribute(
      "href",
      "https://www.linkedin.com/search/results/people/?keywords=Acme",
    );
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
    expect(link).toHaveAccessibleName("Chercher sur LinkedIn (s'ouvre dans un nouvel onglet)");
  });

  it("never renders a link for an address that is not http or https", () => {
    setup(makeReminder({ contact: null, linkedinSearchUrl: "javascript:alert(1)" }));
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByText("Aucun contact enregistré.")).toBeInTheDocument();
  });

  it("shows the draft in a readable block", () => {
    setup();
    const draft = screen.getByRole("group", { name: "Brouillon" });
    expect(draft).toHaveTextContent("J'ai postulé au poste de Data engineer chez Acme.");
  });

  it("always says that nothing is sent by the application", () => {
    setup();
    expect(
      screen.getByText("Rien n'est envoyé par l'application : copie et envoie toi-même."),
    ).toBeInTheDocument();
  });

  it("has the four buttons and each one calls its handler", async () => {
    const user = userEvent.setup();
    const handlers = setup();
    await user.click(screen.getByRole("button", { name: "Copier" }));
    await user.click(screen.getByRole("button", { name: "Fait" }));
    await user.click(screen.getByRole("button", { name: "Reporter de 3 jours" }));
    await user.click(screen.getByRole("button", { name: "Ignorer" }));
    expect(handlers.onCopy).toHaveBeenCalledWith(makeReminder().draft);
    expect(handlers.onDone).toHaveBeenCalledWith("r1");
    expect(handlers.onPostpone).toHaveBeenCalledWith("r1");
    expect(handlers.onIgnore).toHaveBeenCalledWith("r1");
  });

  it("confirms the copy in a live region", async () => {
    const user = userEvent.setup();
    setup(makeReminder(), vi.fn().mockResolvedValue(undefined));
    await user.click(screen.getByRole("button", { name: "Copier" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Brouillon copié.");
  });

  it("says when the copy failed", async () => {
    const user = userEvent.setup();
    setup(makeReminder(), vi.fn().mockRejectedValue(new Error("denied")));
    await user.click(screen.getByRole("button", { name: "Copier" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Copie impossible : sélectionne le texte du brouillon.",
    );
  });

  it("forgets the copy message when the same card receives another reminder", async () => {
    const user = userEvent.setup();
    const handlers = {
      onCopy: vi.fn().mockResolvedValue(undefined),
      onDone: vi.fn(),
      onPostpone: vi.fn(),
      onIgnore: vi.fn(),
    };
    const { rerender } = render(<ReminderCard reminder={makeReminder()} {...handlers} />);
    await user.click(screen.getByRole("button", { name: "Copier" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Brouillon copié.");
    rerender(<ReminderCard reminder={makeReminder({ id: "r2" })} {...handlers} />);
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
  });

  it("offers to file the application as Sans réponse instead of Fait for close_21", async () => {
    const user = userEvent.setup();
    const handlers = setup(makeReminder({ kind: "close_21", draft: "Acme ne t'a pas répondu." }));
    expect(screen.queryByRole("button", { name: "Fait" })).toBeNull();
    expect(screen.getByText("Classer la fiche ?")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Classer en Sans réponse" }));
    expect(handlers.onDone).toHaveBeenCalledWith("r1");
    expect(screen.getByRole("button", { name: "Reporter de 3 jours" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ignorer" })).toBeInTheDocument();
  });

  it("shows the question to January as the block for close_21", () => {
    setup(makeReminder({ kind: "close_21", draft: "Acme ne t'a pas répondu." }));
    expect(screen.getByRole("group", { name: "Brouillon" })).toHaveTextContent(
      "Acme ne t'a pas répondu.",
    );
  });

  it("is a level 2 heading by default, and level 4 under a drawer section", () => {
    const { unmount } = render(
      <ReminderCard
        reminder={makeReminder()}
        {...{ onCopy: vi.fn(), onDone: vi.fn(), onPostpone: vi.fn(), onIgnore: vi.fn() }}
      />,
    );
    expect(
      screen.getByRole("heading", { level: 2, name: "Relance LinkedIn à 7 jours" }),
    ).toBeVisible();
    unmount();
    render(
      <ReminderCard
        reminder={makeReminder()}
        headingLevel={4}
        {...{ onCopy: vi.fn(), onDone: vi.fn(), onPostpone: vi.fn(), onIgnore: vi.fn() }}
      />,
    );
    expect(screen.getByRole("heading", { level: 4 })).toBeVisible();
  });

  it("disables Fait, Reporter and Ignorer and says it is busy while an action is pending", async () => {
    const user = userEvent.setup();
    const handlers = { onCopy: vi.fn(), onDone: vi.fn(), onPostpone: vi.fn(), onIgnore: vi.fn() };
    render(<ReminderCard reminder={makeReminder()} pending {...handlers} />);
    expect(screen.getByRole("article")).toHaveAttribute("aria-busy", "true");
    for (const name of ["Fait", "Reporter de 3 jours", "Ignorer"]) {
      expect(screen.getByRole("button", { name })).toBeDisabled();
    }
    expect(screen.getByRole("button", { name: "Copier" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Fait" }));
    expect(handlers.onDone).not.toHaveBeenCalled();
  });
});
