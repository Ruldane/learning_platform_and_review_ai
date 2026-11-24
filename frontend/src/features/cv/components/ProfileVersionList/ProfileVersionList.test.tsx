import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ProfileVersionView } from "../viewTypes";
import { ProfileVersionList } from "./ProfileVersionList";

const versions: ProfileVersionView[] = [
  { version: 1, status: "validated", source: "archivist", createdAt: "2026-11-03T12:00:00Z" },
  { version: 3, status: "draft", source: "archivist", createdAt: "2026-11-12T12:00:00Z" },
  { version: 2, status: "validated", source: "january", createdAt: "2026-11-05T12:00:00Z" },
];

describe("ProfileVersionList", () => {
  it("lists the newest first, with state, origin and day", () => {
    render(<ProfileVersionList versions={versions} />);
    const items = screen.getAllByRole("listitem").map((item) => item.textContent);
    expect(items).toEqual([
      "Version 3DraftRead from your documentsCreated on 12/11/2026",
      "Version 2ValidatedCurrentEdited by youCreated on 05/11/2026",
      "Version 1ValidatedRead from your documentsCreated on 03/11/2026",
    ]);
  });

  it("flags only the latest validated version", () => {
    render(<ProfileVersionList versions={versions} />);
    expect(screen.getAllByText("Current")).toHaveLength(1);
  });

  it("says when there is no version", () => {
    render(<ProfileVersionList versions={[]} />);
    expect(screen.getByText("No versions yet.")).toBeInTheDocument();
  });
});
