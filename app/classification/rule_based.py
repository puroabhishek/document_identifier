from __future__ import annotations

import glob
import os
from dataclasses import dataclass

import yaml


def _load_rules() -> list[dict]:
    rules_dir = os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "rules")
    rules_dir = os.path.normpath(rules_dir)
    rules = []
    for path in sorted(glob.glob(os.path.join(rules_dir, "*.yaml"))):
        with open(path, "r") as f:
            rules.append(yaml.safe_load(f))
    return rules


AGEING_RULES: list[dict] = _load_rules()


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
