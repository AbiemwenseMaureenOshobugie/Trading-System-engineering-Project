# MS-0.24 — External Credential Resolution

Status: implemented from the frozen semantic contract.

## Purpose

MS-0.24 freezes the ASTER boundary for obtaining external-data credentials.

~~~
RuntimeConfig
    | credential_ref
    v
CredentialResolverPort
    | resolved secret
    v
Composition Root
    |
    v
External Adapter
~~~

## Locked decisions

- CR-D01 — Credential resolution is exposed through the application-layer CredentialResolverPort.
- CR-D02 — Only env:NAME references are supported.
- CR-D03 — The resolved value exists only in composition/adapter memory; it is not domain or persistent state.
- CR-D04 — Unsupported or unresolved references fail runtime composition/startup.
- CR-D05 — Safe reference metadata may be observable; credential values must never be observable.
- CR-D06 — Credentials are resolved once during composition/startup.
- CR-D07 — The resolver is provider-neutral: reference → secret value.

## Canonical reference

`env:TWELVE_DATA_API_KEY` means: read the named environment variable and return its non-empty value.

Other schemes such as vault:, aws:, secret:, and arbitrary URI-like references are unsupported by MS-0.24.

## Secret non-observability

The resolved credential value must never enter domain models, strategy state, Risk, Governance, Decision, AuditRecord, journal entries, persistent storage, telemetry, or exception messages.

Safe diagnostics may expose the reference, scheme/name, resolution status, and non-secret failure category.

## Failure behavior

Composition fails closed when resolution fails. No partially configured market-data adapter is constructed after credential resolution failure.

## Timing

Resolution occurs once during runtime composition. Request processing does not perform credential lookup.

Credential rotation is outside MS-0.24 and requires a future explicit decision.

## Non-goals

- Secret-management service
- Vault/AWS/Azure integration
- Credential rotation
- OAuth
- Provider-specific credential classes
- Encryption infrastructure
- MT5 authentication redesign
