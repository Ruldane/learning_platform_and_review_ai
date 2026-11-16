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
    expect(button).toBeDisabled();
    expect(screen.getByLabelText("Poste visé")).toBeDisabled();
    expect(screen.getByRole("form", { name: "Lancer un relevé du marché" })).toHaveAttribute(
      "aria-busy",
      "true",
    );
    await user.click(button);
    expect(onRun).not.toHaveBeenCalled();
  });
});
