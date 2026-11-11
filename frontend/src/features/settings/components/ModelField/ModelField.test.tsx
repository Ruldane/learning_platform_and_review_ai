import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ModelField } from "./ModelField";

describe("ModelField", () => {
  it("propose la liste quand elle existe et remonte le choix", async () => {
    const user = userEvent.setup();
    const onCommit = vi.fn();
    render(<ModelField label="Modèle" models={["a", "b"]} value="a" onCommit={onCommit} />);
    expect(screen.getByRole("combobox", { name: "Modèle" })).toHaveValue("a");
    await user.selectOptions(screen.getByRole("combobox"), "b");
    expect(onCommit).toHaveBeenCalledWith("b");
  });

  it("garde visible un modèle courant absent de la liste", () => {
    render(<ModelField label="Modèle" models={["a"]} value="ancien" onCommit={vi.fn()} />);
    expect(screen.getByRole("combobox")).toHaveValue("ancien");
  });

  it("passe en saisie libre sans liste et valide à la perte du focus", async () => {
    const user = userEvent.setup();
    const onCommit = vi.fn();
    render(<ModelField label="Modèle" models={null} value="x" onCommit={onCommit} />);
    const input = screen.getByRole("textbox", { name: "Modèle" });
    expect(input).toHaveValue("x");
    await user.type(input, "y");
    expect(onCommit).not.toHaveBeenCalled();
    await user.tab();
    expect(onCommit).toHaveBeenCalledWith("xy");
  });

  it("valide la saisie libre à Entrée", async () => {
    const user = userEvent.setup();
    const onCommit = vi.fn();
    render(<ModelField label="Modèle" models={null} value="" onCommit={onCommit} />);
    await user.type(screen.getByRole("textbox"), "glm-5.3{Enter}");
    expect(onCommit).toHaveBeenCalledTimes(1);
    expect(onCommit).toHaveBeenCalledWith("glm-5.3");
  });

  it("se désactive", () => {
    render(<ModelField label="Modèle" models={null} value="x" disabled onCommit={vi.fn()} />);
    expect(screen.getByRole("textbox")).toBeDisabled();
  });
});
