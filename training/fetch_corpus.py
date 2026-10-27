# -*- coding: utf-8 -*-
"""Collect human-written Vietnamese prose from Wikisource (PD / CC BY-SA).

Why Wikisource: it hosts public-domain and freely licensed Vietnamese texts,
returns real sentences (not listicles), and every page carries a stable
provenance record — which is what makes the resulting dataset auditable.

The script is deliberately conservative:

* only the main namespace (actual texts, not categories/templates),
* random sampling with resume state, so repeated runs extend the corpus
  instead of re-downloading it,
* one request per ``--sleep`` seconds and a descriptive User-Agent,
* length/sentence/Vietnamese-script filters, so poetry fragments, tables and
  stray English pages never reach ``training/data/raw``.

Every accepted page is written as one ``.txt`` (one document = one split unit)
plus a line in ``sources.jsonl`` with title, page id, URL and license note.

Usage:
    python training/fetch_corpus.py --max-pages 800
    python training/fetch_corpus.py --pages "Truyện ngắn" --max-pages 20
    python training/fetch_corpus.py --out training/data/raw --min-words 200
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://vi.wikisource.org/w/api.php"
USER_AGENT = (
    "vietnamese-humanizer-corpus/0.5 "
    "(training data collection; https://github.com/datnguyentien2006/vietnamese-humanize)"
)
# Họ wiki Wikimedia đều dùng chung MediaWiki API + giấy phép CC BY-SA 4.0/PD:
# cùng một script lấy được văn người ở register khác nhau (travel, tin, giáo khoa).
LICENSE_NOTES = {
    "vi.wikisource.org": "Wikisource tiếng Việt — public domain hoặc CC BY-SA 4.0",
    "vi.wikivoyage.org": "Wikivoyage tiếng Việt — CC BY-SA 4.0",
    "vi.wikibooks.org": "Wikibooks tiếng Việt — CC BY-SA 4.0",
    "vi.wikinews.org": "Wikinews tiếng Việt — CC BY-SA 4.0",
}
LICENSE_NOTE = LICENSE_NOTES["vi.wikisource.org"]

_VI_LETTERS = re.compile(r"[A-Za-zÀ-ỹĐđ]")
_DIACRITIC_LETTERS = re.compile(
    r"[ÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ"
    r"àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđĐ]"
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_CATEGORY_LINE = re.compile(r"^(Thể loại|Category):.*$", re.MULTILINE)
# Wikisource scans of pre-1954 books keep a space before punctuation ("nay ,").
# That is a typographic convention, not a defect: normalise it so the model
# never learns it as prose.
_SPACE_BEFORE_PUNCT = re.compile(r"[ \t]+([,.!?;:])[ \t]*")

# Vietnamese legal/administrative texts dominate the main namespace and are the
# one register this project must NOT rewrite mechanically (see
# skills/humanizer-vi/references/registers.md). Skip them by title and by shape.
_LEGAL_TITLE = re.compile(
    r"^(Luật|Bộ luật|Nghị định|Thông tư|Thông tư liên tịch|Quyết định|Pháp lệnh|"
    r"Hiến pháp|Nghị quyết|Công ước|Chỉ thị|Sắc lệnh|Hiệp định|Quy định|Báo cáo)\b",
    flags=re.IGNORECASE,
)
_LEGAL_ARTICLE = re.compile(r"\bĐiều \d+[.\s]", flags=re.UNICODE)

LITERATURE_CATEGORIES = (
    "Truyện ngắn Việt Nam",
    "Tiểu thuyết Việt Nam",
    "Truyện ngắn",
    "Truyện Việt Nam",
    "Truyện cười Việt Nam",
)


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------


def api_get(params: dict[str, str], *, timeout: float = 30.0) -> dict:
    query = urllib.parse.urlencode({"format": "json", "formatversion": "2", **params})
    request = urllib.request.Request(
        f"{API}?{query}", headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def random_titles(namespace: int, limit: int) -> list[str]:
    data = api_get(
        {
            "action": "query",
            "list": "random",
            "rnnamespace": str(namespace),
            "rnlimit": str(min(limit, 20)),
        }
    )
    return [item["title"] for item in data.get("query", {}).get("random", [])]


def fetch_extracts(titles: list[str]) -> dict[str, str]:
    """Plain-text extraction for up to 10 titles; empty dict when unsupported."""
    data = api_get(
        {
            "action": "query",
            "prop": "extracts",
            "explaintext": "1",
            "exsectionformat": "plain",
            "titles": "|".join(titles),
        }
    )
    pages = data.get("query", {}).get("pages", [])
    return {
        page["title"]: page["extract"]
        for page in pages
        if page.get("extract") and not page.get("missing")
    }


def fetch_wikitext(titles: list[str]) -> dict[str, str]:
    data = api_get(
        {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": "|".join(titles),
        }
    )
    out: dict[str, str] = {}
    for page in data.get("query", {}).get("pages", []):
        revisions = page.get("revisions") or []
        if not revisions:
            continue
        content = (revisions[0].get("slots", {}).get("main", {}) or {}).get("content")
        if content:
            out[page["title"]] = strip_wikitext(content)
    return out


# --------------------------------------------------------------------------
# Cleaning / filtering
# --------------------------------------------------------------------------


METADATA_TEMPLATES = frozenset(
    {
        "đầu đề",
        "chú thích cuối trang",
        "chú thích đầu trang",
        "bản quyền",
        "giấy phép",
        "thông tin",
        "sơ khai",
        "thiếu nguồn",
    }
)


def _template_name(line: str) -> str | None:
    match = re.search(r"\{\{\s*([^|{}\n]+)", line)
    return match.group(1).strip().lower() if match else None


def strip_wikitext(text: str) -> str:
    """Turn Wikisource wikitext into plain prose.

    Two things matter here and both were wrong before:

    * Metadata templates (``{{đầu đề…}}``, ``{{chú thích cuối trang}}``) are
      dropped whole.
    * Layout templates are *unwrapped*, not dropped. Wikisource wraps the whole
      article body in ``{{văn|…}}`` — deleting templates deleted the article,
      which is why thousands of real pages were recorded as stubs.
    """
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<ref[^>]*?/>", "", text)
    text = re.sub(r"<ref.*?</ref>", "", text, flags=re.DOTALL)

    kept: list[str] = []
    dropping = False
    for line in text.splitlines():
        if dropping:
            if "}}" in line:
                dropping = False
            continue

        name = _template_name(line)
        if name in METADATA_TEMPLATES:
            after_open = line.split("{{", 1)[1]
            before = line.split("{{", 1)[0].strip()
            if "}}" in after_open:
                # Template closes on the same line: keep only what follows it.
                tail = after_open.split("}}", 1)[1].strip()
                if tail:
                    kept.append(tail)
            else:
                dropping = True
                if before:
                    kept.append(before)
            continue

        line = re.sub(r"\{\{[^|{}\n]*\|", "", line)  # unwrap {{văn|…}}
        line = re.sub(r"\{\{[^{}\n]*\}\}", "", line)
        line = re.sub(r"\}\}", "", line)
        kept.append(line)

    text = "\n".join(kept)
    # Bất kỳ mảnh template nào còn sót lại (tên template lạ, khác chuẩn NFC…)
    # đều không phải văn xuôi: bỏ phần còn lại của dòng đó.
    text = re.sub(r"\{\{[^\n]*", "", text)
    text = re.sub(r"^\s*\}\}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[\[[a-z-]{2,5}:[^\]]*\]\]", "", text)  # interwiki
    text = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[https?://[^\]]*\]", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"'{2,}", "", text)
    text = re.sub(r"^=+\s*(.*?)\s*=+$", r"\1", text, flags=re.MULTILINE)
    text = re.sub(r"^[*#:]+\s*", "", text, flags=re.MULTILINE)
    # Template parameters left behind by unwrapping ("canh lề=right"): short
    # lines with an '=' sign carry no prose.
    text = "\n".join(
        "" if ("=" in line and len(line.strip()) < 120 and " " not in line.strip().split("=")[0])
        else line
        for line in text.splitlines()
    )
    text = re.sub(r"^\s*\|.*$", "", text, flags=re.MULTILINE)
    # Page-number artefacts from scans ("50%", "12") standing alone on a line.
    text = re.sub(r"^\s*\d{1,4}\s*%?\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_metadata(text: str) -> str:
    """Drop Wikisource category lines and normalise old typography."""
    text = _CATEGORY_LINE.sub("", text)
    text = _SPACE_BEFORE_PUNCT.sub(r"\1 ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def looks_vietnamese(text: str) -> bool:
    letters = _VI_LETTERS.findall(text)
    if len(letters) < 200:
        return False
    diacritics = _DIACRITIC_LETTERS.findall(text)
    return len(diacritics) / len(letters) >= 0.02


def _category_page(cmtitle: str, limit: int = 500) -> tuple[list[str], list[str]]:
    """One category: (page titles, subcategory titles)."""
    pages: list[str] = []
    subcats: list[str] = []
    continuation: str | None = None
    while len(pages) < limit:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": cmtitle,
            "cmtype": "page|subcat",
            "cmnamespace": "0|14",
            "cmlimit": "50",
        }
        if continuation:
            params["cmcontinue"] = continuation
        data = api_get(params)
        for member in data.get("query", {}).get("categorymembers", []):
            if member.get("ns") == 14:
                subcats.append(member["title"])
            else:
                pages.append(member["title"])
        continuation = data.get("continue", {}).get("cmcontinue")
        if not continuation:
            break
        time.sleep(0.1)
    return pages[:limit], subcats


def category_members(
    category: str, limit: int = 300, depth: int = 1, _visited: set[str] | None = None
) -> list[str]:
    """Page titles in a category, plus one level of subcategories by default.

    Literary categories on Wikisource are mostly containers, so a depth-0 walk
    returns a couple of dozen titles while depth 1 returns hundreds.
    """
    visited = _visited if _visited is not None else set()
    cmtitle = category if category.startswith("Thể loại:") else f"Thể loại:{category}"
    if cmtitle in visited:
        return []
    visited.add(cmtitle)

    pages, subcats = _category_page(cmtitle, limit)
    if depth > 0:
        for subcat in subcats:
            try:
                pages.extend(
                    category_members(subcat, max(limit // 2, 50), depth - 1, visited)
                )
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                print(f"[warn] bỏ qua thể loại con {subcat}: {exc}", file=sys.stderr)
    return pages


def build_literature_pool(
    categories: tuple[str, ...], per_category: int, seed: int
) -> list[str]:
    """Shuffled, de-duplicated page titles from literature categories."""
    pool: list[str] = []
    for category in categories:
        try:
            pool.extend(category_members(category, per_category))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"[warn] không lấy được thể loại {category}: {exc}", file=sys.stderr)
    unique = list(dict.fromkeys(pool))
    random.Random(seed).shuffle(unique)
    return unique


def is_legal(title: str, text: str) -> bool:
    if _LEGAL_TITLE.match(title.strip()):
        return True
    words = max(len(text.split()), 1)
    return len(_LEGAL_ARTICLE.findall(text)) * 1000 / words >= 3


def quality_reasons(text: str, min_words: int, title: str = "") -> list[str]:
    reasons: list[str] = []
    words = text.split()
    if is_legal(title, text):
        reasons.append("legal_document")
    if len(words) < min_words:
        reasons.append(f"too_short:{len(words)}")
    sentences = [part for part in _SENTENCE_SPLIT.split(text) if part.strip()]
    if len(sentences) < 5:
        reasons.append(f"few_sentences:{len(sentences)}")
    if sentences and len(words) / len(sentences) < 4:
        reasons.append("poetry_or_fragments")
    if not looks_vietnamese(text):
        reasons.append("not_vietnamese")
    if text.count("|") > 20:
        reasons.append("table_like")
    return reasons


# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------


def load_state(path: Path) -> tuple[set[str], str | None, set[str]]:
    """(seen, cursor, stubs). Stubs are remembered so they are not re-fetched."""
    if not path.is_file():
        return set(), None, set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.get("seen", [])), data.get("cursor"), set(data.get("stubs", []))
    except Exception:  # noqa: BLE001
        return set(), None, set()


def save_state(
    path: Path, seen: set[str], cursor: str | None = None, stubs: set[str] | None = None
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "seen": sorted(seen),
                "cursor": cursor,
                "stubs": sorted(stubs or set()),
                "updated_at": datetime.now(UTC).isoformat(),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def all_pages(cursor: str | None, limit: int = 200) -> tuple[list[str], str | None]:
    """Enumerate main-namespace titles (non-redirect), with a resume cursor.

    Categories only hold a few hundred titles, which is not enough for a real
    dataset; the whole main namespace is the actual source of prose.
    """
    params = {
        "action": "query",
        "list": "allpages",
        "apnamespace": "0",
        "aplimit": str(min(limit, 500)),
        "apfilterredir": "nonredirects",
    }
    if cursor:
        params["apcontinue"] = cursor
    data = api_get(params)
    pages = [item["title"] for item in data.get("query", {}).get("allpages", [])]
    return pages, data.get("continue", {}).get("apcontinue")


class TitleFeeder:
    """Feed candidate titles: category pool → main namespace → random pages.

    The category pool is tried first because it is prose-heavy. When it runs
    dry the feeder keeps walking ``list=allpages`` from the saved cursor, so
    repeated runs keep adding documents instead of stopping.
    """

    def __init__(
        self,
        pool: list[str],
        cursor: str | None,
        strategy: str,
        seed: int = 42,
        max_wraps: int = 1,
    ) -> None:
        self.pool = list(pool)
        self.cursor = cursor
        self.strategy = strategy
        self.done = False
        self.wraps = 0
        self.max_wraps = max_wraps
        self.rng = random.Random(seed)
        self.source = "categories" if pool else "allpages"

    def take(self, n: int, skip: set[str]) -> list[str]:
        batch = [title for title in self.pool if title not in skip][:n]
        if batch:
            return batch

        if self.strategy == "random":
            self.source = "random"
            return [title for title in random_titles(0, n) if title not in skip]

        self.source = "allpages"
        while not self.done:
            pages, nxt = all_pages(self.cursor, 200)
            self.cursor = nxt
            if not nxt:
                # Reaching the end is normal (a run may start mid-alphabet after
                # a resume). Wrap once so one command still covers the whole
                # namespace instead of silently stopping at "hết nguồn".
                if self.wraps < self.max_wraps:
                    self.wraps += 1
                    self.cursor = None
                    print(
                        f"[info] hết một vòng allpages — quay lại từ đầu (vòng {self.wraps + 1})"
                    )
                else:
                    self.done = True
            candidates = [
                title
                for title in pages
                if title not in skip and not _LEGAL_TITLE.match(title.strip())
            ]
            if candidates:
                return candidates[:n]
        return []


def safe_filename(title: str, page_id: str, prefix: str = "wikisource") -> str:
    slug = re.sub(r"[^\w\-]+", "-", title, flags=re.UNICODE).strip("-")[:60]
    return f"{prefix}_{page_id}_{slug}.txt"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="training/data/raw")
    parser.add_argument(
        "--api-host",
        default="vi.wikisource.org",
        help="host MediaWiki: vi.wikisource.org (mặc định), vi.wikivoyage.org, vi.wikibooks.org, vi.wikinews.org",
    )
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--min-words", type=int, default=150)
    parser.add_argument("--pages", nargs="*", help="titles cụ thể thay vì lấy ngẫu nhiên")
    parser.add_argument(
        "--strategy",
        choices=("literature", "random"),
        default="literature",
        help="literature: lấy theo thể loại văn học (khuyến nghị); random: trang ngẫu nhiên",
    )
    parser.add_argument(
        "--category",
        action="append",
        help="tên thể loại Wikisource (có thể lặp lại); bỏ trống = bộ mặc định văn học VN",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sleep", type=float, default=0.4)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="số trang mỗi request (MediaWiki cho tối đa 50); tăng để quét nhanh hơn",
    )
    parser.add_argument("--max-attempts-factor", type=int, default=6)
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="xóa state.json (bỏ qua danh sách đã thử), dùng khi đổi bộ lọc",
    )
    parser.add_argument(
        "--retry-stubs",
        action="store_true",
        help="thử lại các trang trước đó trả về rỗng (mặc định: bỏ qua để tiết kiệm request)",
    )
    args = parser.parse_args(argv)

    global API, LICENSE_NOTE
    API = f"https://{args.api_host}/w/api.php"
    LICENSE_NOTE = LICENSE_NOTES.get(args.api_host, f"{args.api_host} — CC BY-SA 4.0")
    file_prefix = args.api_host.split(".")[1]  # wikisource | wikivoyage | wikibooks | wikinews

    out_dir = (ROOT / args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path = out_dir / "state.json"
    sources_path = out_dir / "sources.jsonl"
    seen, cursor, stub_titles = load_state(state_path)
    if args.reset_state:
        seen, cursor, stub_titles = set(), None, set()
        print("[info] state đã reset")
    if args.retry_stubs:
        stub_titles = set()
        print("[info] sẽ thử lại các trang rỗng")

    accepted = 0
    attempts = 0
    stubs = 0
    rejections: dict[str, int] = {}
    # Titles already tried *in this process*. Stubs are deliberately not added
    # to `seen` (a later run should retry them with a better extractor), but
    # without this per-run set the category pool would hand back the same stub
    # pages for ever.
    attempted: set[str] = set()
    max_attempts = max(args.max_pages * args.max_attempts_factor, 10)
    # vi.wikisource has TextExtracts effectively broken: prop=extracts returns a
    # 10-char stub ("| Chú thích") instead of the page text, so every page would
    # be rejected as too_short. Raw wikitext + local cleaning is the reliable
    # path here; extracts stays only as a fallback.
    mode = "wikitext"
    explicit_titles = args.pages

    pool: list[str] = []
    if args.strategy == "literature":
        categories = tuple(args.category) if args.category else LITERATURE_CATEGORIES
        print(f"[info] thể loại: {', '.join(categories)}")
        pool = build_literature_pool(categories, 300, args.seed)
        print(f"[info] pool thể loại: {len(pool)} trang (hết thì tự chuyển sang allpages)")

    feeder = TitleFeeder(pool, cursor, args.strategy, args.seed)

    while accepted < args.max_pages and attempts < max_attempts:
        attempts += 1
        try:
            titles = (
                explicit_titles
                if explicit_titles
                else feeder.take(args.batch_size, seen | attempted | stub_titles)
            )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"[error] không gọi được API: {exc}", file=sys.stderr)
            return 1
        explicit_titles = None  # honour an explicit list exactly once
        titles = [
            title
            for title in titles
            if title not in seen and title not in attempted and title not in stub_titles
        ]
        if titles:
            attempted.update(titles)
        if not titles:
            print("[info] đã duyệt hết nguồn trang (thể loại + allpages)")
            break

        try:
            if mode == "wikitext":
                batch = fetch_wikitext(titles)
                if not batch:
                    batch = fetch_extracts(titles)
            else:
                batch = fetch_extracts(titles)
                if not batch:
                    batch = fetch_wikitext(titles)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"[warn] lỗi khi lấy {len(titles)} trang: {exc}", file=sys.stderr)
            time.sleep(args.sleep * 3)
            continue

        time.sleep(args.sleep)

        for title, text in batch.items():
            cleaned = strip_metadata(text)
            # A stub means extraction failed for this page, not that the page is
            # bad: leave it unseen so a later run can retry with another method.
            if len(cleaned) < 50:
                stubs += 1
                stub_titles.add(title)
                continue
            seen.add(title)
            reasons = quality_reasons(cleaned, args.min_words, title)
            if reasons:
                for reason in reasons:
                    key = reason.split(":", 1)[0]
                    rejections[key] = rejections.get(key, 0) + 1
                continue

            page_id = hashlib.md5(title.encode("utf-8")).hexdigest()[:10]
            path = out_dir / safe_filename(title, page_id, file_prefix)
            path.write_text(cleaned + "\n", encoding="utf-8")
            with sources_path.open("a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {
                            "title": title,
                            "page_id": page_id,
                            "url": "https://vi.wikisource.org/wiki/"
                            + urllib.parse.quote(title.replace(" ", "_")),
                            "license": LICENSE_NOTE,
                            "fetched_at": datetime.now(UTC).isoformat(),
                            "words": len(cleaned.split()),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            accepted += 1
            if accepted >= args.max_pages:
                break

        save_state(state_path, seen, feeder.cursor, stub_titles)
        print(f"[{accepted}/{args.max_pages}] đã lấy · lần thử {attempts} · bị loại {sum(rejections.values())} · nguồn {feeder.source}")

    save_state(state_path, seen, feeder.cursor, stub_titles)
    print("")
    print(f"xong: {accepted} tài liệu → {out_dir}")
    print(f"provenance: {sources_path}")
    if stubs:
        print(f"stub (trang rỗng, đã ghi nhớ để không tải lại): {stubs}")
    if rejections:
        print("lý do loại:", json.dumps(rejections, ensure_ascii=False))
    if accepted == 0:
        print("[warn] không lấy được trang nào — kiểm tra mạng hoặc thử --pages", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[dừng] Ctrl+C — tiến độ đã lưu ở state.json, chạy lại để tiếp tục.")
        raise SystemExit(130)
