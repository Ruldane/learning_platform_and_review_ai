import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import {
  field,
  finish,
  goTo,
  next,
  pdf,
  setup,
  TITLES,
  title,
  withBraveOnly,
  withEnvKey,
} from "./welcomeTestkit";

const CV = "Your CV (PDF, 10 MB max)";
const IMPORT = "Import my documents";

describe("WelcomePage, key and CV steps", () => {
  it("key step accepts env key and moves on", async () => {
    const { user, saved } = setup({ keys: withEnvKey });
    await goTo(user, 3);
    expect(
      await screen.findByText(/A key is already provided by the \.env file \(OpenAI\)/),
    ).toBeInTheDocument();
    await user.click(next("Next"));
    expect(await title(TITLES[3]!)).toBeInTheDocument();
    expect(saved).toEqual([]);
  });

  it("key step saves a key, never shows it, and tests it", async () => {
    const { user, saved, tested } = setup({ keyTest: { ok: true, message: "API key is valid." } });
    await goTo(user, 3);
    await screen.findByText(/No key yet/);
    await user.selectOptions(field("Provider"), "anthropic");
    await user.type(screen.getByLabelText("Anthropic API key"), "sk-ant-secret-1234");
    expect(document.body.innerHTML).not.toContain("sk-ant-secret-1234");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText(/A key is already saved \(Anthropic\)/)).toBeVisible();
    expect(saved).toEqual(["anthropic"]);
    expect(document.body.innerHTML).not.toContain("sk-ant-secret-1234");
    await user.click(screen.getByRole("button", { name: "Test" }));
    expect(await screen.findByText("API key is valid.")).toBeInTheDocument();
    expect(tested).toEqual(["anthropic"]);
    expect(next("Next")).toBeInTheDocument();
  });

  it("key step can be left for later, without any key", async () => {
    const { user, saved } = setup();
    await goTo(user, 3);
    await screen.findByText(/No key yet/);
    await user.click(next("Later"));
    expect(await title(TITLES[3]!)).toBeInTheDocument();
    expect(saved).toEqual([]);
  });

  it("key step: after a failed read and Réessayer, the focus goes to the first field", async () => {
    // Deux lectures ratées : à l'ouverture de la page, puis à l'étape (relue au montage).
    const { user } = setup({ keysFailures: 2 });
    await goTo(user, 3);
    expect(await screen.findByRole("alert")).toHaveTextContent("Le serveur a échoué.");
    // L'erreur ne retire ni le titre ni la navigation de l'étape.
    expect(screen.getByRole("heading", { level: 1, name: TITLES[2]! })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByText(/No key yet/);
    await waitFor(() => expect(field("Provider")).toHaveFocus());
  });

  it("cv step can be skipped", async () => {
    const { user, imports } = setup();
    await goTo(user, 4);
    await user.click(next("Skip"));
    expect(await title(TITLES[4]!)).toBeInTheDocument();
    expect(imports).toEqual([]);
  });

  it("cv step sends the documents as a multipart form and goes on", async () => {
    const { user, imports } = setup({ keys: withEnvKey });
    await goTo(user, 4);
    await user.upload(field(CV), pdf());
    await user.upload(field("Your LinkedIn profile (PDF, optional)"), pdf("linkedin.pdf"));
    await user.click(screen.getByRole("button", { name: IMPORT }));
    expect(await screen.findByText(/Your documents have been sent/)).toBeInTheDocument();
    expect(imports).toHaveLength(1);
    expect(imports[0]!.contentType).toContain("multipart/form-data");
    await user.click(next("Next"));
    expect(await title(TITLES[4]!)).toBeInTheDocument();
  });

  it("cv step shows a refusal of the server and lets the person skip anyway", async () => {
    const { user } = setup({
      keys: withEnvKey,
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
    await user.upload(field(CV), pdf());
    await user.click(screen.getByRole("button", { name: IMPORT }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Une lecture est déjà en cours.");
    await user.click(next("Skip"));
    expect(await title(TITLES[4]!)).toBeInTheDocument();
  });
  it("a Brave key alone is not a key for the models: not offered, not counted", async () => {
    const { user, imports } = setup({ keys: withBraveOnly });
    await goTo(user, 3);
    expect(await screen.findByText(/No key yet/)).toBeInTheDocument();
    expect(screen.queryByText(/Brave/)).toBeNull();
    const options = within(field("Provider")).getAllByRole("option");
    expect(options.map((option) => option.textContent)).toEqual([
      "Anthropic",
      "OpenAI",
      "GLM (Z.ai)",
    ]);
    await user.click(next("Later"));
    await title(TITLES[3]!);
    await user.upload(field(CV), pdf());
    expect(screen.getByText(/Without an API key, Tremplin cannot read/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: IMPORT })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(imports).toEqual([]);
  });

  it("explains which provider the API key must belong to", async () => {
    const { user } = setup();
    await goTo(user, 3);
    expect(screen.getByText(/must belong to your models' provider/)).toBeInTheDocument();
  });

  it("a key of the provider the models already use changes no setting", async () => {
    const keys = withEnvKey.map((key) => ({
      ...key,
      source: key.provider === "anthropic" ? "env" : null,
    }));
    const { user, puts } = setup({ keys });
    await goTo(user, 3);
    expect(await screen.findByText(/provided by the \.env file \(Anthropic\)/)).toBeVisible();
    expect(screen.queryByText(/Your models will switch to/)).toBeNull();
    await user.click(next("Next"));
    await title(TITLES[3]!);
    expect(puts).toEqual([]);
  });

  it("a key of another provider moves the models to it, says so, and lets the CV be read", async () => {
    const { user, puts, imports } = setup({ keys: withBraveOnly });
    await goTo(user, 3);
    await screen.findByText(/No key yet/);
    await user.selectOptions(field("Provider"), "glm");
    await user.type(screen.getByLabelText("GLM (Z.ai) API key"), "glm-secret-1234");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText(/Your models will switch to GLM \(Z\.ai\)/)).toBeVisible();
    expect(puts).toEqual([]);

    await user.click(next("Next"));
    await title(TITLES[3]!);
    expect(puts).toHaveLength(1);
    const tiers = puts[0]!.tiers as Record<string, { provider: string }>;
    expect(Object.values(tiers).map((tier) => tier.provider)).toEqual(["glm", "glm", "glm", "glm"]);
    expect(puts[0]!.onboarding_done).toBe(false);

    await user.upload(field(CV), pdf());
    await user.click(screen.getByRole("button", { name: IMPORT }));
    expect(await screen.findByText(/Your documents have been sent/)).toBeInTheDocument();
    expect(imports).toHaveLength(1);

    // « Terminer » garde ces modèles (le dernier envoi part des réglages relus).
    await user.click(next("Next"));
    await title(TITLES[4]!);
    await user.click(finish());
    await screen.findByText("Accueil de Tremplin");
    const last = puts.at(-1)!;
    expect(last.onboarding_done).toBe(true);
    expect((last.tiers as Record<string, { provider: string }>).fort!.provider).toBe("glm");
  });

  it("says why when the models cannot be moved, and stays on the step", async () => {
    const { user, puts } = setup({
      keys: withEnvKey,
      put: () =>
        HttpResponse.json(
          { error: { code: "boom", message: "Le serveur a échoué.", details: null } },
          { status: 500 },
        ),
    });
    await goTo(user, 3);
    await user.click(next("Next"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Le serveur a échoué.");
    expect(screen.getByRole("heading", { level: 1, name: TITLES[2]! })).toBeInTheDocument();
    expect(puts).toHaveLength(1);
  });
});
