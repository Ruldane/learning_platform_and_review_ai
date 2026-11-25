import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { makeContact } from "../fixtures";
import type { ContactView } from "../viewTypes";
import { ContactList } from "./ContactList";

function many(count: number): ContactView[] {
  return Array.from({ length: count }, (_, index) => makeContact({ name: `Contact ${index + 1}` }));
}

describe("ContactList", () => {
  it("shows each contact with an editable name, role and profile address", () => {
    render(
      <ContactList
        contacts={[makeContact({ name: "Camille", role: "RH", url: "https://example.com/c" })]}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("textbox", { name: "Name, contact 1" })).toHaveValue("Camille");
    expect(screen.getByRole("textbox", { name: "Role, contact 1" })).toHaveValue("RH");
    expect(screen.getByRole("textbox", { name: "Profile URL, contact 1" })).toHaveValue(
      "https://example.com/c",
    );
  });

  it("says so when there is no contact", () => {
    render(<ContactList contacts={[]} onChange={vi.fn()} />);
    expect(screen.getByText("No contacts.")).toBeInTheDocument();
  });

  it("adds an empty contact and reports the new list", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const first = makeContact({ name: "Camille" });
    render(<ContactList contacts={[first]} onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: "Add a contact" }));
    expect(onChange).toHaveBeenCalledWith([first, { id: "", name: "", role: null, url: null }]);
  });

  it("removes a contact and reports the remaining list", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const [a, b] = many(2) as [ContactView, ContactView];
    render(<ContactList contacts={[a, b]} onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: "Remove contact Contact 1" }));
    expect(onChange).toHaveBeenCalledWith([b]);
  });

  it("reports an edit of the name, role and address", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const contact = makeContact({ name: "Cam", role: null, url: null });
    render(<ContactList contacts={[contact]} onChange={onChange} />);
    await user.type(screen.getByRole("textbox", { name: "Name, contact 1" }), "x");
    expect(onChange).toHaveBeenLastCalledWith([{ ...contact, name: "Camx" }]);
    await user.type(screen.getByRole("textbox", { name: "Role, contact 1" }), "R");
    expect(onChange).toHaveBeenLastCalledWith([{ ...contact, role: "R" }]);
  });

  it("turns a cleared role into null", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const contact = makeContact({ role: "R" });
    render(<ContactList contacts={[contact]} onChange={onChange} />);
    await user.clear(screen.getByRole("textbox", { name: "Role, contact 1" }));
    expect(onChange).toHaveBeenLastCalledWith([{ ...contact, role: null }]);
  });

  it("stops at 10 contacts: the add button is disabled and says why", () => {
    render(<ContactList contacts={many(10)} onChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Add a contact" })).toBeDisabled();
    expect(screen.getByText("10 contacts at most.")).toBeInTheDocument();
  });

  it("still allows adding at 9 contacts", () => {
    render(<ContactList contacts={many(9)} onChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Add a contact" })).toBeEnabled();
  });

  it("flags a contact with no name", () => {
    render(<ContactList contacts={[makeContact({ name: "" })]} onChange={vi.fn()} />);
    expect(screen.getByRole("textbox", { name: "Name, contact 1" })).toBeInvalid();
    expect(screen.getByText("Name is required.")).toBeInTheDocument();
  });

  it("is a named group", () => {
    render(<ContactList contacts={[]} onChange={vi.fn()} />);
    expect(screen.getByRole("group", { name: "Contacts" })).toBeInTheDocument();
  });
});
