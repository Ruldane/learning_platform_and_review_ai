import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { MasterProfileView, ProfileSaveErrorView } from "../viewTypes";
import { MasterProfileForm } from "./MasterProfileForm";

const PROFILE: MasterProfileView = {
  identity: {
    name: "Camille Exemple",
    email: "camille.exemple@example.org",
    phone: "+33 6 00 00 00 00",
    location: "Lyon",
    headline: null,
  },
  title: { id: "t1", text: "Développeuse front" },
  summary: null,
  experiences: [
    {
      id: "x1",
      role: "Développeuse",
      company: "Société Fictive",
      location: null,
      start: "2021-03",
      end: null,
      achievements: [{ id: "x1a1", text: "Refonte du tableau de bord" }],
      sources: ["cv", "linkedin"],
    },
  ],
  education: [],
  skills: [
    { id: "c1", name: "React", category: "Front", sources: ["cv"] },
    { id: "c2", name: "SQL", category: null, sources: ["note"] },
    { id: "c3", name: "Git", category: null, sources: ["cv"] },
  ],
  projects: [],
  languages: [{ id: "l1", name: "Français", level: "Natif", sources: ["cv"] }],
  links: [],
};

interface Props {
  profile?: MasterProfileView;
  dropped?: string[];
  saving?: boolean;
  error?: ProfileSaveErrorView | null;
}

function setup(props: Props = {}) {
  const onSave = vi.fn();
  const ui = (next: Props) => (
    <MasterProfileForm
      profile={next.profile ?? PROFILE}
      dropped={next.dropped ?? []}
      saving={next.saving ?? false}
      error={next.error ?? null}
      onSave={onSave}
    />
  );
  const view = render(ui(props));
  return { onSave, rerender: (next: Props) => view.rerender(ui(next)) };
}

const open = (name: string) => userEvent.click(screen.getByRole("button", { name }));
const save = () => userEvent.click(screen.getByRole("button", { name: "Validate my profile" }));
const saved = (onSave: ReturnType<typeof vi.fn>): MasterProfileView =>
  onSave.mock.calls[0]?.[0] as MasterProfileView;

