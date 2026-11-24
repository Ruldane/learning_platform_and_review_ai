import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { apiError } from "@/test/councilHarness";
import { postingsApi } from "@/test/postingsApi";
import { renderPosting } from "@/test/postingsHarness";
import { PostingPage } from "./PostingPage";

function setup(api: Parameters<typeof postingsApi>[0] = {}) {
  return renderPosting((createSocket) => <PostingPage createSocket={createSocket} />, api);
}

const alert = (over: Record<string, unknown> = {}) => ({
  application_id: "ap9",
  level: "probable",
  message: "You already have an application at Société Fictive for this role.",
  company: "Société Fictive",
  title: "Ingénieure données (H/F)",
  status: "applied",
  applied_on: "2026-11-03",
  created_on: "2026-11-03",
  ...over,
});

const check =
  (over: Record<string, unknown> = {}) =>
  () =>
    HttpResponse.json({ own: null, alerts: [], info: [], ...over });

const block = () => screen.findByRole("region", { name: "Application for this posting" });
const CREATE = "Create the application";

describe("PostingPage applications", () => {
  beforeEach(() => useSessionStore.getState().reset("a1"));

  it("checks the posting and offers to create the application when there is none", async () => {
    const { user, state, router } = setup();
    const section = within(await block());
    expect(state.checks).toEqual(["?posting_id=p1"]);
    expect(section.queryByRole("alert")).toBeNull();
    await user.click(section.getByRole("button", { name: CREATE }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/candidatures/ap1"));
    expect(state.applications).toEqual([{ posting_id: "p1", status: "to_apply" }]);
  });

  it("shows the application the posting already has and opens it", async () => {
    const { user, router } = setup({
      check: check({
        own: {
          id: "ap2",
          company: "Société Fictive",
          title: "Ingénieure données",
          status: "applied",
          applied_on: "2026-11-03",
        },
      }),
    });
    const section = within(await block());
    expect(
      section.getByText(/You already have an application for this posting: Société Fictive/),
    ).toBeVisible();
    expect(section.getByText(/Ingénieure données \(Applied\)/)).toBeVisible();
    expect(section.queryByRole("button", { name: CREATE })).toBeNull();
    await user.click(section.getByRole("button", { name: "Open the application" }));
    expect(router.state.location.pathname).toBe("/candidatures/ap2");
  });

  it("shows the duplicate alert of the check, with its three choices and no create button", async () => {
    const { user, router } = setup({ check: check({ alerts: [alert()] }) });
    const section = within(await block());
    expect(section.getByRole("alert")).toHaveTextContent("Likely duplicate");
    expect(section.getByText(/You already have an application at Société Fictive/)).toBeVisible();
    expect(section.queryByRole("button", { name: CREATE })).toBeNull();
    await user.click(section.getByRole("button", { name: "Open the existing application" }));
    expect(router.state.location.pathname).toBe("/candidatures/ap9");
  });

  it("creates the application when confirmed as a different role", async () => {
    const { user, state, router } = setup({ check: check({ alerts: [alert()] }) });
    await user.click(await screen.findByRole("button", { name: "It's a different role" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/candidatures/ap1"));
    expect(state.applications).toEqual([
      { posting_id: "p1", status: "to_apply", distinct_from: ["ap9"] },
    ]);
  });

  it("brings back the create button when the alert is cancelled, and the alert again if the server insists", async () => {
    const { user, state } = setup({
      check: check({ alerts: [alert()] }),
      application: () =>
        HttpResponse.json(
          apiError("application_duplicate", "Application already exists.", { alerts: [alert()] }),
          { status: 409 },
        ),
    });
    await user.click(await screen.findByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("alert")).toBeNull();
    await user.click(screen.getByRole("button", { name: CREATE }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Likely duplicate");
    expect(state.applications).toHaveLength(1);
  });

  it("only notes a same-company info and still offers to create", async () => {
    setup({
      check: check({
        info: [
          alert({
            level: "info",
            message: "You applied at Société Fictive 12 days ago.",
          }),
        ],
      }),
    });
    const section = within(await block());
    expect(section.getByRole("note")).toHaveTextContent("You applied at Société Fictive");
    expect(section.queryByRole("alert")).toBeNull();
    expect(section.getByRole("button", { name: CREATE })).toBeEnabled();
  });

  it("opens the application the posting already has when the server says it exists (409)", async () => {
    const { user, router } = setup({
      application: () =>
        HttpResponse.json(
          apiError("application_exists", "This posting already has an application.", {
            application_id: "ap5",
          }),
          { status: 409 },
        ),
    });
    await user.click(await screen.findByRole("button", { name: CREATE }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/candidatures/ap5"));
  });

  it("says why the creation failed and keeps the button", async () => {
    const { user } = setup({
      application: () =>
        HttpResponse.json(apiError("internal_error", "The server is not responding."), {
          status: 500,
        }),
    });
    await user.click(await screen.findByRole("button", { name: CREATE }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The server is not responding.");
    expect(screen.getByRole("button", { name: CREATE })).toBeEnabled();
  });

  it("says when the check fails, with a retry", async () => {
    let calls = 0;
    const { user } = setup({
      check: () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json(apiError("internal_error", "Unavailable."), { status: 500 })
          : HttpResponse.json({ own: null, alerts: [], info: [] });
      },
    });
    expect(
      await screen.findByText("The search for an existing application failed. Unavailable."),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("button", { name: CREATE })).toBeVisible();
  });
});
