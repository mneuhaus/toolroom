# Purpose coverage

`assess_purpose_coverage(catalog, purpose_report)` checks whether every item in a
declared occurrence, contribution, and finding catalog has an acceptable review
against known nodes in a `pruefstand.purpose-report/1` report. It is a pure,
offline check: it performs no file, CAD, or network access.

The catalog uses schema `pruefstand.purpose-coverage/1`. Its `source` records a
nonempty microversion and lowercase SHA-256 values for the assembly and generator.
`expected` must be a nonempty list of unique items with `id`, `kind`, and a
nonempty descriptive `source` object. `reviews` uses the same IDs and records a
decision, linked purpose-node IDs, reason, and evidence. Root, expected-item, and
review keys are strict; invalid and non-finite JSON values raise `ValueError`.

`explained` and `changed` reviews require a reason, evidence, and at least one
known purpose node. `changed` applies only to findings and represents an
independently evidenced removal or change. An `open` review remains incomplete;
it is never inferred to be explained from its linked nodes.

The result uses schema `pruefstand.purpose-coverage-report/1` and retains every
expected item, its descriptive source, and its review. Item states are `covered`,
`review`, or `incomplete`. Overall status follows
`incomplete > review > no_findings`, and `complete` is true only for
`no_findings`.

- Missing and open reviews are incomplete.
- An explained occurrence, contribution, or finding linked to an `ABSENT` or
  `UNKNOWN` node is incomplete.
- Any linked `ORPHAN` node requires review.
- A changed finding may link an `ABSENT` node. `UNKNOWN` remains incomplete and
  `ORPHAN` still requires review.
- Every linked node is assessed, so a `ROOTED` node cannot hide another listed
  `ABSENT`, `UNKNOWN`, or `ORPHAN` node.

The report covers only the declared catalog, supplied reviews, and linked purpose
classifications. It does not verify artifact bytes, establish that material is
necessary, prove geometry or physical behaviour, or authorize automatic deletion.
