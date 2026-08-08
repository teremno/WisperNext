# ADR 0002: Secure Groq API-key source

## Context

WisperNext requires a Groq API key but must never write it to `settings.json`, logs, support
reports, or source-controlled files. Milestone 2 has no settings UI, and adding a writable
credential implementation before its Windows behavior can be tested would expand risk.

## Decision

Use a user-scoped Generic Credential named `WisperNext/GroqApiKey` in Windows Credential
Manager as the primary persistent source. Use the user-controlled `WISPER_GROQ_API_KEY`
environment variable only as a development fallback. Both implement the typed `SecretProvider`
boundary and return a `SecretValue` whose representation is always redacted.

The native adapter uses Windows `CredReadW`, `CredWriteW`, `CredDeleteW`, and `CredFree` directly,
so no plaintext file or credential dependency is required. Reveal the value only at the Groq
request boundary. The future settings UI may call the same save/replace/delete boundary.

## Alternatives considered

- Plain `settings.json`: rejected because it violates the product's secret-storage rule.
- `.env` loading: rejected because it introduces another plaintext secret file and parser.
- Environment variable as the permanent source: rejected because ordinary desktop launches do
  not reliably inherit a development-process variable.

## Consequences

- A normal launch under the same Windows account can retrieve the key after reboot.
- Application settings remain serializable without any secret field.
- The development environment variable remains a lower-priority fallback.

## Verification method

- Tests prove missing and blank variables are treated as unconfigured.
- Tests prove `repr` does not reveal the configured key.
- Tests prove persist/replace/read/delete and credential-first fallback behavior through a fake
  store.
- A Windows 11 live test writes the existing process key, reads it back, compares it in memory,
  then performs a Groq request with the environment variable removed from the child process.
- Settings reject unknown `api_key` fields and preservation tests retain invalid files.
- Repository checks confirm `.env*` is ignored except `.env.example`.
