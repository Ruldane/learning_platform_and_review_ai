import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { field, goTo, next, pdf, setup, TITLES, title, withEnvKey } from "./welcomeTestkit";

const CV = "Ton CV (PDF, 10 Mo au plus)";
const send = () => screen.getByRole("button", { name: "Importer mes documents" });

describe("WelcomePage, CV step", () => {
  it("without any key, promises no reading and sends nothing", async () => {
    const { user, imports } = setup();
    await goTo(user, 3);
    await screen.findByText(/Aucune clé pour le moment/);
    await user.click(next("Plus tard"));
    await title(TITLES[3]!);
    await user.upload(field(CV), pdf());
    expect(send()).toHaveAttribute("aria-disabled", "true");
    expect(send()).toHaveAccessibleDescription(/Sans clé d'API, Tremplin ne peut pas lire/);
    await user.click(send());
    expect(imports).toEqual([]);
    expect(screen.queryByText(/Tremplin les lit en arrière-plan/)).toBeNull();
  });

  it("without a key, the way back to the key step is offered, and a key opens the import", async () => {
    const { user, imports } = setup();
    await goTo(user, 4);
    await user.click(screen.getByRole("button", { name: "Aller à l'étape de la clé" }));
    await title(TITLES[2]!);
    await screen.findByText(/Aucune clé pour le moment/);
    await user.selectOptions(field("Fournisseur"), "anthropic");
    await user.type(screen.getByLabelText("Clé API Anthropic"), "sk-ant-secret-1234");
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    await screen.findByText(/Une clé est déjà enregistrée \(Anthropic\)/);
    await user.click(next("Suivant"));
    await title(TITLES[3]!);
    await user.upload(field(CV), pdf());
    await user.click(send());
    expect(await screen.findByText(/Tes documents sont envoyés/)).toBeInTheDocument();
    expect(imports).toHaveLength(1);
  });

  it("with a key from the .env file, the import is open from the start", async () => {
    const { user } = setup({ keys: withEnvKey });
    await goTo(user, 4);
    expect(screen.queryByRole("button", { name: "Aller à l'étape de la clé" })).toBeNull();
    expect(send()).toHaveAccessibleDescription("Choisis d'abord ton CV.");
  });

  it("keeps the chosen files when the step changes, and says nothing left yet", async () => {
    const { user, imports } = setup({ keys: withEnvKey });
    await goTo(user, 4);
    await user.upload(field(CV), pdf());
    expect(screen.getByText(/Rien n'est envoyé tant que/)).toBeInTheDocument();
    await user.click(next("Passer"));
    await title(TITLES[4]!);
    await user.click(screen.getByRole("button", { name: "Précédent" }));
    await title(TITLES[3]!);
    expect(screen.getByText("Fichier retenu : cv.pdf")).toBeInTheDocument();
    expect(send()).toHaveAttribute("aria-disabled", "false");
    await user.click(send());
    expect(await screen.findByText(/Tes documents sont envoyés/)).toBeInTheDocument();
    expect(imports).toHaveLength(1);
  });
});
