import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { OnboardingSteps } from "./OnboardingSteps";

const BODY = "Contenu de l'étape";

function setup(over: Partial<Parameters<typeof OnboardingSteps>[0]> = {}) {
  const handlers = { onPrevious: vi.fn(), onNext: vi.fn(), onSkipAll: vi.fn() };
  const props = {
    step: 2,
    total: 5,
    title: "Ce qui sort de ta machine",
    nextLabel: "Suivant",
    busy: false,
    error: null,
    ...handlers,
    ...over,
  };
  const view = render(
    <OnboardingSteps {...props}>
      <p>{BODY}</p>
    </OnboardingSteps>,
  );
  const again = (next: Partial<typeof props>) =>
    view.rerender(
      <OnboardingSteps {...props} {...next}>
        <p>{BODY}</p>
      </OnboardingSteps>,
    );
  return { ...handlers, again, user: userEvent.setup() };
}

describe("OnboardingSteps", () => {
  it("says which step it is on and gives the focus to the step title", () => {
    setup();
    expect(screen.getByText("Étape 2 sur 5")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 1, name: "Ce qui sort de ta machine" }),
    ).toHaveFocus();
    expect(screen.getByText(BODY)).toBeInTheDocument();
  });

  it("reads the step counter with the title, which has the focus", () => {
    const { again } = setup();
    const title = () => screen.getByRole("heading", { level: 1 });
    expect(title()).toHaveAccessibleDescription("Étape 2 sur 5");
    again({ step: 4, title: "Ton CV" });
    expect(title()).toHaveAccessibleDescription("Étape 4 sur 5");
  });

  it("moves the focus to the new title when the step changes", () => {
    const { again } = setup();
    again({ step: 3, title: "Ta clé d'API" });
    expect(screen.getByText("Étape 3 sur 5")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Ta clé d'API" })).toHaveFocus();
  });

  it("offers no previous button on the first step, and one on the others", async () => {
    const { again, onPrevious, user } = setup({ step: 1 });
    expect(screen.queryByRole("button", { name: "Précédent" })).toBeNull();
    again({ step: 3 });
    await user.click(screen.getByRole("button", { name: "Précédent" }));
    expect(onPrevious).toHaveBeenCalledTimes(1);
  });

  it("goes on with the label of the step and skips the whole welcome from every step", async () => {
    const { again, onNext, onSkipAll, user } = setup({ nextLabel: "Plus tard" });
    await user.click(screen.getByRole("button", { name: "Plus tard" }));
    expect(onNext).toHaveBeenCalledTimes(1);
    for (const step of [1, 2, 3, 4, 5]) {
      again({ step });
      await user.click(screen.getByRole("button", { name: "Passer l'accueil" }));
    }
    expect(onSkipAll).toHaveBeenCalledTimes(5);
  });

  it("keeps a blocked next button focusable, gives the reason, and ignores the click", async () => {
    const { onNext, user } = setup({
      step: 5,
      nextLabel: "Terminer",
      nextBlockedReason: "Corrige les champs signalés avant de terminer.",
    });
    const next = screen.getByRole("button", { name: "Terminer" });
    expect(next).toHaveAttribute("aria-disabled", "true");
    expect(next).not.toBeDisabled();
    expect(next).toHaveAccessibleDescription("Corrige les champs signalés avant de terminer.");
    await user.click(next);
    expect(onNext).not.toHaveBeenCalled();
  });

  it("ignores every action while it is saving, without disabling the buttons", async () => {
    const { onNext, onPrevious, onSkipAll, user } = setup({ busy: true, nextLabel: "Terminer" });
    expect(screen.getByRole("button", { name: "Enregistrement…" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    await user.click(screen.getByRole("button", { name: "Enregistrement…" }));
    await user.click(screen.getByRole("button", { name: "Précédent" }));
    await user.click(screen.getByRole("button", { name: "Passer l'accueil" }));
    expect(onNext).not.toHaveBeenCalled();
    expect(onPrevious).not.toHaveBeenCalled();
    expect(onSkipAll).not.toHaveBeenCalled();
  });

  it("announces a failed save", () => {
    setup({ error: "Le serveur a échoué." });
    expect(screen.getByRole("alert")).toHaveTextContent("Le serveur a échoué.");
  });
});