describe("MasterProfileForm", () => {
  it("has the nine collapsible sections, only the identity open", () => {
    setup();
    const titles = [
      "Identity",
      "Title",
      "Summary",
      "Experience (1)",
      "Education (0)",
      "Skills (3)",
      "Projects (0)",
      "Languages (1)",
      "Links (0)",
    ];
    for (const title of titles) {
      const expanded = title === "Identity";
      expect(screen.getByRole("button", { name: title })).toHaveAttribute(
        "aria-expanded",
        String(expanded),
      );
    }
    expect(screen.getByRole("textbox", { name: "Name" })).toHaveValue("Camille Exemple");
    expect(screen.queryByRole("textbox", { name: /Role/ })).not.toBeInTheDocument();
  });

  it("opens and closes a section", async () => {
    setup();
    await open("Experience (1)");
    expect(screen.getByRole("textbox", { name: "Role (Experience 1)" })).toHaveValue(
      "Développeuse",
    );
    await open("Experience (1)");
    expect(screen.queryByRole("textbox", { name: /Role/ })).not.toBeInTheDocument();
  });

  it("shows the sources of each fact as badges", async () => {
    setup();
    await open("Experience (1)");
    await open("Skills (3)");
    const row = screen.getByRole("group", { name: /Experience 1/ });
    expect(
      within(row)
        .getAllByRole("listitem")
        .map((item) => item.textContent)
        .filter((text) => text === "CV" || text === "LinkedIn"),
    ).toEqual(["CV", "LinkedIn"]);
    expect(screen.getByRole("group", { name: /Skill 2/ })).toHaveTextContent("Note");
  });

  it("adds an achievement and returns the whole profile", async () => {
    const { onSave } = setup();
    await open("Experience (1)");
    await userEvent.click(
      screen.getByRole("button", { name: "Add an achievement to experience 1" }),
    );
    await userEvent.type(
      screen.getByRole("textbox", { name: "Achievement 2 (Experience 1)" }),
      "Mise en place des tests",
    );
    await save();
    const profile = saved(onSave);
    expect(profile.experiences[0]?.achievements).toEqual([
      { id: "x1a1", text: "Refonte du tableau de bord" },
      { id: "", text: "Mise en place des tests" },
    ]);
    expect(profile).toEqual({
      ...PROFILE,
      experiences: [
        { ...PROFILE.experiences[0], achievements: profile.experiences[0]?.achievements },
      ],
    });
  });

  it("removes a skill", async () => {
    const { onSave } = setup();
    await open("Skills (3)");
    await userEvent.click(screen.getByRole("button", { name: "Remove skill 2" }));
    expect(screen.getByRole("button", { name: "Skills (2)" })).toBeInTheDocument();
    await save();
    expect(saved(onSave).skills.map((skill) => skill.name)).toEqual(["React", "Git"]);
  });

  it("adds an experience tagged with the user's source and an empty ID", async () => {
    const { onSave } = setup();
    await open("Experience (1)");
    await userEvent.click(screen.getByRole("button", { name: "Add an experience" }));
    expect(screen.getByRole("group", { name: /Experience 2/ })).toHaveTextContent("You");
    await userEvent.type(
      screen.getByRole("textbox", { name: "Role (Experience 2)" }),
      "Stagiaire",
    );
    await userEvent.type(
      screen.getByRole("textbox", { name: "Company (Experience 2)" }),
      "Acme",
    );
    await save();
    expect(saved(onSave).experiences[1]).toMatchObject({
      id: "",
      role: "Stagiaire",
      company: "Acme",
      location: null,
      sources: ["january"],
    });
  });

  it("sends a blank optional field as null and drops a blank line", async () => {
    const { onSave } = setup();
    await userEvent.clear(screen.getByRole("textbox", { name: "Location" }));
    await open("Experience (1)");
    await userEvent.click(
      screen.getByRole("button", { name: "Add an achievement to experience 1" }),
    );
    await save();
    const profile = saved(onSave);
    expect(profile.identity.location).toBeNull();
    expect(profile.experiences[0]?.achievements).toHaveLength(1);
  });

  it("puts a server error under its field, found by its path", () => {
    setup({
      error: {
        message: "Some fields need fixing.",
        fields: { "experiences.0.role": "This field is required." },
      },
    });
    // The form opens the section containing the error.
    const role = screen.getByRole("textbox", { name: "Role (Experience 1)" });
    expect(role).toHaveAttribute("aria-invalid", "true");
    expect(role).toHaveAccessibleDescription("This field is required.");
    expect(screen.getByRole("textbox", { name: "Company (Experience 1)" })).not.toHaveAttribute(
      "aria-invalid",
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Some fields need fixing.");
    expect(screen.getByRole("button", { name: "Skills (3)" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("places an error on a line of a nested list", async () => {
    setup({
      error: {
        message: "Check the highlighted fields.",
        fields: { "experiences.0.achievements.0.text": "Too long." },
      },
    });
    expect(
      screen.getByRole("textbox", { name: "Achievement 1 (Experience 1)" }),
    ).toHaveAccessibleDescription("Too long.");
  });

  it("profile 422 index mapping after empty rows", () => {
    const [first] = PROFILE.experiences;
    if (!first) throw new Error("fixture");
    const profile = {
      ...PROFILE,
      experiences: [
        {
          ...first,
          achievements: [
            { id: "a1", text: "Refonte du tableau de bord" },
            { id: "", text: "  " },
            { id: "a3", text: "Mise en production" },
          ],
        },
      ],
    };
    // The server skips the blank line, so its second entry is the third one displayed.
    setup({
      profile,
      error: {
        message: "Check the highlighted fields.",
        fields: { "experiences.0.achievements.1.text": "Too long." },
      },
    });
    expect(
      screen.getByRole("textbox", { name: "Achievement 3 (Experience 1)" }),
    ).toHaveAccessibleDescription("Too long.");
    expect(
      screen.getByRole("textbox", { name: "Achievement 2 (Experience 1)" }),
    ).not.toHaveAttribute("aria-invalid");
  });

  it("announces the dropped lines", () => {
    const { rerender } = setup({ dropped: ["Augmenté les ventes de 400 %"] });
    expect(
      screen.getByText("1 line removed: figure not found in your documents."),
    ).toBeInTheDocument();
    expect(screen.getByText("Augmenté les ventes de 400 %")).toBeInTheDocument();
    rerender({ dropped: ["a", "b"] });
    expect(
      screen.getByText("2 lines removed: figures not found in your documents."),
    ).toBeInTheDocument();
  });

  it("shows no banner without dropped line", () => {
    setup();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("locks everything while saving", () => {
    setup({ saving: true });
    expect(screen.getByRole("button", { name: "Validating…" })).toBeDisabled();
    expect(screen.getByRole("textbox", { name: "Name" })).toBeDisabled();
  });

  it("starts over from a new profile", () => {
    const { rerender } = setup();
    rerender({ profile: { ...PROFILE, identity: { ...PROFILE.identity, name: "Autre Nom" } } });
    expect(screen.getByRole("textbox", { name: "Name" })).toHaveValue("Autre Nom");
  });

  it("can be used with the keyboard only", async () => {
    const { onSave } = setup();
    const skills = screen.getByRole("button", { name: "Skills (3)" });
    skills.focus();
    await userEvent.keyboard("{Enter}");
    expect(skills).toHaveAttribute("aria-expanded", "true");
    await userEvent.tab();
    expect(screen.getByRole("textbox", { name: "Skill (Skill 1)" })).toHaveFocus();
    await userEvent.keyboard("{End} 2");
    screen.getByRole("button", { name: "Validate my profile" }).focus();
    await userEvent.keyboard("{Enter}");
    expect(saved(onSave).skills[0]?.name).toBe("React 2");
  });
});
