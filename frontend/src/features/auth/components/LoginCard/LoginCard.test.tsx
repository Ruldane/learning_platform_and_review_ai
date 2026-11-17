import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LoginCard } from "./LoginCard";

describe("LoginCard", () => {
  it("offers a plain link to Google, reachable by keyboard", () => {
    render(<LoginCard href="http://localhost:8000/api/v1/auth/google/login" />);
    const link = screen.getByRole("link", { name: "Se connecter avec Google" });
    expect(link).toHaveAttribute("href", "http://localhost:8000/api/v1/auth/google/login");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("announces why the last attempt failed", () => {
    render(<LoginCard href="/x" errorMessage="Connexion annulée." />);
    expect(screen.getByRole("alert")).toHaveTextContent("Connexion annulée.");
  });
});
