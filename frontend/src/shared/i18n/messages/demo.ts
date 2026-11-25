/** Texts for the agent engine demo. */
export const demo = {
  title: "Agent engine demo",
  intro:
    "An Advocate and a Critic debate a topic of your choice; the team asks you a question between the two rounds.",
  topic: {
    label: "Topic",
    placeholder: "e.g. learning Rust",
    submit: "Start the debate",
    starting: "Starting…",
  },
  loading: "Opening the debate…",
  reconnecting: "Live connection lost, reconnecting…",
  restart: "New debate",
  cancel: {
    title: "Cancel the debate?",
    description: "The agents will stop and the session can't be resumed.",
    confirm: "Yes, cancel the debate",
    keep: "No, continue",
  },
} as const;
