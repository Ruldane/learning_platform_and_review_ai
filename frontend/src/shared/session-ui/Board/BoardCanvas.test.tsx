import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import BoardCanvas from "./BoardCanvas";
import { REFIT_DELAY_MS } from "./useRefitOnShow";
import { QUIET_MS } from "./useSettled";
import { fake, fakeApi, lastSceneIds, resetExcalidrawMock } from "./excalidrawMock";

vi.mock("@excalidraw/excalidraw", async () => (await import("./excalidrawMock")).module);
vi.mock("@excalidraw/excalidraw/index.css", () => ({}));

const elements = [
  { id: "a", type: "rectangle" },
  { id: "b", type: "rectangle" },
  { id: "e", type: "arrow" },
] as never[];

function canvas(overrides: Partial<React.ComponentProps<typeof BoardCanvas>> = {}) {
  return (
    <BoardCanvas
      title="Carte du domaine"
      elements={elements}
      files={{}}
      animate
      reducedMotion={false}
      readOnly={false}
      onReady={vi.fn()}
      onSceneChange={vi.fn()}
      {...overrides}
    />
  );
}

describe("BoardCanvas", () => {
  beforeEach(() => {
    resetExcalidrawMock();
    vi.useFakeTimers();
  });
  afterEach(() => vi.useRealTimers());

  it("reveals scribe elements one by one, 200 ms apart", async () => {
    render(canvas());
    expect(fake.props?.initialData?.elements).toEqual([]);
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(lastSceneIds()).toEqual(["a"]);
    await act(() => vi.advanceTimersByTimeAsync(199));
    expect(lastSceneIds()).toEqual(["a"]);
    await act(() => vi.advanceTimersByTimeAsync(1));
    expect(lastSceneIds()).toEqual(["a", "b"]);
    await act(() => vi.advanceTimersByTimeAsync(200));
    expect(lastSceneIds()).toEqual(["a", "b", "e"]);
  });

  it("is read-only while drawing, then editable", async () => {
    render(canvas());
    expect(screen.getByTestId("excalidraw")).toHaveAttribute("data-view-mode", "true");
    await act(() => vi.advanceTimersByTimeAsync(400));
    // Tout est affiché, mais Excalidraw n'a pas fini de signaler la dernière image.
    expect(screen.getByTestId("excalidraw")).toHaveAttribute("data-view-mode", "true");
    await act(() => vi.advanceTimersByTimeAsync(250));
    expect(screen.getByTestId("excalidraw")).toHaveAttribute("data-view-mode", "false");
    expect(fakeApi.scrollToContent).toHaveBeenLastCalledWith(undefined, expect.any(Object));
  });

  it("frames the content again once the canvas has measured itself (a state already seen)", async () => {
    render(canvas({ animate: false }));
    await act(() => vi.advanceTimersByTimeAsync(0));
    const early = fakeApi.scrollToContent.mock.calls.length;
    await act(() => vi.advanceTimersByTimeAsync(REFIT_DELAY_MS));
    expect(fakeApi.scrollToContent.mock.calls.length).toBe(early + 1);
    expect(fakeApi.scrollToContent).toHaveBeenLastCalledWith(undefined, expect.any(Object));
  });

  it("shows everything at once without animation or with reduced motion", () => {
    const { unmount } = render(canvas({ animate: false }));
    expect(fake.props?.initialData?.elements).toHaveLength(3);
    unmount();
    render(canvas({ reducedMotion: true }));
    expect(fake.props?.initialData?.elements).toHaveLength(3);
    expect(fakeApi.updateScene).not.toHaveBeenCalled();
  });

  it("ignores changes while drawing and stays read-only for a read-only board", async () => {
    const onSceneChange = vi.fn();
    render(canvas({ readOnly: true, onSceneChange }));
    fake.props?.onChange?.([], {}, {});
    expect(onSceneChange).not.toHaveBeenCalled();
    await act(() => vi.advanceTimersByTimeAsync(400));
    await act(() => vi.advanceTimersByTimeAsync(250));
    expect(screen.getByTestId("excalidraw")).toHaveAttribute("data-view-mode", "true");
    fake.props?.onChange?.(elements, {}, {});
    expect(onSceneChange).toHaveBeenCalledWith(elements, false);
  });

  it("stays read-only a moment without animation, Excalidraw's changes being the reference", async () => {
    const onSceneChange = vi.fn();
    render(canvas({ animate: false, onSceneChange }));
    expect(screen.getByTestId("excalidraw")).toHaveAttribute("data-view-mode", "true");
    act(() => fake.props?.onChange?.(elements, {}, {}));
    expect(onSceneChange).toHaveBeenLastCalledWith(elements, true);
    await act(() => vi.advanceTimersByTimeAsync(QUIET_MS));
    expect(screen.getByTestId("excalidraw")).toHaveAttribute("data-view-mode", "false");
    act(() => fake.props?.onChange?.(elements, {}, {}));
    expect(onSceneChange).toHaveBeenLastCalledWith(elements, false);
  });

  it("restarts the quiet window on each change of Excalidraw, which becomes the reference", async () => {
    const onSceneChange = vi.fn();
    render(canvas({ animate: false, onSceneChange }));
    await act(() => vi.advanceTimersByTimeAsync(200));
    act(() => fake.props?.onChange?.(elements, {}, {}));
    expect(onSceneChange).toHaveBeenLastCalledWith(elements, true);
    await act(() => vi.advanceTimersByTimeAsync(QUIET_MS - 1));
    expect(screen.getByTestId("excalidraw")).toHaveAttribute("data-view-mode", "true");
    await act(() => vi.advanceTimersByTimeAsync(1));
    expect(screen.getByTestId("excalidraw")).toHaveAttribute("data-view-mode", "false");
  });

  it("passes nothing on while the elements are still appearing", async () => {
    const onSceneChange = vi.fn();
    render(canvas({ onSceneChange }));
    await act(() => vi.advanceTimersByTimeAsync(0));
    act(() => fake.props?.onChange?.([elements[0]], {}, {}));
    expect(onSceneChange).not.toHaveBeenCalled();
    await act(() => vi.advanceTimersByTimeAsync(400));
    act(() => fake.props?.onChange?.(elements, {}, {}));
    expect(onSceneChange).toHaveBeenLastCalledWith(elements, true);
  });
});
