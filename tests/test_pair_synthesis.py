# -*- coding: utf-8 -*-
"""P0: the pair-synthesis contract (AI-flavoured input, human target)."""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "training"))

import pair_synthesis as ps  # noqa: E402
from prepare_dataset import (  # noqa: E402
    _write_pair_split,
    collect_synthesized_pairs,
    infer_register,
)

HUMAN = (
    "Nhóm vận hành theo dõi tỷ lệ lỗi trong 30 phút sau mỗi lần phát hành. "
    "Nếu tỷ lệ vượt 2%, người trực ca có thể quay về bản trước. "
    "Bản 3.2.1 phát hành ngày 8/10/2025 và giảm thời gian khởi động 38%. "
    "Nhóm đã ghi lại toàn bộ sự cố trong biên bản."
)


def _cfg(source: Path | str, **syn_overrides) -> dict:
    syn = {
        "dirtying": "rule",
        "max_gold_errors_per_100_words": 1.0,
        "min_ai_hits": 1,
        "length_ratio": [0.8, 1.5],
        "per_doc_max_pairs": 2,
    }
    syn.update(syn_overrides)
    return {
        "dataset": {
            "source_paths": [str(source)],
            "text_column": "text",
            "mode": "synthesize",
            "min_words": 30,
            "max_words": 400,
            "train_ratio": 0.5,
            "dedupe": True,
        },
        "synthesize": syn,
    }


# ---------------------------------------------------------------- dirtying


def test_rule_dirtying_preserves_fact_tokens() -> None:
    dirty = ps.dirty_rule_based(HUMAN, random.Random(0))

    assert ps.fact_tokens(dirty) == ps.fact_tokens(HUMAN)


def test_rule_dirtying_keeps_date_and_numbers_verbatim() -> None:
    dirty = ps.dirty_rule_based(HUMAN, random.Random(1))

    assert "8/10/2025" in dirty
    assert "38%" in dirty
    assert "2%" in dirty


def test_rule_dirtying_injects_catalog_connectors() -> None:
    dirty = ps.dirty_rule_based(HUMAN, random.Random(2))

    assert ps.connector_hits(dirty) >= 1
    assert ps.check_pair(dirty, HUMAN, length_ratio_bounds=(0.5, 2.0)) is None


def test_rule_dirtying_is_deterministic_for_a_seed() -> None:
    assert ps.dirty_rule_based(HUMAN, random.Random(7)) == ps.dirty_rule_based(
        HUMAN, random.Random(7)
    )


def test_rule_dirtying_skips_structural_lines() -> None:
    dirty = ps.dirty_rule_based("# Tiêu đề\n\nMột câu ngắn.", random.Random(0))

    assert dirty.startswith("# Tiêu đề")


def test_lower_first_protects_proper_nouns_and_acronyms() -> None:
    assert ps._lower_first("Hà Nội có mưa lớn.") == "Hà Nội có mưa lớn."
    assert ps._lower_first("UBND tỉnh đã họp.") == "UBND tỉnh đã họp."
    # Tên riêng: không có bằng chứng từ này tồn tại ở dạng thường → giữ nguyên.
    assert ps._lower_first("Liên ngồi yên lặng.", "Liên ngồi yên lặng bên quầy.") == (
        "Liên ngồi yên lặng."
    )
    # Danh từ chung: xuất hiện dạng thường trong đoạn → hạ chữ đầu.
    assert ps._lower_first("Tiếng trống vang.", "từng tiếng một vang xa.") == (
        "tiếng trống vang."
    )
    # Không có ngữ cảnh: bảo thủ, giữ nguyên.
    assert ps._lower_first("Nhóm đã họp.") == "Nhóm đã họp."


# ---------------------------------------------------------------- acceptance


def test_check_pair_rejects_dropped_number() -> None:
    reason = ps.check_pair("Nhóm giảm thời gian khởi động đáng kể.", HUMAN)

    assert reason is not None
    assert reason.startswith("fact_drift")


def test_check_pair_rejects_added_number() -> None:
    reason = ps.check_pair("Bên cạnh đó, " + HUMAN + " Tỷ lệ đạt 99%.", HUMAN)

    assert reason is not None
    assert reason.startswith("fact_drift")


def test_check_pair_accepts_separator_style_change() -> None:
    human = "Doanh thu đạt 1.850 tỷ đồng trong quý."
    ai = "Tổng thể, doanh thu đạt 1850 tỷ đồng trong quý."

    assert ps.check_pair(ai, human, length_ratio_bounds=(0.5, 2.0)) is None


def test_check_pair_rejects_identical_sides() -> None:
    assert ps.check_pair(HUMAN, HUMAN) == "identical"


def test_check_pair_rejects_length_outlier() -> None:
    ai = "Bên cạnh đó, " + HUMAN + " " + ("Ngoài ra, nội dung thêm. " * 20)

    reason = ps.check_pair(ai, HUMAN, length_ratio_bounds=(0.9, 1.1))
    assert reason is not None
    assert reason.startswith("length_ratio")


def test_check_pair_requires_ai_flavour() -> None:
    clean_input = HUMAN  # no connector at all

    assert ps.check_pair(clean_input, HUMAN) == "identical"
    assert ps.check_pair(clean_input + " Thêm.", HUMAN).startswith("not_ai_flavoured")


