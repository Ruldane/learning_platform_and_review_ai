import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { PostingChoiceView } from "../viewTypes";
import { CompareTargetPicker } from "./CompareTargetPicker";

const postings: PostingChoiceView[] = [
  { id: "p1", title: "Ingénieure données", company: "Société Fictive" },
  { id: "p2", title: "Dév back", company: null },
];

function setup(props: Partial<Parameters<typeof CompareTargetPicker>[0]> = {}) {
  const onTarget = vi.fn();
  const onPosting = vi.fn();
  render(
    <CompareTargetPicker
      target="goal"
      onTarget={onTarget}
      postings={postings}
      postingId={null}
      onPosting={onPosting}
      {...props}
    />,
  );
  return { onTarget, onPosting };
}

describe("CompareTargetPicker", () => {
  it("offers the goal and a posting, the goal being checked", () => {
    setup();
    expect(screen.getByRole("radio", { name: "My target role" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "A posting" })).not.toBeChecked();
    expect(screen.queryByRole("combobox")).toBeNull();
  });

  it("switches to a posting with the keyboard", async () => {
    const { onTarget } = setup();
    screen.getByRole("radio", { name: "My target role" }).focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(onTarget).toHaveBeenCalledWith("posting");
  });

  it("lists the analysed postings and reports the choice", async () => {
    const { onPosting } = setup({ target: "posting" });
    const select = screen.getByRole("combobox", { name: "Posting" });
    expect(
      screen.getByRole("option", { name: "Ingénieure données (Société Fictive)" }),
    ).toBeVisible();
    expect(screen.getByRole("option", { name: "Dév back" })).toBeVisible();
    await userEvent.selectOptions(select, "p2");
    expect(onPosting).toHaveBeenCalledWith("p2");
    await userEvent.selectOptions(select, "");
    expect(onPosting).toHaveBeenLastCalledWith(null);
  });
});
