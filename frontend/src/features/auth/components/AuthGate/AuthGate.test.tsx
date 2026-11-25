import { render, screen } from "@testing-library/react";
import { useState } from "react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { AuthGate, type GateStatus } from "./AuthGate";

function renderGate(status: GateStatus, onRetry = vi.fn(), message?: string) {
  const router = createMemoryRouter(
    [
      {
        path: "/",
        element: (
          <AuthGate status={status} message={message} onRetry={onRetry}>
            <p>Contenu protégé</p>
          </AuthGate>
        ),
      },
      { path: "/login", element: <p>Page de connexion</p> },
    ],
    { initialEntries: ["/"] },
  );
  render(<RouterProvider router={router} />);
  return { router, onRetry };
}

describe("AuthGate", () => {
  it("renders the children once open, and nothing else", () => {
    renderGate("ready");
    expect(screen.getByText("Contenu protégé")).toBeInTheDocument();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("replaces the page by /login when there is no session", () => {
    const { router } = renderGate("signedOut");
    expect(screen.getByText("Page de connexion")).toBeInTheDocument();
    expect(screen.queryByText("Contenu protégé")).toBeNull();
    // Un remplacement : « précédent » ne ramène pas à une porte qui renverrait aussitôt.
    expect(router.state.historyAction).toBe("REPLACE");
  });

  it("announces the check while loading, without the children", () => {
    renderGate("loading");
    expect(screen.getByRole("status")).toHaveTextContent("Checking your sign-in…");
    expect(screen.queryByText("Contenu protégé")).toBeNull();
  });

  it("shows the error with a retry that keeps the keyboard inside the page", async () => {
    const user = userEvent.setup();
    const { onRetry } = renderGate("error", vi.fn(), "Impossible de joindre le serveur.");
    expect(screen.getByRole("alert")).toHaveTextContent("Impossible de joindre le serveur.");
    const retry = screen.getByRole("button", { name: "Retry" });
    retry.focus();
    await user.keyboard("{Enter}");
    expect(onRetry).toHaveBeenCalledTimes(1);
    // Le conteneur reprend le focus : le bouton peut disparaître pendant la relecture.
    expect(screen.getByRole("main")).toHaveFocus();
  });

  it("hands the focus to the page content once a retry succeeds", async () => {
    const user = userEvent.setup();
    function Harness() {
      const [status, setStatus] = useState<GateStatus>("error");
      return (
        <AuthGate status={status} onRetry={() => setStatus("ready")}>
          <main id="contenu" tabIndex={-1}>
            Contenu protégé
          </main>
        </AuthGate>
      );
    }
    render(<RouterProvider router={createMemoryRouter([{ path: "/", element: <Harness /> }])} />);
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Contenu protégé")).toHaveFocus();
  });

  it("does not take the focus when the gate simply opens", () => {
    render(
      <RouterProvider
        router={createMemoryRouter([
          {
            path: "/",
            element: (
              <AuthGate status="ready" onRetry={vi.fn()}>
                <main id="contenu" tabIndex={-1}>
                  Contenu protégé
                </main>
              </AuthGate>
            ),
          },
        ])}
      />,
    );
    expect(screen.getByText("Contenu protégé")).not.toHaveFocus();
  });
});
