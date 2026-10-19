\# MS-0.1A Phase A record



Branch: ms-0.1a-phase-a-rework

Pushed HEAD: 5a0b36a5809f3b18ff9d15ed30e7c31dfef975e5

Base: dfba915c89be08f597a2a39868b769a42707ff71 (main)



\## Commits



&#x20; 368c1f5 MS-0.1A Phase A: add failing conformance tests for R56, R57, R59, R65, R68

&#x20; f1d0f7e R56: TRANSITION exists only while no replacement regime is established

&#x20; 768e1fc R57: invalidated structure becomes non-controlling

&#x20; 3bfcece R59, R68: gate range breakout on no established trend

&#x20; 5a0b36a R65: fail a range penetration when the next completed candle closes inside the range



Author: rework-engine <rework@example.invalid> (sandbox implementation engine)

Applied by: AbiemwenseMaureenOshobugie



\## Verification (fresh clone, detached at origin/ms-0.1a-phase-a-rework)



&#x20; git rev-parse HEAD

&#x20;   5a0b36a5809f3b18ff9d15ed30e7c31dfef975e5



&#x20; git merge-base --is-ancestor origin/main HEAD

&#x20;   exit 0



&#x20; git diff origin/main..HEAD --stat

&#x20;   src/trading\_system/strategy/market\_structure/engine.py       |  30 +++-

&#x20;   tests/unit/test\_market\_structure\_engine.py                   | 159 +++++++++

&#x20;   2 files changed, 182 insertions(+), 7 deletions(-)



&#x20; PYTHONPATH=src python -m pytest -q

&#x20;   319 passed in 13.70s



\## Conformance status



&#x20; R56   IMPLEMENTED

&#x20; R57   PARTIAL (see below)

&#x20; R59   IMPLEMENTED

&#x20; R65   IMPLEMENTED

&#x20; R68   IMPLEMENTED



\## R57 disclosure



IMPLEMENTED sub-clause: "Invalidated structure remains historical but

becomes inactive and non-controlling." TRANSITION returns None as the

controlling level after an invalidation.



PARTIAL sub-clause: "Old invalidated structure is not silently revived."

One new HL after an invalidation can still restore UPTREND from old

counts, because \_trend\_status counts all historical labels.



Insufficient spec text (verbatim, §8): "Each later invalidation of a

replacement regime creates a distinct transition episode." The sentence

names an episode but does not define what structural evidence belongs

to it.



What a future amendment would need to say: which swings count toward

HH/HL (or LH/LL) after an invalidation; whether the invalidating close

belongs to the pre-invalidation or post-invalidation episode; whether a

swing sharing the invalidation timestamp counts.



\## Follow-ups recorded



R13 — opposing-swing rebinding. Landed spec text (§3) requires recording

old and new opposing references in structural\_events on replacement. No

engine implementation. Out of Phase A scope.



Deferred items blocking future work:

&#x20; - §5 bootstrap (first meaningful swing admission) — blocks Phase B

&#x20; - §8 "distinct transition episode" counting rule — blocks R57 full

&#x20; - §7 "established/progressed" controlling-swing semantics — blocks

&#x20;   trend-behavior tests

&#x20; - R13 opposing-swing rebinding implementation

