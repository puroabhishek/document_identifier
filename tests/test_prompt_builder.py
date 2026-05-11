from app.services.prompt_builder import ClassLabel, PromptBuilder


def _make_builder(examples: list[str] | None = None) -> PromptBuilder:
    pb = PromptBuilder()
    pb.set_class_labels([
        ClassLabel(
            label="bank_statement",
            name="Bank Statement",
            description="Issued by a bank showing transactions.",
            examples=examples or [],
        ),
        ClassLabel(
            label="passport",
            name="Passport",
            description="International travel document.",
            examples=[],
        ),
    ])
    return pb


def test_prompt_contains_class_labels():
    pb = _make_builder()
    prompt = pb.build_classify_prompt("some document text")
    assert "bank_statement" in prompt
    assert "Bank Statement" in prompt
    assert "passport" in prompt


def test_prompt_contains_document_text():
    pb = _make_builder()
    prompt = pb.build_classify_prompt("IBAN: QA57 COMM 0000")
    assert "IBAN: QA57 COMM 0000" in prompt


def test_prompt_truncates_long_document_text():
    pb = _make_builder()
    long_text = "x" * 10000
    prompt = pb.build_classify_prompt(long_text)
    # 1500 char truncation means the full long_text is not present
    assert "x" * 1501 not in prompt


def test_prompt_includes_few_shot_examples():
    pb = _make_builder(examples=["Example bank statement text here"])
    prompt = pb.build_classify_prompt("doc")
    assert "Example bank statement text here" in prompt
    assert "FEW-SHOT EXAMPLES" in prompt


def test_prompt_no_examples_section_when_empty():
    pb = _make_builder(examples=[])
    prompt = pb.build_classify_prompt("doc")
    assert "FEW-SHOT EXAMPLES" not in prompt


def test_prompt_uses_first_example_only():
    pb = PromptBuilder()
    pb.set_class_labels([
        ClassLabel(
            label="bank_statement",
            name="Bank Statement",
            description="",
            examples=["example one", "example two", "example three"],
        )
    ])
    prompt = pb.build_classify_prompt("doc")
    assert "example one" in prompt
    assert "example two" not in prompt
    assert "example three" not in prompt


def test_set_class_labels_replaces_previous():
    pb = PromptBuilder()
    pb.set_class_labels([ClassLabel("old_label", "Old", "", [])])
    pb.set_class_labels([ClassLabel("new_label", "New", "", [])])
    prompt = pb.build_classify_prompt("doc")
    assert "new_label" in prompt
    assert "old_label" not in prompt
