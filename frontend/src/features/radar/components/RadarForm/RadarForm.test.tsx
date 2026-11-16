import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RadarForm } from "./RadarForm";

describe("RadarForm", () => {
  it("starts from the proposed role and zone and launches with them", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<RadarForm role="Data engineer" zone="France" onRun={onRun} running={false} />);
    expect(screen.getByLabelText("Poste visé")).toHaveValue("Data engineer");
    expect(screen.getByLabelText("Zone")).toHaveValue("France");
    await user.click(screen.getByRole("button", { name: "Lancer un relevé" }));
    expect(onRun).toHaveBeenCalledWith({ role: "Data engineer", zone: "France" });
  });

  it("trims what is typed and leaves an empty zone to the server's default", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<RadarForm role="" zone="France" onRun={onRun} running={false} />);
    await user.type(screen.getByLabelText("Poste visé"), "  Analyste données ");
    await user.clear(screen.getByLabelText("Zone"));
    await user.keyboard("{Enter}");
    expect(onRun).toHaveBeenCalledWith({ role: "Analyste données", zone: null });
  });

  it("refuses an empty role with a field error and sends nothing", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<RadarForm role="   " zone="France" onRun={onRun} running={false} />);
    await user.click(screen.getByRole("button", { name: "Lancer un relevé" }));
    expect(onRun).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("Indique le poste visé.");
    expect(screen.getByLabelText("Poste visé")).toBeInvalid();
  });

  it("waits for the running run: fields and button are disabled and the form is busy", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<RadarForm role="Data engineer" zone="France" onRun={onRun} running />);
    const button = screen.getByRole("button", { name: "Relevé en cours…" });
    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByLabelText("Poste visé")).toHaveAttribute("readonly");
    expect(screen.getByRole("form", { name: "Lancer un relevé du marché" })).toHaveAttribute(
      "aria-busy",
      "true",
    );
    await user.click(button);
    expect(onRun).not.toHaveBeenCalled();
  });

  it("refuses a one-character role with a field error and sends nothing", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<RadarForm role="D" zone="France" onRun={onRun} running={false} />);
    await user.click(screen.getByRole("button", { name: "Lancer un relevé" }));
    expect(onRun).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Le poste doit faire au moins 2 caractères.",
    );
    expect(screen.getByLabelText("Poste visé")).toBeInvalid();
  });

  it("refuses a one-character zone, clears the error once corrected, and accepts 2 characters", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<RadarForm role="Data engineer" zone="F" onRun={onRun} running={false} />);
    await user.click(screen.getByRole("button", { name: "Lancer un relevé" }));
    expect(onRun).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("La zone doit faire au moins 2 caractères");
    expect(screen.getByLabelText("Zone")).toBeInvalid();
    await user.type(screen.getByLabelText("Zone"), "R");
    expect(screen.queryByRole("alert")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Lancer un relevé" }));
    expect(onRun).toHaveBeenCalledWith({ role: "Data engineer", zone: "FR" });
  });

  it("counts the length after trimming: two spaces and a letter are one character", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<RadarForm role="  D " zone="" onRun={onRun} running={false} />);
    await user.click(screen.getByRole("button", { name: "Lancer un relevé" }));
    expect(onRun).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Poste visé")).toBeInvalid();
  });

  it("shows the server's refusal on the field it names", () => {
    render(
      <RadarForm
        role=""
        zone="France"
        onRun={vi.fn()}
        running={false}
        roleError="Indique le poste visé pour lancer un relevé."
        zoneError="Cette zone n'est pas acceptée."
      />,
    );
    expect(screen.getByLabelText("Poste visé")).toBeInvalid();
    expect(screen.getByLabelText("Poste visé")).toHaveAccessibleDescription(
      "Indique le poste visé pour lancer un relevé.",
    );
    expect(screen.getByLabelText("Zone")).toHaveAccessibleDescription(
      "Cette zone n'est pas acceptée.",
    );
  });
});
