import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RadarForm } from "./RadarForm";

describe("RadarForm", () => {
  it("starts from the proposed role and zone and launches with them", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<RadarForm role="Data engineer" zone="France" onRun={onRun} running={false} />);
    expect(screen.getByLabelText("Target role")).toHaveValue("Data engineer");
    expect(screen.getByLabelText("Area")).toHaveValue("France");
    await user.click(screen.getByRole("button", { name: "Run a scan" }));
    expect(onRun).toHaveBeenCalledWith({ role: "Data engineer", zone: "France" });
  });

  it("trims what is typed and leaves an empty zone to the server's default", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<RadarForm role="" zone="France" onRun={onRun} running={false} />);
    await user.type(screen.getByLabelText("Target role"), "  Analyste données ");
    await user.clear(screen.getByLabelText("Area"));
    await user.keyboard("{Enter}");
    expect(onRun).toHaveBeenCalledWith({ role: "Analyste données", zone: null });
  });

  it("refuses an empty role with a field error and sends nothing", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<RadarForm role="   " zone="France" onRun={onRun} running={false} />);
    await user.click(screen.getByRole("button", { name: "Run a scan" }));
    expect(onRun).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("Enter the target role.");
    expect(screen.getByLabelText("Target role")).toBeInvalid();
  });

  it("waits for the running run: fields and button are disabled and the form is busy", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<RadarForm role="Data engineer" zone="France" onRun={onRun} running />);
    const button = screen.getByRole("button", { name: "Scan in progress…" });
    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByLabelText("Target role")).toHaveAttribute("readonly");
    expect(screen.getByRole("form", { name: "Run a market scan" })).toHaveAttribute(
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
    await user.click(screen.getByRole("button", { name: "Run a scan" }));
    expect(onRun).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "The role must be at least 2 characters.",
    );
    expect(screen.getByLabelText("Target role")).toBeInvalid();
  });

  it("refuses a one-character zone, clears the error once corrected, and accepts 2 characters", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<RadarForm role="Data engineer" zone="F" onRun={onRun} running={false} />);
    await user.click(screen.getByRole("button", { name: "Run a scan" }));
    expect(onRun).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("The area must be at least 2 characters");
    expect(screen.getByLabelText("Area")).toBeInvalid();
    await user.type(screen.getByLabelText("Area"), "R");
    expect(screen.queryByRole("alert")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Run a scan" }));
    expect(onRun).toHaveBeenCalledWith({ role: "Data engineer", zone: "FR" });
  });

  it("counts the length after trimming: two spaces and a letter are one character", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<RadarForm role="  D " zone="" onRun={onRun} running={false} />);
    await user.click(screen.getByRole("button", { name: "Run a scan" }));
    expect(onRun).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Target role")).toBeInvalid();
  });

  it("shows the server's refusal on the field it names", () => {
    render(
      <RadarForm
        role=""
        zone="France"
        onRun={vi.fn()}
        running={false}
        roleError="Enter the target role to run a scan."
        zoneError="The area is invalid."
      />,
    );
    expect(screen.getByLabelText("Target role")).toBeInvalid();
    expect(screen.getByLabelText("Target role")).toHaveAccessibleDescription(
      "Enter the target role to run a scan.",
    );
    expect(screen.getByLabelText("Area")).toHaveAccessibleDescription("The area is invalid.");
  });
});
