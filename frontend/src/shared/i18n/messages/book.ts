export const book = {
  title: "Your book",
  program: {
    label: "Program",
    pick: "Select a program",
    empty: "Create a program from a goal",
  },
  edition: {
    label: "Program edition",
    prepare: "Prepare the book",
    queued: "The edition is being prepared.",
    failed: "The book couldn't be prepared.",
    retry: "Retry",
    chapters: "Chapters published in the edition: {count}",
  },
  download: {
    pdf: "Download as PDF",
    epub: "Download as EPUB",
  },
  notes: {
    title: "Link an Obsidian note",
    help: "Add this wiki link to a synced note. Replace “lesson-id” with the ID at the end of the lesson's URL.",
    link: "[[tremplin:lesson:lesson-id]]",
  },
} as const;
