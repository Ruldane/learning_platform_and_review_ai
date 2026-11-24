import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ExerciseForm } from "./ExerciseForm";

function setup(over: Partial<Parameters<typeof ExerciseForm>[0]> = {}) {
  const calls = { onCreate: vi.fn().mockResolvedValue(true), onGenerate: vi.fn() };
  render(
    <ExerciseForm
      creating={false}
      generating={false}
      notice={null}
      error={null}
      {...calls}
      {...over}
    />,
  );
  return { ...calls, user: userEvent.setup() };
}

describe("ExerciseForm", () => {
  it("creates and generates", async () => {
    const { user, onCreate, onGenerate } = setup();
    expect(screen.getByRole("button", { name: "Add exercise" })).toBeDisabled();
    await user.type(screen.getByRole("textbox", { name: "Title" }), "Additionner");
    await user.type(screen.getByRole("textbox", { name: "Prompt" }), "Écris add.");
    await user.type(screen.getByRole("textbox", { name: /Starter code/ }), "x = 1");
    await user.type(screen.getByRole("textbox", { name: /Tests/ }), "def test_a(): pass");
    await user.click(screen.getByRole("button", { name: "Add exercise" }));
    expect(onCreate).toHaveBeenCalledWith({
      title: "Additionner",
      statement: "Écris add.",
      starter: "x = 1",
      tests: "def test_a(): pass",
    });
    // Ajouté : les champs sont vidés.
    expect(await screen.findByRole("textbox", { name: "Title" })).toHaveValue("");

    await user.type(screen.getByRole("textbox", { name: "Topic" }), "les dictionnaires");
    await user.selectOptions(screen.getByRole("combobox", { name: "Level" }), "advanced");
    await user.click(screen.getByRole("button", { name: "Generate" }));
    expect(onGenerate).toHaveBeenCalledWith({ topic: "les dictionnaires", level: "advanced" });
  });

  it("keeps what was typed when the exercise is refused", async () => {
    const { user } = setup({ onCreate: vi.fn().mockResolvedValue(false) });
    await user.type(screen.getByRole("textbox", { name: "Title" }), "Additionner");
    await user.type(screen.getByRole("textbox", { name: "Prompt" }), "Écris add.");
    await user.click(screen.getByRole("button", { name: "Add exercise" }));
    expect(screen.getByRole("textbox", { name: "Title" })).toHaveValue("Additionner");
  });

  it("announces the notice and the server error", () => {
    setup({ notice: "Exercise added.", error: "Le titre est trop long." });
    expect(screen.getByRole("status")).toHaveTextContent("Exercise added.");
    expect(screen.getByRole("alert")).toHaveTextContent("Le titre est trop long.");
  });

  it("will not generate without a topic", () => {
    setup();
    expect(screen.getByRole("button", { name: "Generate" })).toBeDisabled();
  });
});
