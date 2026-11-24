export const lessonUpdates = {
  title: "Release watch",
  release: "{name} {version}",
  source: "View the changelog",
  compare: "Compare example {block}",
  before: "Published example",
  after: "Proposed example",
  accept: "Approve and verify the fix",
  retryDraft: "Retry preparation",
  retryCheck: "Retry verification",
  state: {
    preparing: "The Verifier is preparing the fix…",
    ready: "Fix to approve",
    stale: "The lesson has changed since this proposal.",
    failed: "The fix didn't go through. The published lesson is still available.",
    checking: "The approved fix is being verified…",
    published: "Fix published",
  },
} as const;
