import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderRoutes } from "@/test/renderRoutes";
import { closedGate, refusedFieldsResponse, settingsApi } from "@/test/settingsApi";
import { server } from "@/test/server";
import { settingsFixture } from "../../fixtures";
import { StylePage } from "./StylePage";

const overrides = { tutor: { provider: "openai", model: "gpt-6-luna" } };
const stored = { ...settingsFixture, style_guide: "Phrases courtes.", agent_overrides: overrides };

function setup(put?: Parameters<typeof settingsApi>[0]["put"], gate?: Promise<void>) {
  const api = settingsApi({ settings: stored, put, gate });
  server.use(...api.handlers);
  const view = renderRoutes(
    [{ path: "/settings/style", element: <StylePage /> }],
    "/settings/style",
  );
  return { ...api, ...view };
}

const guide = () => screen.getByLabelText("Personal style guide");
const save = () => screen.getByRole("button", { name: "Save" });

describe("StylePage", () => {
  it("style guide saves", async () => {
    const { puts, user } = setup();
    await screen.findByRole("heading", { level: 1, name: "Style" });
    expect(guide()).toHaveValue("Phrases courtes.");
    expect(screen.getByText("16 characters")).toBeInTheDocument();
    expect(save()).toHaveAttribute("aria-disabled", "true");

    await user.clear(guide());
    await user.type(guide(), "Tutoiement, pas de jargon.");
    expect(screen.getByText("26 characters")).toBeInTheDocument();
    expect(screen.getByText("Unsaved changes.")).toBeInTheDocument();
    expect(puts).toEqual([]);
    await user.click(save());

    expect(await screen.findByText("Style guide saved.")).toBeInTheDocument();
    expect(puts).toHaveLength(1);
    expect(puts[0]).toMatchObject({
      style_guide: "Tutoiement, pas de jargon.",
      onboarding_done: true,
      agent_overrides: overrides,
      tiers: settingsFixture.tiers,
      brief_time: "07:00",
    });
    expect(puts[0]).not.toHaveProperty("vision_enabled");
  });

  it("keeps what is typed while the save is running, and still says it is not saved", async () => {
    const held = closedGate();
    const { user, puts } = setup(undefined, held.promise);
    await screen.findByRole("heading", { level: 1, name: "Style" });
    await user.clear(guide());
    await user.type(guide(), "Version A");
    await user.click(save());
    await waitFor(() => expect(puts).toHaveLength(1)); // l'envoi est en cours, tenu par la porte
    await user.type(guide(), " et B"); // pendant l'envoi
    held.open();
    expect(puts[0]).toMatchObject({ style_guide: "Version A" });
    await screen.findByText("Unsaved changes.");
    expect(guide()).toHaveValue("Version A et B");
  });

  it("keeps the focus on the save button, says why it is blocked, counts thousands", async () => {
    const { user } = setup();
    await screen.findByRole("heading", { level: 1, name: "Style" });
    await user.click(save());
    expect(save()).toHaveFocus();
    expect(save()).toHaveAccessibleDescription("Nothing to save.");
    await user.clear(guide());
    await user.click(guide());
    await user.paste("x".repeat(12000));
    expect(screen.getByText("12,000 characters")).toBeInTheDocument();
    await user.click(save());
    await screen.findByText("Style guide saved.");
    expect(save()).toHaveFocus();
  });

  it("counts one character in the singular and an empty guide as zero", async () => {
    const api = settingsApi({ settings: { ...stored, style_guide: "a" } });
    server.use(...api.handlers);
    const { user } = renderRoutes(
      [{ path: "/settings/style", element: <StylePage /> }],
      "/settings/style",
    );
    expect(await screen.findByText("1 character")).toBeInTheDocument();
    await user.clear(guide());
    expect(screen.getByText("0 characters")).toBeInTheDocument();
  });

  it("flags the field, without echoing the text, when the server refuses it", async () => {
    const { user } = setup(() => refusedFieldsResponse("style_guide"));
    await screen.findByRole("heading", { level: 1, name: "Style" });
    await user.clear(guide());
    await user.type(guide(), "Texte secret");
    await user.click(save());
    await screen.findByRole("alert");
    expect(guide()).toHaveAttribute("aria-invalid", "true");
    expect(guide()).toHaveValue("Texte secret");
    expect(
      screen.getByText("Error: The server refused this value: check it."),
    ).toBeInTheDocument();
    // ni le message ni l'indication ne citent le texte refusé
    expect(screen.getByRole("alert")).not.toHaveTextContent("Texte secret");
  });
});
