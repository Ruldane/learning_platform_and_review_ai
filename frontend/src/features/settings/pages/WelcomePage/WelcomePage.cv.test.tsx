import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { field, goTo, next, pdf, setup, TITLES, title, withEnvKey } from "./welcomeTestkit";

const CV = "Your CV (PDF, 10 MB max)";
const KEY_STEP = "Go to the key step";
const send = () => screen.getByRole("button", { name: "Import my documents" });

describe("WelcomePage, CV step", () => {
  it("without any key, promises no reading and sends nothing", async () => {
    const { user, imports } = setup();
    await goTo(user, 3);
    await screen.findByText(/No key yet/);
    await user.click(next("Later"));
    await title(TITLES[3]!);
    await user.upload(field(CV), pdf());
    expect(send()).toHaveAttribute("aria-disabled", "true");
    expect(send()).toHaveAccessibleDescription(/Without an API key, Tremplin cannot read/);
    await user.click(send());
    expect(imports).toEqual([]);
    expect(screen.queryByText(/Tremplin reads them in the background/)).toBeNull();
  });

  it("without a key, the way back to the key step is offered, and a key opens the import", async () => {
    const { user, imports } = setup();
    await goTo(user, 4);
    await user.click(screen.getByRole("button", { name: KEY_STEP }));
    await title(TITLES[2]!);
    await screen.findByText(/No key yet/);
    await user.selectOptions(field("Provider"), "anthropic");
    await user.type(screen.getByLabelText("Anthropic API key"), "sk-ant-secret-1234");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByText(/A key is already saved \(Anthropic\)/);
    await user.click(next("Next"));
    await title(TITLES[3]!);
    await user.upload(field(CV), pdf());
    await user.click(send());
    expect(await screen.findByText(/Your documents have been sent/)).toBeInTheDocument();
    expect(imports).toHaveLength(1);
  });

  it("with a key from the .env file, the import is open from the start", async () => {
    const { user } = setup({ keys: withEnvKey });
    await goTo(user, 4);
    expect(screen.queryByRole("button", { name: KEY_STEP })).toBeNull();
    expect(send()).toHaveAccessibleDescription("Choose your CV first.");
  });

  it("keeps the chosen files when the step changes, and says nothing left yet", async () => {
    const { user, imports } = setup({ keys: withEnvKey });
    await goTo(user, 4);
    await user.upload(field(CV), pdf());
    expect(screen.getByText(/Nothing is sent until/)).toBeInTheDocument();
    await user.click(next("Skip"));
    await title(TITLES[4]!);
    await user.click(screen.getByRole("button", { name: "Previous" }));
    await title(TITLES[3]!);
    expect(screen.getByText("Selected file: cv.pdf")).toBeInTheDocument();
    expect(send()).toHaveAttribute("aria-disabled", "false");
    await user.click(send());
    expect(await screen.findByText(/Your documents have been sent/)).toBeInTheDocument();
    expect(imports).toHaveLength(1);
  });
});
