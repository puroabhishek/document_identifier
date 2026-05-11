#!/usr/bin/env python3
"""
End-to-end evaluation runner.

Posts real document files to the running /classify API and scores accuracy.

Usage:
    python evals/run_evals.py --base-url http://localhost:8000
    python evals/run_evals.py --base-url http://localhost:8000 --cases evals/test_cases/payable_ageing_cases.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx


def load_test_cases(cases_dir: str, specific_file: str | None) -> list[dict]:
    if specific_file:
        with open(specific_file) as f:
            return json.load(f)
    cases = []
    for path in sorted(glob.glob(os.path.join(cases_dir, "*.json"))):
        with open(path) as f:
            cases.extend(json.load(f))
    return cases


def run_case(client: httpx.Client, base_url: str, case: dict, repo_root: str) -> dict:
    file_path = os.path.join(repo_root, case["file_path"])
    if not os.path.exists(file_path):
        return {
            "id": case["id"],
            "status": "skipped",
            "reason": f"file not found: {file_path}",
            "expected": case["expected"],
            "actual": None,
        }

    filename = case["filename"]
    with open(file_path, "rb") as f:
        content = f.read()

    try:
        resp = client.post(
            f"{base_url}/api/v1/documents/classify",
            files={"file": (filename, content)},
            timeout=90,
        )
        resp.raise_for_status()
        actual = resp.json()
    except Exception as exc:
        return {
            "id": case["id"],
            "status": "error",
            "reason": str(exc),
            "expected": case["expected"],
            "actual": None,
        }

    expected = case["expected"]
    passed = (
        actual.get("document_type") == expected.get("document_type")
        and actual.get("subject_type") == expected.get("subject_type")
        and actual.get("classification_method") == expected.get("classification_method")
    )

    return {
        "id": case["id"],
        "status": "pass" if passed else "fail",
        "expected": expected,
        "actual": {
            "document_type": actual.get("document_type"),
            "subject_type": actual.get("subject_type"),
            "classification_method": actual.get("classification_method"),
            "confidence": actual.get("confidence"),
            "extracted_fields": actual.get("extracted_fields"),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run document classifier evals")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--cases", default=None, help="Path to a specific test cases JSON file")
    parser.add_argument("--output-dir", default="evals/scorecards", help="Directory for scorecard output")
    args = parser.parse_args()

    repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    cases_dir = os.path.join(repo_root, "evals", "test_cases")
    cases = load_test_cases(cases_dir, args.cases)

    if not cases:
        print("No test cases found.")
        sys.exit(1)

    print(f"Running {len(cases)} eval case(s) against {args.base_url}\n")

    results = []
    with httpx.Client() as client:
        for case in cases:
            result = run_case(client, args.base_url, case, repo_root)
            results.append(result)
            icon = {"pass": "✓", "fail": "✗", "skipped": "~", "error": "!"}.get(result["status"], "?")
            conf = result["actual"]["confidence"] if result["actual"] else None
            conf_str = f"  confidence: {conf:.3f}" if conf is not None else ""
            print(f"  [{icon}] {result['id']:30s} {result['status']}{conf_str}")
            if result["status"] in ("fail", "error"):
                print(f"       expected: {result['expected']}")
                print(f"       actual:   {result['actual']}")

    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    errors = sum(1 for r in results if r["status"] == "error")
    total_run = passed + failed + errors

    print(f"\nResults: {passed}/{total_run} passed", end="")
    if skipped:
        print(f"  ({skipped} skipped — sample files missing in data/raw/)", end="")
    print()

    scorecard = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "summary": {"total": len(cases), "passed": passed, "failed": failed, "skipped": skipped, "errors": errors},
        "results": results,
    }

    os.makedirs(os.path.join(repo_root, args.output_dir), exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    scorecard_path = os.path.join(repo_root, args.output_dir, f"{date_str}.json")
    with open(scorecard_path, "w") as f:
        json.dump(scorecard, f, indent=2)
    print(f"Scorecard → {scorecard_path}")

    sys.exit(0 if failed == 0 and errors == 0 else 1)


if __name__ == "__main__":
    main()