def test_check_pair_can_require_a_lint_hit() -> None:
    ai = ps.dirty_rule_based(HUMAN, random.Random(3))

    reason = ps.check_pair(
        ai, HUMAN, length_ratio_bounds=(0.5, 2.0), lint_fn=lambda _text: [], require_lint_hit=True
    )
    assert reason == "not_ai_flavoured:linter_silent"


# ---------------------------------------------------------------- measurement


def test_overlap_metrics_are_sane() -> None:
    assert ps.word_ngram_overlap(HUMAN, HUMAN) == 1.0
    assert ps.word_ngram_overlap("một hai ba bốn năm sáu", "bảy tám chín mười") == 0.0
    assert ps.longest_common_substring_ratio("abcdef", "abcdef") == 1.0


def test_fact_tokens_match_the_backend_guard() -> None:
    seed = ps._fallback_fact_tokens
    cases = [
        HUMAN,
        "Ngày 22/10/2025, 1.250 hộ dân sơ tán; lượng mưa 480 mm.",
        "Không có số liệu nào.",
        "1.850 tỷ và 1850 tỷ và 1,850 tỷ",
    ]
    for text in cases:
        assert seed(text) == ps.fact_tokens(text), text


# ---------------------------------------------------------------- dataset build


def _write_corpus(tmp_path: Path, docs: int, paragraphs: int = 2) -> Path:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    paragraph = (
        "Nhóm theo dõi tỷ lệ lỗi trong ba mươi phút sau mỗi lần phát hành phần mềm. "
        "Nếu tỷ lệ vượt hai phần trăm, người trực ca có thể quay về bản trước đó. "
        "Bản phát hành ghi nhận đầy đủ thời điểm và người phụ trách kiểm tra."
    )
    for index in range(docs):
        body = "\n\n".join([f"{paragraph} Đợt {index}." for _ in range(paragraphs)])
        (corpus / f"news_doc{index}.txt").write_text(body, encoding="utf-8")
    return corpus


def test_synthesize_pairs_are_accepted_and_infer_register(tmp_path: Path) -> None:
    corpus = _write_corpus(tmp_path, docs=2)

    pairs, rejections = collect_synthesized_pairs(_cfg(corpus), lint_fn=None)

    assert pairs, [r.reason for r in rejections]
    for pair in pairs:
        assert ps.fact_tokens(pair.user_text) == ps.fact_tokens(pair.assistant_text)
        assert pair.register == "news"
        assert pair.doc_id.startswith("news_doc")


def test_gold_filter_rejects_noisy_human_chunks(tmp_path: Path) -> None:
    corpus = _write_corpus(tmp_path, docs=1)

    pairs, rejections = collect_synthesized_pairs(
        _cfg(corpus, max_gold_errors_per_100_words=0.0),
        lint_fn=lambda _text: [{"finding_type": "error"}],
    )

    assert pairs == []
    assert {r.reason for r in rejections} == {"gold_noisy"}


def test_gold_filter_ignores_heuristic_findings(tmp_path: Path) -> None:
    """Literature trips sentence-length heuristics constantly; only errors count."""
    corpus = _write_corpus(tmp_path, docs=1)

    pairs, rejections = collect_synthesized_pairs(
        _cfg(corpus, max_gold_errors_per_100_words=0.0),
        lint_fn=lambda _text: [{"finding_type": "heuristic"}],
    )

    assert pairs, [r.reason for r in rejections]


def test_document_split_keeps_documents_whole(tmp_path: Path) -> None:
    corpus = _write_corpus(tmp_path, docs=6)
    pairs, _ = collect_synthesized_pairs(_cfg(corpus), lint_fn=None)

    train, val = ps.split_by_document(pairs, train_ratio=0.5, seed=42)

    train_docs = {pair.doc_id for pair in train}
    val_docs = {pair.doc_id for pair in val}
    assert train and val
    assert train_docs.isdisjoint(val_docs)
    assert train_docs | val_docs == {pair.doc_id for pair in pairs}


def test_written_jsonl_matches_the_frozen_prompt_shape(tmp_path: Path) -> None:
    corpus = _write_corpus(tmp_path, docs=1)
    pairs, _ = collect_synthesized_pairs(_cfg(corpus), lint_fn=None)

    out = tmp_path / "train.jsonl"
    _write_pair_split(out, pairs)

    import json

    row = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert [m["role"] for m in row["messages"]] == ["system", "user", "assistant"]
    assert "<ORIGINAL>" in row["messages"][1]["content"]
    assert row["messages"][2]["content"] in {
        pair.assistant_text for pair in pairs
    }


def test_manifest_counts_and_reasons(tmp_path: Path) -> None:
    corpus = _write_corpus(tmp_path, docs=2)
    pairs, rejections = collect_synthesized_pairs(_cfg(corpus), lint_fn=None)

    manifest = ps.pair_manifest(pairs, rejections, extra={"mode": "synthesize"})

    assert manifest["pairs"] == len(pairs)
    assert manifest["documents"] == len({p.doc_id for p in pairs})
    assert manifest["mode"] == "synthesize"
    assert isinstance(manifest["rejection_reasons"], dict)


@pytest.mark.parametrize(
    ("doc_id", "expected"),
    [
        ("sample02_news_flood", "news"),
        ("bao_cao_tai_chinh_q3", "report"),
        ("academic_elearning", "academic"),
        ("blog_travel_hoian", "blog"),
        ("khong_ro_loai", "unknown"),
    ],
)
def test_infer_register(doc_id: str, expected: str) -> None:
    assert infer_register(doc_id) == expected
