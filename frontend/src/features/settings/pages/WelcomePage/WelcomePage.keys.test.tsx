import { screen, waitFor } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { field, goTo, next, pdf, setup, TITLES, title, withEnvKey } from "./welcomeTestkit";

describe("WelcomePage, key and CV steps", () => {
  it("key step accepts env key and moves on", async () => {
    const { user, saved } = setup({ keys: withEnvKey });
    await goTo(user, 3);
    expect(
      await screen.findByText(/Une clé est déjà fournie par le fichier \.env \(OpenAI\)/),
    ).toBeInTheDocument();
    await user.click(next("Suivant"));
    expect(await title(TITLES[3]!)).toBeInTheDocument();
    expect(saved).toEqual([]);
  });

  it("key step saves a key, never shows it, and tests it", async () => {
    const { user, saved, tested } = setup({ keyTest: { ok: true, message: "Clé valide." } });
    await goTo(user, 3);
    await screen.findByText(/Aucune clé pour le moment/);
    await user.selectOptions(field("Fournisseur"), "anthropic");
    await user.type(screen.getByLabelText("Clé API Anthropic"), "sk-ant-secret-1234");
    expect(document.body.innerHTML).not.toContain("sk-ant-secret-1234");
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByText(/Une clé est déjà enregistrée \(Anthropic\)/)).toBeVisible();
    expect(saved).toEqual(["anthropic"]);
    expect(document.body.innerHTML).not.toContain("sk-ant-secret-1234");
    await user.click(screen.getByRole("button", { name: "Tester" }));
    expect(await screen.findByText("Clé valide.")).toBeInTheDocument();
    expect(tested).toEqual(["anthropic"]);
    expect(next("Suivant")).toBeInTheDocument();
  });

  it("key step can be left for later, without any key", async () => {
    const { user, saved } = setup();
    await goTo(user, 3);
    await screen.findByText(/Aucune clé pour le moment/);
    await user.click(next("Plus tard"));
    expect(await title(TITLES[3]!)).toBeInTheDocument();
    expect(saved).toEqual([]);
  });

  it("key step: after a failed read and Réessayer, the focus goes to the first field", async () => {
    const { user } = setup({ keysFailures: 1 });
    await goTo(user, 3);
    expect(await screen.findByRole("alert")).toHaveTextContent("Le serveur a échoué.");
    // L'erreur ne retire ni le titre ni la navigation de l'étape.
    expect(screen.getByRole("heading", { level: 1, name: TITLES[2]! })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    await screen.findByText(/Aucune clé pour le moment/);
    await waitFor(() => expect(field("Fournisseur")).toHaveFocus());
  });

  it("cv step can be skipped", async () => {
    const { user, imports } = setup();
    await goTo(user, 4);
    await user.click(next("Passer"));
    expect(await title(TITLES[4]!)).toBeInTheDocument();
    expect(imports).toEqual([]);
  });

  it("cv step sends the documents as a multipart form and goes on", async () => {
    const { user, imports } = setup();
    await goTo(user, 4);
    await user.upload(field("Ton CV (PDF, 10 Mo au plus)"), pdf());
    await user.upload(field("Ton profil LinkedIn (PDF, facultatif)"), pdf("linkedin.pdf"));
    await user.click(screen.getByRole("button", { name: "Importer mes documents" }));
    expect(await screen.findByText(/Tes documents sont envoyés/)).toBeInTheDocument();
    expect(imports).toHaveLength(1);
    expect(imports[0]!.contentType).toContain("multipart/form-data");
    await user.click(next("Suivant"));
    expect(await title(TITLES[4]!)).toBeInTheDocument();
  });

  it("cv step shows a refusal of the server and lets the person skip anyway", async () => {
    const { user } = setup({
      importProfile: () =>
        HttpResponse.json(
          {
            error: {
              code: "capture_in_progress",
              message: "Une lecture est déjà en cours.",
              details: null,
            },
          },
          { status: 409 },
        ),
    });
    await goTo(user, 4);
    await user.upload(field("Ton CV (PDF, 10 Mo au plus)"), pdf());
    await user.click(screen.getByRole("button", { name: "Importer mes documents" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Une lecture est déjà en cours.");
    await user.click(next("Passer"));
    expect(await title(TITLES[4]!)).toBeInTheDocument();
  });
});
