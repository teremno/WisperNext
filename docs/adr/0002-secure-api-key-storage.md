# ADR 0002: Secure Groq API-key source

## Context

WisperNext requires a Groq API key but must never write it to `settings.json`, logs, support
reports, or source-controlled files. Milestone 2 has no settings UI, and adding a writable
credential implementation before its Windows behavior can be tested would expand risk.

## Decision

Read the key from the user-controlled `WISPER_GROQ_API_KEY` environment variable through a
typed `SecretProvider`. Return it as a `SecretValue` whose string representation is always
redacted. Reveal the value only at the future Groq request boundary.

Do not add API-key entry to the UI until a Windows Credential Manager adapter can persist,
retrieve, replace, and delete the credential safely and can be verified on Windows 11.

## Alternatives considered

- Plain `settings.json`: rejected because it violates the product's secret-storage rule.
- `.env` loading: rejected because it introduces another plaintext secret file and parser.
- Windows Credential Manager now: deferred because no key-entry UI exists in this milestone
  and its native lifecycle requires targeted Windows verification.

## Consequences

- Users configure the key outside the application for the current implementation.
- Application settings remain serializable without any secret field.
- A later writable adapter can implement the same boundary without changing domain code.

## Verification method

- Tests prove missing and blank variables are treated as unconfigured.
- Tests prove `repr` does not reveal the configured key.
- Settings reject unknown `api_key` fields and preservation tests retain invalid files.
- Repository checks confirm `.env*` is ignored except `.env.example`.
