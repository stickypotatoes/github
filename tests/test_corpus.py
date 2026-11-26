"""Validate the Coach adversarial corpus as data.

These tests check the corpus file's format and internal consistency only.
There is no classifier in this repo, and nothing here runs one.
"""
import json
from pathlib import Path

CORPUS = Path(__file__).resolve().parent.parent / "corpus" / "stop_cases.jsonl"

ALLOWED_VERDICTS = {
    "CONFIRMED",
    "POSSIBLE",
    "POSSIBLE_BOUNDARY",
    "CHANNEL_SCOPED_STOP",
    "NO_STOP",
}
REQUIRED_FIELDS = {"id", "text", "verdict", "class", "basis"}


def load_cases():
    lines = [ln for ln in CORPUS.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines]


def test_corpus_file_parses_line_by_line():
    cases = load_cases()
    assert len(cases) > 0


def test_every_case_has_all_five_fields():
    for case in load_cases():
        assert REQUIRED_FIELDS <= set(case), f"{case.get('id')} missing fields"


def test_every_verdict_is_in_the_allowed_set():
    for case in load_cases():
        assert case["verdict"] in ALLOWED_VERDICTS, f"{case['id']}: {case['verdict']}"


def test_ids_are_unique():
    ids = [c["id"] for c in load_cases()]
    assert len(ids) == len(set(ids))


def test_no_two_cases_share_identical_text():
    texts = [c["text"] for c in load_cases()]
    assert len(texts) == len(set(texts))


def test_every_basis_is_non_empty():
    for case in load_cases():
        assert isinstance(case["basis"], str) and case["basis"].strip(), case["id"]
