import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { applicationOut } from "@/test/applicationsApi";
import { openStream, renderApplications } from "@/test/applicationsHarness";
import { councilEvents } from "@/test/councilEvents";
import { apiError } from "@/test/councilHarness";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { kitApi, kitItem, type KitApiOptions } from "@/test/kitApi";
import { server } from "@/test/server";
import { applicationsManifest } from "../../manifest";
import { KitPage } from "./KitPage";

const KIT_ROUTE = "applications/:applicationId/kit";

function setup(options: KitApiOptions = {}, api: Parameters<typeof renderApplications>[2] = {}) {
  const sockets = createFakeSocketServer();
  const kit = kitApi(options);
  server.use(...kit.handlers);
  const routes = applicationsManifest.routes.map((route) =>
    route.path === KIT_ROUTE
      ? { path: route.path, element: <KitPage createSocket={sockets.factory} /> }
      : route,
  );
  const view = renderApplications(routes, "/applications/a1/kit", {
    applications: [applicationOut({ id: "a1", company: "Acme", title: "Data engineer" })],
    ...api,
  });
  return { ...view, sockets, kit };
}

const piece = (title: string) => screen.findByRole("region", { name: title });

describe("KitPage", () => {
  beforeEach(() => useSessionStore.getState().reset("k1"));

  it("introduces the kit before it is generated: the application, the promise, one button", async () => {
    setup();
    expect(
      await screen.findByRole("heading", { level: 1, name: "Application kit" }),
    ).toBeVisible();
    expect(await screen.findByText("Acme, Data engineer")).toBeVisible();
    expect(screen.getByText(/The app sends nothing/)).toBeVisible();
    expect(await screen.findByText(/The kit hasn't been generated yet/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Generate the kit" })).toBeEnabled();
    expect(screen.queryByRole("region", { name: "Cover letter" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Download the archive" })).toBeNull();
    expect(screen.getByRole("link", { name: "Back to the application" })).toHaveAttribute(
      "href",
      "/applications/a1",
    );
  });

  it("starts the kit, follows its session and shows each piece as it arrives, announced aloud", async () => {
    const { user, sockets, kit } = setup();
    await user.click(await screen.findByRole("button", { name: "Generate the kit" }));
    await waitFor(() => expect(kit.state.starts).toBe(1));
    const stream = await openStream(sockets, "k1");
    expect(await screen.findByText(/The kit is being prepared/)).toHaveFocus();
    expect(screen.queryByRole("button", { name: "Generate the kit" })).toBeNull();
    expect((await piece("Cover letter")).textContent).toContain("Preparing");

    const e = councilEvents("k1");
    kit.arrive("letter", { content: "Madame, Monsieur,", words: 2 });
    stream.push(e.artifactReady("kit_item", "k-letter", null));
    const letter = within(await piece("Cover letter"));
    await waitFor(() =>
      expect(letter.getByLabelText("Text: Cover letter")).toHaveValue("Madame, Monsieur,"),
    );
    expect(letter.getByText("Ready")).toBeVisible();
    expect(await screen.findByText("Cover letter: ready.")).toBeInTheDocument();
    expect(screen.getByText("1 of 7 pieces has arrived.")).toBeVisible();

    kit.arrive("pitch", { status: "to_check", flags: ["Kubernetes"], content: "Je suis Camille." });
    stream.push(e.artifactReady("kit_item", "k-pitch", null));
    expect(await screen.findByText("Elevator pitch: to check.")).toBeInTheDocument();
    expect(within(await piece("Elevator pitch")).getByRole("note")).toHaveTextContent(
      "Not in your profile: Kubernetes.",
    );
    // The letter remains ready without another announcement.
    expect(screen.getByText("2 of 7 pieces have arrived.")).toBeVisible();
  });

  it("reads the kit again at the end of the run even when an artifact.ready was lost", async () => {
    const { user, sockets, kit } = setup();
    await user.click(await screen.findByRole("button", { name: "Generate the kit" }));
    const stream = await openStream(sockets, "k1");
    const e = councilEvents("k1");
    // The server saved two pieces while the connection was down.
    kit.arrive("cv", { content: "CV ciblé" });
    kit.arrive("followups", {
      status: "failed",
      content: "",
      error: "The model did not respond.",
      words: null,
    });
    kit.finish();
    stream.push(e.completed());
    const followups = within(await piece("Follow-ups"));
    expect(await followups.findByText("Failed")).toBeVisible();
    expect(followups.getByRole("note")).toHaveTextContent("The model did not respond.");
    expect((await piece("Tailored résumé")).textContent).toContain("Ready");
    const summary = /The kit is done: 1 piece ready, 0 pieces to check, 1 piece failed\./;
    expect(await screen.findByText(summary)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Regenerate the kit" })).toBeVisible();
  });

  it.each([
    ["posting_required", /no linked posting or posting text.*Add the posting text/],
    ["profile_required", /No validated master profile/],
  ])("explains a refused start (%s) and keeps the button", async (code, message) => {
    const { user } = setup({
      start: () => HttpResponse.json(apiError(code, "Refused."), { status: 409 }),
    });
    await user.click(await screen.findByRole("button", { name: "Generate the kit" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.getByRole("button", { name: "Generate the kit" })).toBeEnabled();
    if (code === "profile_required") {
      expect(screen.getByRole("link", { name: "Open my profile" })).toHaveAttribute(
        "href",
        "/career/profile",
      );
    }
  });

  it("shows why a piece is to check even with no flag: salary answers and a brief without sources", async () => {
    setup({
      items: [
        kitItem("form_answers", {
          status: "to_check",
          salary_fields: 1,
          content: "### Quelles sont vos prétentions ?\nÀ remplir par toi",
        }),
        kitItem("company_brief", {
          status: "to_check",
          content: "Acme [1]",
          sources: [{ rank: 1, url: "https://example.org/acme", title: "Acme, le site" }],
        }),
      ],
    });
    const form = within(await piece("Form answers"));
    expect(form.getByRole("note")).toHaveTextContent("1 salary answer is for you to fill in");
    expect(form.getByLabelText("Quelles sont vos prétentions ?")).toHaveAccessibleDescription(
      "For you to fill in",
    );
    const brief = within(await piece("Company brief"));
    expect(brief.getByRole("note")).toHaveTextContent(/Unsourced passages were removed/);
    expect(brief.getByRole("link", { name: /Acme, le site/ })).toHaveAttribute(
      "href",
      "https://example.org/acme",
    );
  });

  it("saves an edit only on request, re-reads a piece to check and shows its new status", async () => {
    const { user, kit } = setup({
      items: [
        kitItem("letter", {
          status: "to_check",
          flags: ["Kubernetes"],
          content: "Avec Kubernetes.",
        }),
      ],
    });
    const letter = within(await piece("Cover letter"));
    await user.clear(letter.getByLabelText("Text: Cover letter"));
    await user.type(letter.getByLabelText("Text: Cover letter"), "Sans le terme.");
    expect(kit.state.patches).toEqual([]);
    await user.click(letter.getByRole("button", { name: "Save: Cover letter" }));
    await waitFor(() =>
      expect(kit.state.patches).toEqual([{ kind: "letter", body: { content: "Sans le terme." } }]),
    );
    expect(await letter.findByText("Change saved. The piece is ready.")).toBeVisible();
    expect(letter.getByText("Ready")).toBeVisible();
    expect(letter.getByText("Edited by you")).toBeVisible();
    expect(letter.queryByRole("note")).toBeNull();
  });

  it("never blocks an edit while the kit runs", async () => {
    const { user, kit } = setup({
      running: true,
      sessionId: "k9",
      items: [kitItem("letter", { content: "Ancienne." })],
    });
    const letter = within(await piece("Cover letter"));
    await user.type(letter.getByLabelText("Text: Cover letter"), " Corrigée.");
    await user.click(letter.getByRole("button", { name: "Save: Cover letter" }));
    await waitFor(() => expect(kit.state.patches).toHaveLength(1));
    expect(await letter.findByText(/Change saved/)).toBeVisible();
  });

  it("shows the refusal of a save under the piece", async () => {
    const { user } = setup({
      items: [kitItem("letter")],
      patch: () =>
        HttpResponse.json(
          apiError("profile_required", "Your edit could not be checked without a validated profile."),
          { status: 409 },
        ),
    });
    const letter = within(await piece("Cover letter"));
    await user.type(letter.getByLabelText("Text: Cover letter"), "!");
    await user.click(letter.getByRole("button", { name: "Save: Cover letter" }));
    expect(await letter.findByRole("alert")).toHaveTextContent(
      "Your edit could not be checked without a validated profile.",
    );
  });

  it("copies the text of a piece to the clipboard", async () => {
    const { user } = setup({ items: [kitItem("pitch", { content: "Je suis Camille." })] });
    const pitch = within(await piece("Elevator pitch"));
    await user.click(pitch.getByRole("button", { name: "Copy: Elevator pitch" }));
    expect(await pitch.findByText("Copied to clipboard.")).toBeVisible();
    expect(await navigator.clipboard.readText()).toBe("Je suis Camille.");
  });

  it("offers the archive once a piece exists, as a download of kit.zip", async () => {
    setup({ items: [kitItem("cv")] });
    const link = await screen.findByRole("link", { name: "Download the archive" });
    expect(link).toHaveAttribute(
      "href",
      expect.stringMatching(/\/api\/v1\/applications\/a1\/kit\.zip$/),
    );
    expect(link).toHaveAttribute("download");
  });

  it("lets January cancel a running kit", async () => {
    const { user, state } = setup({ running: true, sessionId: "k9", items: [kitItem("cv")] });
    await user.click(await screen.findByRole("button", { name: "Cancel the kit" }));
    await waitFor(() => expect(state.cancels).toEqual(["k9"]));
  });

  it("says the application is gone on a 404", async () => {
    setup({}, { applications: [] });
    expect(await screen.findByText("This application no longer exists.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Back to tracking" })).toBeVisible();
    expect(screen.getByRole("heading", { level: 1, name: "Application not found" })).toBeVisible();
  });

  it("offers to retry when the kit cannot be read", async () => {
    let failures = 2;
    const { user } = setup({
      items: [kitItem("cv")],
      read: () => {
        if (failures-- <= 0) return undefined;
        return HttpResponse.json(apiError("internal_error", "Server error."), { status: 500 });
      },
    });
    await user.click(await screen.findByRole("button", { name: "Retry" }, { timeout: 5000 }));
    expect((await piece("Tailored résumé")).textContent).toContain("Ready");
  });
});
