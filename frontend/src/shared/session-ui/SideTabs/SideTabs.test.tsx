import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { SideTabs } from "./SideTabs";

const TABS = [
  { id: "a", label: "Premier" },
  { id: "b", label: "Deuxième" },
  { id: "c", label: "Troisième" },
];

function Harness({ initial = "a" }: { initial?: string }) {
  const [active, setActive] = useState(initial);
  return (
    <SideTabs
      label="Espaces"
      tabs={TABS}
      active={active}
      onChange={setActive}
      panels={{ a: <p>Contenu A</p>, b: <p>Contenu B</p>, c: <p>Contenu C</p> }}
    />
  );
}

describe("SideTabs", () => {
  it("is a named tablist whose tabs control their panels", () => {
    render(<Harness />);
    expect(screen.getByRole("tablist", { name: "Espaces" })).toBeInTheDocument();
    const tab = screen.getByRole("tab", { name: "Premier" });
    const panel = screen.getByRole("tabpanel", { name: "Premier" });
    expect(tab).toHaveAttribute("aria-selected", "true");
    expect(tab).toHaveAttribute("aria-controls", panel.id);
    expect(screen.getByRole("tab", { name: "Deuxième" })).toHaveAttribute("tabindex", "-1");
  });

  it("mounts a panel when first shown and keeps it mounted, hidden", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    expect(screen.queryByText("Contenu B")).toBeNull();
    await user.click(screen.getByRole("tab", { name: "Deuxième" }));
    expect(screen.getByText("Contenu B")).toBeVisible();
    expect(screen.getByText("Contenu A")).not.toBeVisible();
    expect(screen.queryByText("Contenu C")).toBeNull();
  });

  it("moves with the arrow keys, Home and End, and the focus follows", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    screen.getByRole("tab", { name: "Premier" }).focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Deuxième" })).toHaveFocus();
    expect(screen.getByRole("tab", { name: "Deuxième" })).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{ArrowLeft}{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "Troisième" })).toHaveFocus();
    await user.keyboard("{Home}");
    expect(screen.getByRole("tab", { name: "Premier" })).toHaveFocus();
    await user.keyboard("{End}");
    expect(screen.getByRole("tab", { name: "Troisième" })).toHaveFocus();
  });
});
