# Packet and report contracts

## Compatibility

v0.3.0 accepts original schema_version 1 packets without modification. Their
comparison behavior, result fields and report bytes remain unchanged. Version 2
is opt-in with schema_version 2 and a baselines array (empty is allowed). Never
silently reinterpret a v1 packet as requiring an action-caused change.

Versioned [JSON Schemas](../schemas) use Draft 2020-12 for packets, individual
requirements/observations, baselines and reports. Run
`uv run python scripts/validate_schemas.py` to check all committed contract examples.
Runtime validation additionally enforces unique IDs, exact Python integer types,
finite numbers, calendar validity, nesting depth, regex safety and cross-record
relationships. JSON Schema alone cannot prove evidence truth or those relationships.

## Version 1

Exact root fields: schema_version (integer 1), as_of (timezone-aware RFC3339),
requirements (nonempty array), actions (array), observations (array). Each array
<= 10,000, IDs unique per array. IDs, subjects and object keys are nonblank strings
<= 200 characters. Files UTF-8 without BOM, <= 5 MiB; duplicate JSON keys invalid.

Requirement exact fields: id, subject, path (1..32 object-key strings), expected
(JSON value, recursive depth <= 32), observation_id, max_age_seconds (nonnegative
integer, Boolean forbidden), action_id (ID or null). Observation exact fields:
id, subject, observed_at (RFC3339), state (JSON object). Action exact fields:
id, status (succeeded|failed|unknown). Unknown fields and nonfinite numbers fail.

Missing references are unobserved. Only the named observation is checked. Its
subject must match and age must be in [0,max_age_seconds] relative to as_of.
Missing object paths are unobserved. Equality is recursive and typed, except
integer/float numeric equivalence. No array indexing, expressions or collectors.

Action: succeeded=>confirmed, failed=>contradicted, unknown/missing=>unobserved,
null=>not_required. Overall contradicted if either required component contradicted;
confirmed if outcome confirmed and action confirmed/not_required; otherwise
unobserved. Reports show both components and an outcome reason. No clock lookup.
Output schema_version 1, counts, results, exit_code and exact input SHA-256.

Offset hours 00..23/minutes 00..59 are enforced. Fractional-second freshness uses
every supplied digit. Leap seconds and year 0000 are unsupported by the calendar
parser and rejected. Timestamp strings are limited to 64 characters.

## Version 2 checks and baseline evidence

Root adds required baselines and optional require_signatures (Boolean, default
false). Baseline rows have the same shape as observations. ID uniqueness is per
array, with explicit baseline_id references into baselines. Requirements retain
all v1 fields and optionally add check (default equal), baseline_id and
requires_change (Boolean, default false). Even baseline-only checks retain expected
for a stable requirement shape; that field is ignored by those two check types.

- equal: the original recursive typed equality.
- range: expected is an object with min and/or max, each a finite number; optional
  min_inclusive/max_inclusive are Booleans and default true. An inclusivity flag
  needs its matching bound. Reversed bounds are invalid. Observed Booleans and
  nonnumbers contradict the check. Numbers need no float subtraction.
- contains: observed value must be an array with at least one member equal to
  expected under typed recursive equality. Objects, substrings and array indices
  are not membership checks.
- regex: expected is the restricted pattern described below; observed value must
  be a string of at most 4096 characters. Uses fullmatch, including at newline
  boundaries. Wrong types or oversized observations contradict the check.
- unchanged / changed_from_baseline: require baseline_id and compare the addressed
  value to that baseline using typed equality. They respectively confirm equality
  or inequality. unchanged conflicts with requires_change=true and is rejected.

A selected baseline must match the subject, contain the same object path and
strictly precede the selected final observation. A missing or incompatible baseline
is unobserved, never confirmed. No baseline age threshold is inferred from final
max_age_seconds. Its preaction provenance is supplied by the caller: the tool has
no action clock or collector and cannot establish when an action occurred.

For an otherwise satisfied equal/range/contains/regex check with requires_change=true,
an unchanged addressed value returns outcome and status unconfirmed with reason
`no observed change`. Failed action still makes overall status contradicted.
Different state can satisfy a change check without proving which action caused it.
A caller must choose requires_change only when change is actually required; a correct
refusal or deliberately unchanged state may be the legitimate target.

Version 2 reports add counts.unconfirmed and each result's signature label. Exit 0
means all requirements confirmed, exit 1 includes unconfirmed, unobserved or
contradicted results; exit 2 means invalid input/I/O. Readers restricted to three
statuses must migrate before adopting version 2. Version 1 reports keep three counts.

## Restricted regex safety

Patterns are 2..256 ASCII characters, anchored with ^ and $. The body permits
ASCII letters/digits and literal space, underscore, hyphen, colon, slash, comma,
at sign. Bracket classes contain only ASCII letters/digits, spaces, underscore,
hyphen and valid ranges. Escapes permit only literal `. - _ ^ $ [ ] { }` and
backslash. Each atom may have one fixed `{n}` repetition with 1<=n<=128; the total
expanded width is <=4096. Empty bodies are allowed. Examples: `^ok$`,
`^[A-Z]{2}[0-9]{2}$`,`^v[0-9]\\.[0-9]$` (JSON requires escaped backslashes).

