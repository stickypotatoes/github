# Coach Adversarial Corpus

The ruled test corpus for the Live Call Coach's stop-recognition decisions.
Each case is a seller sentence plus the verdict the system is required to
produce for it. This corpus is the release gate's evidence base: no Coach
build ships unless the corpus passes against it.

## The five verdicts

- **CONFIRMED** — a real stop. It latches and never auto-clears.
- **POSSIBLE** — unresolved. Coaching holds and a human decides.
- **POSSIBLE_BOUNDARY** — a time or scope limit on contact. Recorded as a
  boundary; never a latch.
- **CHANNEL_SCOPED_STOP** — a stop for one channel only (e.g. texting).
  Other channels are unaffected.
- **NO_STOP** — no stop decision may be derived from this sentence.

## Case schema

`corpus/stop_cases.jsonl` holds one JSON object per line:

| Field     | Meaning                                             |
|-----------|-----------------------------------------------------|
| `id`      | Stable case identifier (e.g. `S01`)                 |
| `text`    | The seller sentence, verbatim                       |
| `verdict` | One of the five verdicts above                      |
| `class`   | The case family (e.g. `direct`, `negation`)         |
| `basis`   | One line: the ruling the case encodes               |

## Running the tests

```sh
pip install pytest
pytest
```

The tests validate the corpus as data — format, required fields, allowed
verdicts, unique ids, unique texts, non-empty bases. There is no classifier
in this repo, and the tests do not run one.
