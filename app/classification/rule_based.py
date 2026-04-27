import re
from dataclasses import dataclass


AGEING_RULES: list[dict] = [
    {
        "class_label": "payable_ageing_report",
        "keywords": [
            "payable ageing", "payable aging", "accounts payable",
            "ap ageing", "ap aging", "creditors ageing", "creditor aging",
            "vendor", "supplier", "creditor",
        ],
    },
    {
        "class_label": "receivable_ageing_report",
        "keywords": [
            "receivable ageing", "receivable aging", "accounts receivable",
            "ar ageing", "ar aging", "debtors ageing", "debtor aging",
            "customer", "debtor",
        ],
    },
]


@dataclass
class RuleScore:
    class_label: str
    hits: int
    total: int

    @property
    def score(self) -> float:
        return self.hits / self.total if self.total else 0.0


def score_xlsx(text: str) -> list[RuleScore]:
    text_lower = text.lower()
    scores = []
    for rule in AGEING_RULES:
        hits = sum(1 for kw in rule["keywords"] if kw in text_lower)
        scores.append(RuleScore(class_label=rule["class_label"], hits=hits, total=len(rule["keywords"])))
    return sorted(scores, key=lambda s: s.score, reverse=True)
