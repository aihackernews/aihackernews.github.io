# Issue bookkeeping queue

The community-submissions processor queues GitHub issue actions here as
`issue-<N>.json` files:

```json
{
  "issue": 12,
  "comment": "text to post as a comment, or null",
  "close": "completed"
}
```

`close` is one of `"completed"`, `"not_planned"`, or `null` (comment only).

The `Issue bookkeeping` GitHub Actions workflow
(`.github/workflows/issue-bookkeeping.yml`) performs the comment/close with
its built-in token and deletes the queue file afterwards. Files here are
transient — an empty queue is the normal state.
