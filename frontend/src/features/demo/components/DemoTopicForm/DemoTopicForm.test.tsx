import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DemoTopicForm } from "./DemoTopicForm";

describe("DemoTopicForm", () => {
  it("envoie le sujet sans espaces autour", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<DemoTopicForm pending={false} error={null} onSubmit={onSubmit} />);
    await user.type(screen.getByLabelText("Sujet"), "  apprendre Rust ");
    await user.click(screen.getByRole("button", { name: "Lancer le débat" }));
    expect(onSubmit).toHaveBeenCalledWith("apprendre Rust");
  });

  it("n'envoie pas un sujet trop court (le serveur exige 3 caractères)", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<DemoTopicForm pending={false} error={null} onSubmit={onSubmit} />);
    await user.type(screen.getByLabelText("Sujet"), "ab ");
    expect(screen.getByRole("button", { name: "Lancer le débat" })).toBeDisabled();
    await user.keyboard("{Enter}");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("désactive le bouton pendant le lancement", () => {
    render(<DemoTopicForm pending error={null} onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Lancement…" })).toBeDisabled();
  });

  it("affiche l'erreur de lancement", () => {
    render(<DemoTopicForm pending={false} error="Serveur injoignable" onSubmit={vi.fn()} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Serveur injoignable");
  });
});
