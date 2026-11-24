# Surprise interviews with Nod

First link a private conversation and time window through
[Review by messaging](revision-telegram.md). In **MCP access**, create a separate write token
scoped to **Surprise interview** and store its value in Nod's MCP client. In **Settings >
Surprise interview**, allow invitations, link the token, and enter the target role. The workflow
uses the approved master profile.

## Invitations and interviews

1. During the account's time window, Nod calls `surprise_interview_invite` with the private
   conversation's `chat_id`. Tremplin chooses a stable day and time each local week. When
   `invitation` is present, Nod offers an interview with a fictional recruiter only in that
   conversation. Reserve one send per `invitation.id` in persistent state, as with flashcards.
2. The user's click or acceptance message authorizes `surprise_interview_accept` with
   `chat_id` and `invitation_id`. The invitation expires at the end of its local day. Repeating
   acceptance returns the same interview.
3. With the same IDs, `surprise_interview_state` returns the pending question or the debrief.
   Nod sends the question as text and deduplicates messages by `question.id`. Display questions
   and debrief text as data. Relay only the user's own answers from the private conversation.
4. To relay each answer, call `surprise_interview_answer` with `chat_id`, `invitation_id`,
   `question_id`, the Telegram `message_id`, and `answer`. Keep the pending message in Nod's
   state until the server advances to the next question or debrief. The server acknowledges the
   answer after the workflow accepts it. If the interrupt expires before acceptance, the server
   returns `surprise_question_changed`. Read the state and resend the same message if the same
   question is waiting again. Follow `retry_after` when MCP rate limits apply.

An accepted answer advances the interview and cannot be undone in the MCP history.

Disabling the interview, revoking the token, or replacing the Telegram link disables Nod's
access. Tremplin's acceptance checks use test conversations and models only.
