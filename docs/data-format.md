# Tool and CLI payloads

A record payload has `name`, original `source_text`, and `observations` (possibly empty for an interaction-only record). Optional: confirmed `person_id`, `account_urls`, `occurred_on` (YYYY-MM-DD or null), `source_url`, stable `request_id`, `explicit`, `save_allowed`, `confirm_distinct`.

Each observation requires `category`, `text`, and `evidence`, which must be an exact excerpt present in source_text. Categories: background, skill, interest, project, need, offer, commitment, note. `certainty`: explicit (default), inferred, unverified. `status`: current, open, resolved, outdated, needs_confirmation. Needs/commitments default to open, other observations to current.

Needs also accept optional `origin`: `requested` (the person asked), `user_created` (the user made a concrete offer or promise to help), or `inferred` (a need interpreted from other context). Existing records without origin remain valid. Origin is preserved through updates, export, and undo. It is separate from `certainty`.

For example, “If I find good AI learning resources, I’ll recommend them to you” can produce an open `user_created` need for suitable resources alongside an open commitment to recommend them. Preserve the condition and do not describe it as the recipient’s explicit request. Completing a recommendation does not by itself prove the recipient’s underlying need is resolved.

Account URLs identify a person only when confirmed by the user/source. Account URLs are normalized (known tracking parameters removed on LinkedIn/X; identity-bearing query parameters and fragments preserved; common LinkedIn/X account paths lowercased); name matches require confirmation. If no identifier can disambiguate an existing name, the assistant must ask for identity clarification. `confirm_distinct` is a conscious declaration of a different person, not an automatic retry switch.

Retries reuse the same request_id with identical arguments. Different content under the same request ID is rejected. Without a request ID, identical canonicalized payloads deduplicate. Semantically equivalent paraphrases aren't automatically deduplicated; the assistant must inspect history. An undone request stays marked undone; a new deliberate recording requires a new request ID.

Update JSON:

```json
{
  "observation_id": "ID_FROM_HISTORY",
  "expected_revision": 1,
  "text": "PCB designer found",
  "status": "resolved",
  "source_text": "Riley found a PCB designer yesterday.",
  "evidence": "found a PCB designer",
  "occurred_on": null
}
```

The source excerpt proves provenance, not factual correctness or proper attribution; the assistant is responsible for interpreting it. A fresh correction creates an interaction and revises the observation. Earlier versions remain in the audit journal until forgotten.