Alternation, groups, lookarounds, backreferences, wildcard dots, shorthand classes,
unbounded quantifiers, variable repetitions and flags are rejected. The stdlib
engine receives only a fixed-width sequence of literals/classes: it has no choices
of repetition length or alternative branch. This bounds complexity by construction;
there is no timeout API or timeout guarantee. Arbitrary regular expressions are not
supported, and rejection is an input error rather than a silently changed pattern.

## Optional signatures

Observation/baseline signature is an object with exact fields algorithm (Ed25519),
key_id (ID), signature (base64, <=128 characters, decoded length exactly 64).
Unsigned observations are labeled unsigned and remain usable unless
require_signatures=true. Supplied signatures without a verifier are unverified.
A verified signature proves the supplied bytes match a locally supplied public key,
not truthful state, collector accuracy, freshness in the real world or action cause.
Invalid signatures cannot confirm a check. Missing/unverified signatures cannot
confirm when require_signatures=true; the same rule applies to selected baselines.

`check_packet(packet, verifier=None)` accepts the SignatureVerifier protocol from
outcome_check.signatures. Verifiers are trusted local application code, not executable
plugins loaded from packet data. The provided Ed25519Verifier accepts a mapping of
key IDs to raw 32-byte public keys and never downloads keys. Install the signing
extra for cryptography; default core has zero dependencies. Optional sign_observation
returns a new row from a raw local private key; it never writes or persists that key.

CLI `--public-keys keys.json` reads a local JSON object mapping key IDs to base64
32-byte public keys. Duplicate keys, malformed key IDs, bad encoding and input over
5 MiB fail. Key files are read-only inputs and cannot alias a report output. Keys are
not secrets; the CLI has no private-key or signing option.

Payload is canonical JSON of the complete observation excluding signature, plus
algorithm and key_id at its top level. Canonicalization implements only this RFC 8785
subset: null, Boolean, strings without lone surrogates, arrays, objects sorted by
UTF-16 code units, and safe integers [-9007199254740991,9007199254740991]. Strings
use JSON control escaping and UTF-8 without normalization. Floats, larger integers
and lone surrogates are rejected for signing/verification. This is not full RFC 8785
number support. Ordinary unsigned checks still accept all finite JSON floats.

## Local report writes

HTML displays lone surrogates accepted in unsigned JSON as visible `\ud800`-style
backslash escapes, including in evidence cells and the timeline. Ordinary Unicode
is preserved. This display rule does not change verdicts, JSON report bytes,
embedded download bytes, or signing and canonicalization restrictions.

All inputs and target aliases (including existing hard links) are checked before
any write. --force permits replacing reports; its absence never overwrites a newly
created competing target. Each report stages beside its target, flushes/fsyncs, then
uses atomic replacement (--force) or hard-link publication (no force). Temporary
stages are cleaned after failure. The input and unrelated files remain untouched.
Multiple reports are not a transaction: a later export failure can leave an earlier
completed report. Atomic replacement requires filesystem support; unsupported
operations fail closed. This does not promise crash recovery or directory durability.

## Version 3 signatures and migration

Version 0.4.0 adds schema_version 3 with the v2 check/baseline semantics and
report statuses. A signed v3 observation or baseline requires one additional
signature field, `canonicalization: "RFC8785"`. The complete row excluding its
signature is combined with algorithm, key_id and canonicalization at top level,
then serialized and signed. Unknown profiles or algorithms are rejected. Changing
or stripping profile metadata cannot preserve a valid v3 signature.

`outcome_check.canonical.canonicalize` implements RFC 8785 serialization over
finite IEEE-754 binary64 values: shortest round-trip decimal, ECMAScript's
fixed/exponent thresholds, negative zero as 0, exact JSON control escaping,
UTF-16 object-key ordering, and UTF-8 output without Unicode normalization.
NaN, infinities, lone surrogates, non-JSON types and nesting beyond 32 fail.
Python integers are accepted only if exactly representable as binary64; arbitrary
precision integers must use strings. This avoids silently rounding a supplied
integer into different signed content. Ordinary unsigned v1/v2 values retain
their previous semantics.

The legacy `canonical_json` and default `sign_observation` retain their restricted
v2 bytes and reject floats. Request the new profile explicitly with
`sign_observation(row, key_id, private_key, canonicalization="RFC8785")` and place
that observation in a v3 packet. v2 packets reject the new field. Algorithm and key
ID remain bound for both versions; a signature proves supplied bytes under a local
key, never their truth or which agent caused a change.

`migrate_to_v3(packet)` validates and deep-copies unsigned v1/v2 packets, adding an
empty baselines array where needed. It rejects signed input. A trusted signer must
retain the original content, remove the old signature only as part of authentic
re-signing, sign every affected observation/baseline with the new profile, and
then validate the new v3 packet. Never merely relabel an old signature or discard
signatures to imply that authentication survived migration.

Interoperability evidence: all 24 finite RFC 8785 Appendix B numeric vectors;
1,000 deterministic Hypothesis float examples; 20,000 seeded binary64 candidates
against dev-only rfc8785 0.1.4; and 99,956 finite candidates against Node 22.23.2
V8 JSON.stringify. Run `uv run python scripts/check_jcs_interop.py` for the latter.
Sources: [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785#appendix-B) and
[reference implementation](https://github.com/trailofbits/rfc8785.py/tree/v0.1.4).
These are finite interoperability checks, not an exhaustive enumeration of all
binary64 values. Neither reference implementation is a product runtime dependency.
