# Requirement matrix

| Requirement | Mechanism | Status |
|---|---|---|
| Consensus-bound semantic mapping | Strict pose/duration normalization | PASS: forged pose rejected |
| Complete canonical output | One unique row per fragment | PASS: strict direct suite |
| Deterministic result | Exhaustive longest compatible chain | PASS: complete, partial, and reordered cases |
| Authorization and liveness | Frozen creators, replay block, expired paths | PASS: targeted tests |
| Exact deployed source | Transaction source comparison | PASS: exact byte match |
