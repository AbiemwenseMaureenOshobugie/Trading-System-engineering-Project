# GKS-0.1 — Canonical Governing Key-Level Selection

## Purpose

Select the single Key Level governing an H1 thesis before M15 confirmation.

GKS is downstream of MS-0.1A H1 structure and MS-0.2 Key-Level Detection.
It does not create, modify, merge, or reconstruct Key-Level geometry.

## GKS-01 — Eligibility

A Key Level is eligible only when:

- `active == True`
- its `role` is direction-compatible:
  - BUY → `SUPPORT`
  - SELL → `RESISTANCE`

A missing or incompatible role makes the Key Level ineligible.

## GKS-02 — Structural association

The H1 `MarketStructureState.controlling_level` is the structural anchor.

When present, its canonical MS-0.2 evidence reference is:

`SWING:{controlling_level.kind.value}:{controlling_level.timestamp.isoformat()}`

A Key Level is structurally associated with the controlling level when that exact
reference is present in `KeyLevel.evidence_refs`.

Association is exact. It is not based on price, timestamp alone, zone geometry,
proximity, or Key-Level ID.

If `controlling_level` is absent, there is no governing Key Level.

## GKS-03 — Selection

After applying eligibility and structural association:

- exactly one eligible Key Level → select it;
- zero eligible Key Levels → `NO_GOVERNING_KEY_LEVEL`;
- more than one eligible Key Level → `STRUCTURAL_CONSISTENCY_FAILURE`.

The selector uses `evidence_refs`, not `source_types` or `role`, to establish
structural association. Role is used only for direction compatibility.

## GKS-04 — Canonical evidence reference

GKS reuses the existing MS-0.2 validated-swing evidence reference:

`SWING:{controlling_level.kind.value}:{controlling_level.timestamp.isoformat()}`

No new controlling-level identifier is introduced.

## Boundary

GKS does not:

- select CP-1/CP-2 confirmation;
- calculate risk;
- determine stop loss;
- determine target;
- alter MS-0.1A structure;
- alter MS-0.2 source-zone semantics;
- use tolerance or proximity matching.

The selected Key Level is passed downstream as the governing `setup_key_level`.
