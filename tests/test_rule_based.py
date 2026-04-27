import pytest

from app.classification.rule_based import score_xlsx


def test_payable_keywords_score_highest():
    text = "accounts payable ageing vendor supplier creditor 0-30 days"
    scores = score_xlsx(text)
    assert scores[0].class_label == "payable_ageing_report"
    assert scores[0].score > 0


def test_receivable_keywords_score_highest():
    text = "accounts receivable ageing customer debtor ar aging 31-60 days"
    scores = score_xlsx(text)
    assert scores[0].class_label == "receivable_ageing_report"
    assert scores[0].score > 0


def test_scores_sorted_descending():
    text = "payable ageing vendor supplier creditor"
    scores = score_xlsx(text)
    assert scores[0].score >= scores[1].score


def test_zero_hits_gives_zero_score():
    text = "completely unrelated document content here"
    scores = score_xlsx(text)
    for s in scores:
        assert s.score == 0.0


def test_case_insensitive_matching():
    text = "ACCOUNTS PAYABLE AGEING VENDOR"
    scores = score_xlsx(text)
    payable = next(s for s in scores if s.class_label == "payable_ageing_report")
    assert payable.hits > 0


def test_partial_match_returns_nonzero_score():
    text = "vendor supplier"
    scores = score_xlsx(text)
    payable = next(s for s in scores if s.class_label == "payable_ageing_report")
    assert 0 < payable.score < 1.0
