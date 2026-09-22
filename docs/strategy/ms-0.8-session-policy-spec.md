# MS-0.8 — Session / Time Policy Engine

## Objective

Define when ASTER permits trading based on the canonical session rules, producing a deterministic session eligibility result that Governance can consume.

## Inputs

`timestamp_utc: datetime`

The input represents a UTC timestamp and must be timezone-aware and UTC.

## Session Identity

- `ASIAN`
- `LONDON`
- `LONDON_NEW_YORK_OVERLAP`
- `NEW_YORK`
- `OUTSIDE_SESSION`

## Temporal Boundaries (UTC)

| Session | Window |
|---|---|
| Asian | 00:00–08:00 |
| London | 07:00–16:00 |
| New York | 12:00–21:00 |
| London–New York overlap | 12:00–16:00 |
| Outside | all other |

Identity precedence is:

1. 12:00 ≤ time < 16:00 → `LONDON_NEW_YORK_OVERLAP`
2. 07:00 ≤ time < 16:00 → `LONDON`
3. 00:00 ≤ time < 08:00 → `ASIAN`
4. 12:00 ≤ time < 21:00 → `NEW_YORK`
5. otherwise → `OUTSIDE_SESSION`

## Trading Eligibility

`is_trading_permitted` is true only when:

- the UTC day is Monday–Friday, and
- the session identity is `LONDON` or `LONDON_NEW_YORK_OVERLAP`.

Otherwise it is false.

## Output Contract

`SessionPolicyResult` contains:

- `timestamp_utc: datetime`
- `session_identity: SessionIdentity`
- `is_trading_permitted: bool`
- `reason: Optional[str]`

Derived properties:

- `is_london_session`
- `is_overlap`
- `is_asian_session`

The session identity and `is_trading_permitted` field are authoritative. `reason` is explanatory only.

## Scope Exclusions

MS-0.8 does not:

- modify strategy rules;
- modify Risk Engine;
- modify Decision Engine;
- invent session hours;
- handle holidays;
- apply DST adjustments;
- add weekend trading;
- add Asian trading;
- use AI/ML.

## Invariants

- **I-56:** Session identity is the authoritative temporal field.
- **I-57:** Trading is permitted only during London or London–New York overlap on Monday–Friday.
- **I-58:** No holiday logic is introduced.
- **I-59:** No DST adjustment is applied.
- **I-60:** Session eligibility is supplied to Governance.
- **I-61:** `reason` is explanatory, not authoritative.

## Acceptance Tests

- **MS08-T-01:** Timestamp in London session → `LONDON`.
- **MS08-T-02:** Timestamp in overlap → `LONDON_NEW_YORK_OVERLAP`.
- **MS08-T-03:** Timestamp in Asian session → `ASIAN`.
- **MS08-T-04:** Timestamp in New York session → `NEW_YORK`.
- **MS08-T-05:** Timestamp outside sessions → `OUTSIDE_SESSION`.
- **MS08-T-06:** Trading permitted during London Monday–Friday.
- **MS08-T-07:** Trading permitted during overlap Monday–Friday.
- **MS08-T-08:** Trading not permitted during Asian.
- **MS08-T-09:** Trading not permitted during New York.
- **MS08-T-10:** Trading not permitted Saturday.
- **MS08-T-11:** Trading not permitted Sunday.
- **MS08-T-12:** No holiday logic applied.
- **MS08-T-13:** No DST adjustment applied.
- **MS08-T-14:** `SessionPolicyResult` is deterministic.
- **MS08-T-15:** `is_trading_permitted` is authoritative; `reason` is explanatory.
