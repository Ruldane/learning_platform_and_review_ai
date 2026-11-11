import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { KIND_COLORS } from "../kindColors";
import { mapPoint } from "../viewFixtures";
import { VectorMap } from "./VectorMap";

const svg = () =>
  screen.getByRole("group", { name: "Carte des éléments de la mémoire" }) as unknown as SVGElement;

describe("VectorMap", () => {
  it("draws one focusable point per item and opens it", async () => {
    const onOpen = vi.fn();
    const user = userEvent.setup();
    render(
      <VectorMap points={[mapPoint("i1"), mapPoint("i2")]} truncated={false} onOpen={onOpen} />,
    );
    const points = screen.getAllByRole("button", { name: /\(Acquis\)/ });
    expect(points).toHaveLength(2);
    expect(points[0]).toHaveAttribute("aria-label", "Élément i1 (Acquis)");
    points[0]!.focus();
    await user.keyboard("{Enter}");
    expect(onOpen).toHaveBeenCalledWith("i1");
    await user.click(points[1]!);
    expect(onOpen).toHaveBeenCalledWith("i2");
  });

  it("colors a point by its kind", () => {
    render(<VectorMap points={[mapPoint("i1")]} truncated={false} onOpen={vi.fn()} />);
    expect(screen.getByRole("button", { name: /Acquis/ })).toHaveAttribute(
      "fill",
      KIND_COLORS.acquis,
    );
  });

  it("starts on the whole map and zooms in and out within 1 to 8", async () => {
    const user = userEvent.setup();
    render(<VectorMap points={[mapPoint("i1")]} truncated={false} onOpen={vi.fn()} />);
    expect(svg()).toHaveAttribute("viewBox", "-1.1 -1.1 2.2 2.2");
    await user.click(screen.getByRole("button", { name: "Zoom avant" }));
    expect(svg()).toHaveAttribute("viewBox", "-0.55 -0.55 1.1 1.1");
    await user.click(screen.getByRole("button", { name: "Zoom avant" }));
    await user.click(screen.getByRole("button", { name: "Zoom avant" }));
    expect(svg()).toHaveAttribute("viewBox", "-0.1375 -0.1375 0.275 0.275");
    expect(screen.getByRole("button", { name: "Zoom avant" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Zoom arrière" }));
    expect(svg()).toHaveAttribute("viewBox", "-0.275 -0.275 0.55 0.55");
    await user.click(screen.getByRole("button", { name: "Recentrer" }));
    expect(svg()).toHaveAttribute("viewBox", "-1.1 -1.1 2.2 2.2");
    expect(screen.getByRole("button", { name: "Zoom arrière" })).toBeDisabled();
  });

  it("zooms with the mouse wheel", () => {
    render(<VectorMap points={[mapPoint("i1")]} truncated={false} onOpen={vi.fn()} />);
    fireEvent.wheel(svg(), { deltaY: -100 });
    expect(svg()).toHaveAttribute("viewBox", "-0.55 -0.55 1.1 1.1");
    fireEvent.wheel(svg(), { deltaY: 100 });
    expect(svg()).toHaveAttribute("viewBox", "-1.1 -1.1 2.2 2.2");
  });

  it("pans by dragging the background when zoomed, without opening a point", () => {
    const onOpen = vi.fn();
    render(<VectorMap points={[mapPoint("i1")]} truncated={false} onOpen={onOpen} />);
    fireEvent.wheel(svg(), { deltaY: -100 });
    vi.spyOn(svg(), "getBoundingClientRect").mockReturnValue({
      left: 0,
      top: 0,
      width: 100,
      height: 100,
      right: 100,
      bottom: 100,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    });
    fireEvent.pointerDown(svg(), { clientX: 50, clientY: 50, pointerId: 1 });
    fireEvent.pointerMove(svg(), { clientX: 40, clientY: 50, pointerId: 1 });
    fireEvent.pointerUp(svg(), { clientX: 40, clientY: 50, pointerId: 1 });
    // 10 px sur 100 px de large = 0,11 unité de carte : le centre passe de 0 à 0,11.
    expect(svg()).toHaveAttribute("viewBox", "-0.44 -0.55 1.1 1.1");
    expect(onOpen).not.toHaveBeenCalled();
  });

  it("shows the legend of the six kinds", () => {
    render(<VectorMap points={[mapPoint("i1")]} truncated={false} onOpen={vi.fn()} />);
    const legend = screen.getByRole("list", { name: "Légende des types" });
    expect(legend.querySelectorAll("li")).toHaveLength(6);
  });

  it("warns when the map is truncated", () => {
    const { rerender } = render(
      <VectorMap points={[mapPoint("i1")]} truncated={false} onOpen={vi.fn()} />,
    );
    expect(screen.queryByText(/2 000 éléments/)).not.toBeInTheDocument();
    rerender(<VectorMap points={[mapPoint("i1")]} truncated onOpen={vi.fn()} />);
    expect(
      screen.getByText("Carte limitée aux 2 000 éléments les plus récents."),
    ).toBeInTheDocument();
  });

  it("shows an empty state without points", () => {
    render(<VectorMap points={[]} truncated={false} onOpen={vi.fn()} />);
    expect(screen.getByText("La carte apparaîtra après le premier import.")).toBeInTheDocument();
    expect(screen.queryByRole("group")).not.toBeInTheDocument();
  });
});
