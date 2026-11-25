import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { authApi, authRequired, camille, errorBody, localMe } from "@/test/authApi";
import { server } from "@/test/server";
import { renderAuth } from "../../authTestkit";

const MESSAGES: [string, string][] = [
  ["access_denied", "Sign-in cancelled."],
  ["state_invalid", "The sign-in expired, start again."],
  ["email_not_allowed", "This account isn't allowed on this instance."],
  ["email_unverified", "Google address not verified."],
  ["google_unavailable", "Google isn't responding, try again in a moment."],
  ["token_invalid", "Google's response was rejected."],
  ["claim_expired", "The takeover choice expired, sign in again."],
  ["local_already_claimed", "This computer's data has already been taken over by an account."],
];

describe("LoginPage", () => {
  it.each(MESSAGES)("login error messages by code: %s", async (code, message) => {
    server.use(...authApi({ me: null }).handlers);
    renderAuth(`/login?error=${code}`);
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });

  it("shows a callback error passed with the previous query key", async () => {
    server.use(...authApi({ me: null }).handlers);
    renderAuth("/login?erreur=access_denied");
    expect(await screen.findByRole("alert")).toHaveTextContent("Sign-in cancelled.");
  });

  it("login error messages by code: an unknown code gets the general message, never shown", async () => {
    server.use(...authApi({ me: null }).handlers);
    renderAuth("/login?error=%3Cb%3Ecode_inventé%3C%2Fb%3E");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Sign-in failed, try again.");
    expect(alert).not.toHaveTextContent("inventé");
  });

  it("login error messages by code: no code, no message; inherited keys are unknown", async () => {
    server.use(...authApi({ me: null }).handlers);
    renderAuth("/login?error=constructor");
    expect(await screen.findByRole("alert")).toHaveTextContent("Sign-in failed");
  });

  it("shows the Google link and no alert without an error code", async () => {
    server.use(...authApi({ me: null }).handlers);
    renderAuth("/login");
    const link = await screen.findByRole("link", { name: "Sign in with Google" });
    expect(link).toHaveAttribute("href", "http://localhost:8000/api/v1/auth/google/login");
    expect(screen.queryByRole("alert")).toBeNull();
    await waitFor(() =>
      expect(screen.getByRole("heading", { level: 1, name: "Sign in" })).toHaveFocus(),
    );
  });

  it("sends the local mode back to the app", async () => {
    server.use(...authApi({ me: localMe }).handlers);
    renderAuth("/login");
    expect(await screen.findByText("Chemin : /")).toBeInTheDocument();
  });

  it("does not bounce a Google account back to the gate: it keeps showing the card", async () => {
    server.use(...authApi({ me: camille }).handlers);
    const { visited } = renderAuth("/login");
    expect(
      await screen.findByRole("link", { name: "Sign in with Google" }),
    ).toBeInTheDocument();
    expect(visited).toEqual(["/login"]);
  });

  it("offers a retry when the server cannot say which mode it runs", async () => {
    server.use(...authApi({ me: camille, meFails: true }).handlers);
    renderAuth("/login");
    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("gives the title the focus once a retry succeeds", async () => {
    let calls = 0;
    server.use(
      http.get(`${apiBaseUrl}/api/v1/auth/me`, () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json(errorBody("boom"), { status: 500 })
          : HttpResponse.json(authRequired, { status: 401 });
      }),
    );
    const { user } = renderAuth("/login");
    const retry = await screen.findByRole("button", { name: "Retry" });
    await user.click(retry);
    const title = await screen.findByRole("heading", { name: "Sign in" });
    await screen.findByRole("link", { name: "Sign in with Google" });
    expect(title).toHaveFocus();
  });
});
