import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ConfirmationView } from "../viewTypes";
import { ConfirmationCard } from "./ConfirmationCard";

const field = (id: string, label: string, value: string, required = false) => ({
  id,
  label,
  required,
  maxLength: 200,
  value,
});

const CONFIRMATION: ConfirmationView = {
  question: "Create this application ?",
  fields: [
    field("company", "Company", "Acme", true),
    field("title", "Role", "Data engineer", true),
    field("status", "Status", "applied", true),
    field("applied_on", "Application date (YYYY-MM-DD)", ""),
    field("channel", "Channel", "linkedin"),
    field("contact_name", "Contact", ""),
    field("contact_role", "Contact role", ""),
    field("notes", "Notes", ""),
  ],
  options: [
    { value: "create", label: "Create application" },
    { value: "cancel", label: "Cancel" },
  ],
};

function setup(confirmation = CONFIRMATION, disabled = false) {
  const onChoose = vi.fn();
  render(<ConfirmationCard confirmation={confirmation} disabled={disabled} onChoose={onChoose} />);
  return onChoose;
}

describe("ConfirmationCard", () => {
  it("shows the question and the fields the assistant read, already filled", () => {
    setup();
    expect(screen.getByText("Create this application ?")).toBeInTheDocument();
    expect(screen.getByLabelText("Company")).toHaveValue("Acme");
    expect(screen.getByLabelText("Role")).toHaveValue("Data engineer");
  });

  it("shows readable status and channel labels", () => {
    setup();
    expect(screen.getByLabelText("Status")).toHaveDisplayValue("Applied");
    expect(screen.getByLabelText("Channel")).toHaveDisplayValue("LinkedIn");
  });

  it("says an empty date means today", () => {
    setup();
    expect(screen.getByLabelText("Application date (YYYY-MM-DD)")).toHaveAccessibleDescription(
      "Without a date, the application uses today's date.",
    );
  });

  it("sends the choice with the fields as January leaves them", async () => {
    const user = userEvent.setup();
    const onChoose = setup();
    const company = screen.getByLabelText("Company");
    await user.clear(company);
    await user.type(company, "Acme Corp");
    await user.selectOptions(screen.getByLabelText("Status"), "interview");
    await user.click(screen.getByRole("button", { name: "Create application" }));
    expect(onChoose).toHaveBeenCalledWith(
      "create",
      expect.objectContaining({
        company: "Acme Corp",
        status: "interview",
        title: "Data engineer",
      }),
    );
  });

  it("refuses to create while a required field is empty, but never blocks cancel", async () => {
    const user = userEvent.setup();
    const onChoose = setup();
    await user.clear(screen.getByLabelText("Role"));
    expect(screen.getByRole("button", { name: "Create application" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onChoose).toHaveBeenCalledWith("cancel", {});
  });

  it("offers only the choices of the server", () => {
    setup({
      ...CONFIRMATION,
      options: [
        { value: "distinct", label: "It's a different role" },
        { value: "open", label: "Open the existing application" },
        { value: "cancel", label: "Cancel" },
      ],
    });
    expect(screen.queryByRole("button", { name: "Create application" })).toBeNull();
    expect(screen.getByRole("button", { name: "It's a different role" })).toBeEnabled();
  });

  it("sends edits for a different role and opens the existing application", async () => {
    const user = userEvent.setup();
    const onChoose = setup({
      ...CONFIRMATION,
      options: [
        { value: "distinct", label: "It's a different role" },
        { value: "open", label: "Open the existing application" },
      ],
    });
    await user.click(screen.getByRole("button", { name: "Open the existing application" }));
    await user.click(screen.getByRole("button", { name: "It's a different role" }));
    expect(onChoose).toHaveBeenNthCalledWith(1, "open", {});
    expect(onChoose).toHaveBeenNthCalledWith(
      2,
      "distinct",
      expect.objectContaining({ company: "Acme" }),
    );
  });

  it("disables everything when it is answered", () => {
    setup(CONFIRMATION, true);
    expect(screen.getByLabelText("Company")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
  });

  it("refuses a contact role without a contact name, and says why", async () => {
    const user = userEvent.setup();
    const onChoose = setup();
    await user.type(screen.getByLabelText("Contact role"), "Responsable data");
    expect(screen.getByLabelText("Contact")).toBeInvalid();
    expect(
      screen.getByText("Give the contact's name, otherwise their role is lost."),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Create application" })).toBeDisabled();
    await user.type(screen.getByLabelText("Contact"), "Camille");
    expect(screen.getByRole("button", { name: "Create application" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Create application" }));
    expect(onChoose).toHaveBeenCalledTimes(1);
  });

  it("does not let a future date be picked", () => {
    setup();
    const max = screen.getByLabelText("Application date (YYYY-MM-DD)").getAttribute("max");
    expect(max).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("shows why the question is asked again", () => {
    setup({ ...CONFIRMATION, reason: "The date can't be in the future." });
    expect(screen.getByRole("alert")).toHaveTextContent("The date can't be in the future.");
  });
});
