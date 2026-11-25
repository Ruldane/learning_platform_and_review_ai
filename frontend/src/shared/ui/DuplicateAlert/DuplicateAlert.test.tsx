import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DuplicateAlert } from "./DuplicateAlert";
import type { DuplicateAlertView } from "./DuplicateAlert";

const CERTAIN: DuplicateAlertView = {
  level: "certain",
  applicationId: "a1",
  company: "Acme",
  title: "Data engineer",
  status: "applied",
  message: "You already applied for the Data engineer role at Acme on 3 November (Applied).",
};
const PROBABLE: DuplicateAlertView = {
  level: "probable",
  applicationId: "a2",
  company: "Acme",
  title: "Data engineer (H/F)",
  status: "to_apply",
  message: "You already have an application for the Data engineer (H/F) role at Acme (To apply).",
};
const INFO: DuplicateAlertView = {
  level: "info",
  applicationId: "a3",
  company: "Acme",
  title: "Analyste",
  status: "applied",
  message: "For reference, you applied for the Analyste role at Acme 12 days ago.",
};

function setup(alerts: DuplicateAlertView[]) {
  const handlers = { onOpen: vi.fn(), onDistinct: vi.fn(), onCancel: vi.fn() };
  render(<DuplicateAlert alerts={alerts} {...handlers} />);
  return handlers;
}

describe("DuplicateAlert", () => {
  it("shows the server message of the strongest alert, whatever the order", () => {
    setup([PROBABLE, CERTAIN]);
    const alert = screen.getByRole("alert");
    expect(within(alert).getByText(CERTAIN.message)).toBeInTheDocument();
  });

  it("says the level in words, not only with a colour", () => {
    setup([CERTAIN]);
    expect(screen.getByText("Certain duplicate")).toBeInTheDocument();
  });

  it.each([
    ["certain", "Certain duplicate"],
    ["probable", "Likely duplicate"],
    ["possible", "Possible duplicate"],
    ["info", "For info"],
  ] as const)("says the level in words for %s", (level, words) => {
    setup([{ ...PROBABLE, level }]);
    expect(screen.getByText(words)).toBeInTheDocument();
  });

  it("lists the other alerts with their level in words", () => {
    setup([CERTAIN, PROBABLE, INFO]);
    const others = screen.getByRole("list", { name: "Other similar applications" });
    const items = within(others).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Acme, Data engineer (H/F) (To apply): Likely duplicate");
    expect(items[1]).toHaveTextContent("Acme, Analyste (Applied): For info");
  });

  it("offers the three choices of the spec and each calls its handler", async () => {
    const user = userEvent.setup();
    const handlers = setup([PROBABLE, CERTAIN]);
    await user.click(screen.getByRole("button", { name: "Open the existing application" }));
    await user.click(screen.getByRole("button", { name: "It's a different role" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(handlers.onOpen).toHaveBeenCalledWith("a1");
    expect(handlers.onDistinct).toHaveBeenCalledTimes(1);
    expect(handlers.onCancel).toHaveBeenCalledTimes(1);
  });

  it("renders an info alert as a simple note, with no choice", () => {
    setup([INFO]);
    expect(screen.getByRole("note")).toHaveTextContent(INFO.message);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("renders nothing when there is no alert", () => {
    const { container } = render(
      <DuplicateAlert alerts={[]} onOpen={vi.fn()} onDistinct={vi.fn()} onCancel={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
