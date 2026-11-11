import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ProviderOrderEditor } from "./ProviderOrderEditor";

describe("ProviderOrderEditor", () => {
  it("liste les fournisseurs dans l'ordre", () => {
    render(<ProviderOrderEditor value={["searxng", "brave"]} braveAvailable onChange={vi.fn()} />);
    const items = screen.getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("SearXNG");
    expect(items[1]).toHaveTextContent("Brave");
  });

  it("monte Brave en premier", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ProviderOrderEditor value={["searxng", "brave"]} braveAvailable onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: "Monter Brave" }));
    expect(onChange).toHaveBeenCalledWith(["brave", "searxng"]);
  });

  it("descend SearXNG", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ProviderOrderEditor value={["searxng", "brave"]} braveAvailable onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: "Descendre SearXNG" }));
    expect(onChange).toHaveBeenCalledWith(["brave", "searxng"]);
  });

  it("désactive monter sur le premier et descendre sur le dernier", () => {
    render(<ProviderOrderEditor value={["searxng", "brave"]} braveAvailable onChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Monter SearXNG" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Descendre Brave" })).toBeDisabled();
  });

  it("grise Brave sans clé, avec la consigne, et fige l'ordre", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <ProviderOrderEditor
        value={["searxng", "brave"]}
        braveAvailable={false}
        onChange={onChange}
      />,
    );
    const brave = screen.getAllByRole("listitem")[1] as HTMLElement;
    expect(brave).toHaveAttribute("aria-disabled", "true");
    expect(
      within(brave).getByText("Ajoutez une clé Brave dans Modèles et clés"),
    ).toBeInTheDocument();
    for (const button of screen.getAllByRole("button")) expect(button).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Monter Brave" }));
    expect(onChange).not.toHaveBeenCalled();
  });

  it("n'affiche pas la consigne quand Brave a une clé", () => {
    render(<ProviderOrderEditor value={["brave"]} braveAvailable onChange={vi.fn()} />);
    expect(screen.queryByText(/Ajoutez une clé Brave/)).not.toBeInTheDocument();
  });
});
