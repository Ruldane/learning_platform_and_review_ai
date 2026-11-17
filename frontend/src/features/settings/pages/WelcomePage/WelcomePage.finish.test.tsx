import { act, fireEvent, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { refusedFieldsResponse } from "@/test/settingsApi";
import { settingsKeys } from "../../queryKeys";
import { finish, goTo, next, setup, skipAll, TITLES, title } from "./welcomeTestkit";

describe("WelcomePage, finishing and leaving a step", () => {
  it("two activations of « Passer l'accueil » in the same instant send one save", async () => {
    const { puts } = setup();
    await title(TITLES[0]!);
    act(() => {
      fireEvent.click(skipAll());
      fireEvent.click(skipAll());
    });
    expect(await screen.findByText("Accueil de Tremplin")).toBeInTheDocument();
    expect(puts).toHaveLength(1);
  });

  it("two activations of « Terminer » in the same instant send one save", async () => {
    const { user, puts } = setup();
    await goTo(user, 5);
    act(() => {
      fireEvent.click(finish());
      fireEvent.click(finish());
    });
    expect(await screen.findByText("Accueil de Tremplin")).toBeInTheDocument();
    expect(puts).toHaveLength(1);
  });

  it("drops the error of a failed save when the step changes", async () => {
    let calls = 0;
    const { user } = setup({
      put: () => (++calls === 1 ? refusedFieldsResponse("brief_time") : undefined),
    });
    await title(TITLES[0]!);
    await user.click(skipAll());
    expect(await screen.findByRole("alert")).toHaveTextContent("Requête invalide");
    await user.click(next("Suivant"));
    await title(TITLES[1]!);
    expect(screen.queryByRole("alert")).toBeNull();

    await user.click(skipAll());
    expect(await screen.findByText("Accueil de Tremplin")).toBeInTheDocument();
  });

  it("drops the error of a failed save when going back", async () => {
    let calls = 0;
    const { user } = setup({
      put: () => (++calls === 1 ? refusedFieldsResponse("brief_time") : undefined),
    });
    await goTo(user, 2);
    await user.click(skipAll());
    expect(await screen.findByRole("alert")).toHaveTextContent("Requête invalide");
    await user.click(screen.getByRole("button", { name: "Précédent" }));
    await title(TITLES[0]!);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("reads the model only while step 1 is on screen", async () => {
    const { user, client } = setup();
    await title(TITLES[0]!);
    const observers = () =>
      client
        .getQueryCache()
        .find({ queryKey: settingsKeys.onboardingEmbedding })
        ?.getObserversCount() ?? 0;
    const health = () =>
      client
        .getQueryCache()
        .find({ queryKey: settingsKeys.onboardingHealth })
        ?.getObserversCount() ?? 0;
    expect(observers()).toBe(1);
    expect(health()).toBe(1);
    await user.click(next("Suivant"));
    await title(TITLES[1]!);
    expect(observers()).toBe(0);
    expect(health()).toBe(0);
  });
});
