"""Label tables for sprint documents (SPR-33): the words scripts match, kept in labels/<locale>.json.

A key is an English, immutable identifier such as "heading.plain_summary"; a label is the text a document shows for
that key in one locale. Every locale file carries the same key set. A value is one string, or a list of strings
(alternates; list position i of one locale lines up with position i of every other locale; position 0 is the
primary label that translate() and label() produce).

Matching accepts the labels of every shipped locale (a label is resolved to its key whichever table it came from):

    key_of(text)             whole text -> key, or None
    exact(text, key)         whole text equals a label of the key
    contains(text, key)      Vietnamese: substring (today's check.py semantics); other locales: whole text only
    startswith(text, key)    Vietnamese: prefix; other locales: prefix ending at a word boundary
    alternation(key)         regex alternation of every label of the key, every label passed through re.escape

"Whole text" means: leading numbering ("2.1"), surrounding asterisks, a trailing colon, letter case and runs of
blanks are ignored; nothing else (GC1: an English label never matches as a bare substring). A text that is exactly a
label of another key in a non-substring locale is never matched by contains/startswith of a different key, so the
Vietnamese label "Review" cannot hijack the English heading "Review focus". Known limit: contains() on a longer
English text can still hit an ASCII-only Vietnamese label as a substring; callers match headings and cells, not
prose, with the English locale.

translate(text, locale) and scan(text) share one walker. It skips front matter, code fences, HTML comments and table
data rows, and looks only at headings (numbering kept), table header rows and bold field labels ("**Label:**" at any
place of a prose line). A heading that is not a label as a whole is also tried as "left - right" around the first
spaced em dash, which covers "Placeholder - Plan (PLAN)". translate() rewrites only matched labels, so unknown text
stays byte for byte; a label already in the target locale is left alone, so translating twice changes nothing. A label
whose first letter is lowercase in the source keeps that lowercase first letter, so vi -> en -> vi is byte-identical.
Only the groups heading, column and field are walked; level, quote, phrase and status keys are for matching code.

Uniqueness is per domain: no two keys of the labels domain (heading, column, field) or of the words domain (level,
quote, phrase, status) share a label inside a locale or across locales. One Vietnamese word is deliberately shared
between the two domains (column.proposal and status.proposed, both written as the same word, the second being the
existing index.py output); key_of() without groups reports None for it, key_of(text, groups=domain_of(key)) resolves it.

Importing this module reads nothing; tables are read on first use. Locale names are validated against the files in
labels/ (two or three lowercase letters), so "../x" is rejected before any path is built.

Vietnamese-only residual (deliberately NOT in the tables; check.py and _agile_rules.py keep matching these as they do
today, and English documents carry them in Vietnamese until a later sprint):
  - old-scale words of check.py: OLD_VI (cao, trung binh, thap, nghiem trong, quan trong, nhe, with diacritics),
    OLD_CELL, OLD_CELL_UPPER and the OLD_FIELD / OLD_SRC_* regexes; they flag a retired scale, they are not labels;
    how English Note and Blocker interact with the old scale is decided in TK3 (GC2).
  - the legacy bulletin alias, the second entry of check.py BULLETIN_HEADINGS (kept for records written before the rename).
  - grant words of _agile_rules.py: AGILE_PREFIX, AGILE_GATES_BOTH, the level words and the dead branch/push constants.
  - rule messages printed by check.py and the summary words of its exit lines (output only), console lines of init.py.
  - prose, HTML comment hints, example rows and example headings of the templates; status words used as table data
    (Chua chay, Dang lam, Dat, Khong dat, Khong ap dung) and the cell separator used in decision-log tables.
"""

from __future__ import annotations

import functools
import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, Iterator, List, NamedTuple, Optional, Tuple

DEFAULT_LOCALE = "vi"
SUBSTRING_LOCALES = ("vi",)  # locales whose labels keep substring matching in contains()/startswith()
WALK_GROUPS = ("heading", "column", "field")
LABEL_GROUPS = WALK_GROUPS  # domain 1: labels that structure a document
WORD_GROUPS = ("level", "quote", "phrase", "status")  # domain 2: words that appear as data or output
LABELS_DIR = Path(__file__).resolve().parent.parent / "labels"

_LOCALE_NAME = re.compile(r"[a-z]{2,3}")
_NUMBERING = re.compile(r"^[0-9]+(?:\.[0-9]+)*\.?\s+")
_HEADING = re.compile(r"^(#{1,6})([ \t]+)(\S.*?)[ \t]*$")
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_FENCE_CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})\s*$")
_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?\s*$")
_BOLD = re.compile(r"\*\*([^*\n]+?)\*\*(:?)")
_CODE_SPAN = re.compile(r"`[^`\n]*`")
_EM_DASH = " — "

Table = Dict[str, Tuple[str, ...]]


class LabelError(ValueError):
    """A locale is not shipped, or a label table is missing, unreadable or malformed."""


class Span(NamedTuple):
    """One machine-read label found by scan(): where it is and what it resolves to."""

    kind: str  # "heading" | "header" | "field"
    line: int  # 0-based line index in text.split("\n")
    start: int  # character offsets of the label inside that line (line ending excluded)
    end: int
    text: str
    key: Optional[str]  # None when the text is not a label of any walked group
    entries: Tuple[Tuple[str, int], ...]  # (locale, alternate position) for every table that holds the label


class _Entry(NamedTuple):
    key: str
    locale: str
    alt: int


# --- loading --------------------------------------------------------------------------------------------

_TABLES: Dict[Tuple[str, str], Table] = {}
_INDEX: Dict[str, List[_Entry]] = {}  # folded label -> entries, built for LABELS_DIR on first use
_SHIPPED: List[Tuple[str, ...]] = []  # one-element cache for the shipped locales of LABELS_DIR
_BY_KEY: Dict[str, List[Tuple[str, str]]] = {}  # key -> (locale, label), built for LABELS_DIR on first use


def shipped(labels_dir=None) -> Tuple[str, ...]:
    """Locales that have a labels/<locale>.json file, sorted. The default directory is listed once per process."""
    if labels_dir is None and _SHIPPED:
        return _SHIPPED[0]
    directory = Path(labels_dir) if labels_dir is not None else LABELS_DIR
    try:
        names = [p.stem for p in directory.iterdir() if p.suffix == ".json" and p.is_file()]
    except OSError:
        return ()
    found = tuple(sorted(n for n in names if _LOCALE_NAME.fullmatch(n)))
    if labels_dir is None:
        _SHIPPED.append(found)
    return found


def valid_locale(locale, labels_dir=None) -> bool:
    return isinstance(locale, str) and _LOCALE_NAME.fullmatch(locale) is not None and locale in shipped(labels_dir)


def require_locale(locale, labels_dir=None) -> str:
    if not valid_locale(locale, labels_dir):
        raise LabelError(f"locale {str(locale)[:40]!r} is not shipped (shipped: {', '.join(shipped(labels_dir)) or 'none'})")
    return locale


def _no_duplicates(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise LabelError(f"duplicate key {key!r}")
        seen[key] = value
    return seen


def parse_table(data, source: str = "labels") -> Table:
    """Validate a parsed label file and return key -> tuple of labels. Raises LabelError."""
    if not isinstance(data, dict) or not data:
        raise LabelError(f"{source}: expected a non-empty JSON object")
    table: Table = {}
    for key, value in data.items():
        if not isinstance(key, str) or not key.strip():
            raise LabelError(f"{source}: empty key")
        labels = [value] if isinstance(value, str) else value
        if not isinstance(labels, list) or not labels:
            raise LabelError(f"{source}: {key}: expected a string or a non-empty list of strings")
        for lab in labels:
            if not isinstance(lab, str) or not lab.strip():
                raise LabelError(f"{source}: {key}: labels must be non-empty strings")
        table[key] = tuple(labels)
    return table


def load(locale, labels_dir=None) -> Table:
    """The table of one locale: key -> tuple of labels (primary first). Cached per directory."""
    require_locale(locale, labels_dir)
    directory = Path(labels_dir) if labels_dir is not None else LABELS_DIR
    cache_key = (str(directory), locale)
    if cache_key not in _TABLES:
        path = directory / f"{locale}.json"
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise LabelError(f"{path.name}: cannot read ({exc.__class__.__name__})") from exc
        if raw.startswith(b"\xef\xbb\xbf"):
            raise LabelError(f"{path.name}: byte order mark not allowed")
        try:
            data = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates)
        except (UnicodeDecodeError, ValueError) as exc:
            raise LabelError(f"{path.name}: not valid UTF-8 JSON ({exc.__class__.__name__})") from exc
        _TABLES[cache_key] = parse_table(data, path.name)
    return _TABLES[cache_key]


def alternates(key: str, locale, labels_dir=None) -> Tuple[str, ...]:
    table = load(locale, labels_dir)
    if key not in table:
        raise LabelError(f"unknown label key {str(key)[:60]!r}")
    return table[key]


def label(key: str, locale, labels_dir=None) -> str:
    """The primary label of a key in a locale."""
    return alternates(key, locale, labels_dir)[0]


def labels_of(key: str) -> Dict[str, Tuple[str, ...]]:
    """Every label of a key in every shipped locale: {locale: labels}."""
    found = {loc: load(loc)[key] for loc in shipped() if key in load(loc)}
    if not found:
        raise LabelError(f"unknown label key {str(key)[:60]!r}")
    return found


# --- matching -------------------------------------------------------------------------------------------


@functools.lru_cache(maxsize=8192)
def _squash(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split()).casefold()


@functools.lru_cache(maxsize=8192)
def _fold(text: str) -> str:
    """Comparison form of a whole label or cell: numbering, surrounding asterisks, trailing colon and case ignored."""
    s = " ".join(unicodedata.normalize("NFC", text).split()).strip("*").strip()
    s = _NUMBERING.sub("", s)
    if s.endswith(":"):
        s = s[:-1].rstrip()
    return s.casefold()


def _index() -> Dict[str, List[_Entry]]:
    if not _INDEX:
        for locale in shipped():
            for key, labs in load(locale).items():
                for alt, lab in enumerate(labs):
                    _INDEX.setdefault(_fold(lab), []).append(_Entry(key, locale, alt))
    return _INDEX


def _entries_of(text: str, locales=None) -> List[_Entry]:
    return [e for e in _index().get(_fold(text), []) if locales is None or e.locale in locales]


def domain_of(key: str) -> Tuple[str, ...]:
    """The group names of the domain a key belongs to (labels or words)."""
    return LABEL_GROUPS if key.split(".", 1)[0] in LABEL_GROUPS else WORD_GROUPS


def key_of(text: str, locales=None, groups=None) -> Optional[str]:
    """The key whose label equals the whole text (see module docstring), or None when none or several match.
    groups limits the search to key groups, for example a domain (see domain_of)."""
    keys = {e.key for e in _entries_of(text, locales) if groups is None or e.key.split(".", 1)[0] in groups}
    return next(iter(keys)) if len(keys) == 1 else None


def exact(text: str, key: str, locales=None) -> bool:
    return any(e.key == key for e in _entries_of(text, locales))


def _key_labels(key: str, locales) -> List[Tuple[str, str]]:
    if not _BY_KEY:
        for loc in shipped():
            for k, labs in load(loc).items():
                _BY_KEY.setdefault(k, []).extend((loc, lab) for lab in labs)
    return [(loc, lab) for loc, lab in _BY_KEY.get(key, ()) if locales is None or loc in locales]


def _hijacked(text: str, key: str) -> bool:
    """True when the text is exactly a label of a different key in a locale that matches anchored."""
    others = tuple(loc for loc in shipped() if loc not in SUBSTRING_LOCALES)
    winner = key_of(text, others) if others else None
    return winner is not None and winner != key


def contains(text: str, key: str, locales=None) -> bool:
    entries = _key_labels(key, locales)
    if not entries or _hijacked(text, key):
        return False
    squashed = _squash(text)
    for loc, lab in entries:
        if loc in SUBSTRING_LOCALES:
            if _squash(lab) in squashed:
                return True
        elif _fold(text) == _fold(lab):
            return True
    return False


def startswith(text: str, key: str, tail: str = "", locales=None) -> bool:
    """The text begins with a label of the key followed by tail (for example ":")."""
    entries = _key_labels(key, locales)
    if not entries or _hijacked(text, key):
        return False
    squashed = _squash(text)
    for loc, lab in entries:
        target = _squash(lab) + tail.casefold()
        if not squashed.startswith(target):
            continue
        rest = squashed[len(target):]
        if loc in SUBSTRING_LOCALES or rest == "" or not rest[0].isalnum() or target.endswith(":"):
            return True
    return False


def alternation(key: str, locales=None) -> str:
    """Regex source matching any label of the key; every label goes through re.escape. Empty for an unknown key."""
    labs = sorted({lab for _, lab in _key_labels(key, locales)}, key=lambda s: (-len(s), s))
    if not labs:
        return ""
    escaped = [re.escape(lab) for lab in labs]
    return escaped[0] if len(escaped) == 1 else "(?:" + "|".join(escaped) + ")"


# --- the shared walker ----------------------------------------------------------------------------------


def _mask_comments(body: str, in_comment: bool) -> Tuple[str, bool]:
    """Blank out HTML comment text (offsets stay valid); in_comment carries a comment across lines."""
    out: List[str] = []
    i = 0
    while i < len(body):
        if in_comment:
            j = body.find("-->", i)
            if j == -1:
                out.append(" " * (len(body) - i))
                i = len(body)
            else:
                out.append(" " * (j + 3 - i))
                i = j + 3
                in_comment = False
        else:
            j = body.find("<!--", i)
            if j == -1:
                out.append(body[i:])
                i = len(body)
            else:
                out.append(body[i:j] + "    ")
                i = j + 4
                in_comment = True
    return "".join(out), in_comment


def _trim_span(s: str, a: int, b: int) -> Tuple[int, int]:
    """Shrink [a, b) past blanks, surrounding asterisks and a trailing colon."""
    while a < b and (s[a].isspace() or s[a] == "*"):
        a += 1
    while b > a and (s[b - 1].isspace() or s[b - 1] in "*:"):
        b -= 1
    return a, b


def _cells(s: str) -> Iterator[Tuple[int, int]]:
    start = s.find("|") + 1
    seg = start
    for i in range(start, len(s) + 1):
        if i == len(s) or (s[i] == "|" and s[i - 1] != "\\"):
            yield seg, i
            seg = i + 1


def _candidates(text: str) -> Iterator[Tuple[str, int, int, int]]:
    """(kind, line, start, end) of every place a label may stand; the single walk behind scan() and translate()."""
    lines = text.split("\n")
    first = 0
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                first = j + 1
                break
    fence: Optional[Tuple[str, int]] = None
    in_comment = False
    prev_row = False
    for idx in range(first, len(lines)):
        body = lines[idx][:-1] if lines[idx].endswith("\r") else lines[idx]
        if fence is not None:
            m = _FENCE_CLOSE.match(body)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1]:
                fence = None
            continue
        visible, in_comment = _mask_comments(body, in_comment)
        if not visible.strip():
            prev_row = False
            continue
        m = _FENCE_OPEN.match(visible)
        if m:
            fence = (m.group(1)[0], len(m.group(1)))
            prev_row = False
            continue
        if visible.lstrip().startswith("|"):
            if not prev_row:
                following = lines[idx + 1].rstrip("\r") if idx + 1 < len(lines) else ""
                if _SEPARATOR.match(following):
                    for a, b in _cells(visible):
                        a, b = _trim_span(visible, a, b)
                        if a < b:
                            yield "header", idx, a, b
            prev_row = True
            continue
        prev_row = False
        hm = _HEADING.match(visible)
        if hm:
            yield "heading", idx, hm.start(3), hm.end(3)
            continue
        code_masked = _CODE_SPAN.sub(lambda mo: " " * len(mo.group(0)), visible)
        for bm in _BOLD.finditer(code_masked):
            inner = bm.group(1)
            if not (inner.rstrip().endswith(":") or bm.group(2) == ":"):
                continue
            a, b = _trim_span(visible, bm.start(1), bm.end(1))
            if a < b:
                yield "field", idx, a, b


def _make_span(kind: str, body: str, idx: int, a: int, b: int) -> Span:
    text = body[a:b]
    found = [e for e in _entries_of(text) if e.key.split(".", 1)[0] in WALK_GROUPS]
    keys = {e.key for e in found}
    if len(keys) != 1:
        return Span(kind, idx, a, b, text, None, ())
    entries = tuple(sorted({(e.locale, e.alt) for e in found}))
    return Span(kind, idx, a, b, text, next(iter(keys)), entries)


def _heading_spans(body: str, idx: int, a: int, b: int) -> List[Span]:
    nm = _NUMBERING.match(body[a:b])
    if nm:
        a += nm.end()
    a, b = _trim_span(body, a, b)
    if a >= b:
        return []
    whole = _make_span("heading", body, idx, a, b)
    if whole.key is not None:
        return [whole]
    sep = body.find(_EM_DASH, a, b)
    if sep == -1:
        return [whole]
    parts = []
    for lo, hi in ((a, sep), (sep + len(_EM_DASH), b)):
        lo, hi = _trim_span(body, lo, hi)
        if lo < hi:
            parts.append(_make_span("heading", body, idx, lo, hi))
    return parts if any(p.key is not None for p in parts) else [whole]


def scan(text: str, all_spans: bool = False) -> List[Span]:
    """Machine-read label spans of a document, in reading order; all_spans also lists candidates that match no label."""
    lines = text.split("\n")
    spans: List[Span] = []
    for kind, idx, a, b in _candidates(text):
        body = lines[idx]
        if kind == "heading":
            spans.extend(_heading_spans(body, idx, a, b))
        else:
            spans.append(_make_span(kind, body, idx, a, b))
    spans.sort(key=lambda s: (s.line, s.start))
    return spans if all_spans else [s for s in spans if s.key is not None]


def locales_in(text: str) -> Tuple[str, ...]:
    """Locales that own at least one label of the document alone; labels shared by several locales say nothing."""
    found = set()
    for span in scan(text):
        owners = {loc for loc, _ in span.entries}
        if len(owners) == 1:
            found |= owners
    return tuple(sorted(found))


def _render(span: Span, locale: str) -> Optional[str]:
    if span.key is None or any(loc == locale for loc, _ in span.entries):
        return None
    alt = span.entries[0][1]
    target = alternates(span.key, locale)
    new = target[alt] if alt < len(target) else target[0]
    if span.text[:1].islower() and new[:1].isupper():
        new = new[:1].lower() + new[1:]
    return new


def translate(text: str, locale) -> str:
    """Rewrite the machine-read labels of a document into the locale (numbering and everything else untouched)."""
    require_locale(locale)
    lines = text.split("\n")
    edits: Dict[int, List[Tuple[int, int, str]]] = {}
    for span in scan(text):
        new = _render(span, locale)
        if new is not None and new != span.text:
            edits.setdefault(span.line, []).append((span.start, span.end, new))
    for idx, items in edits.items():
        line = lines[idx]
        for start, end, new in sorted(items, reverse=True):
            line = line[:start] + new + line[end:]
        lines[idx] = line
    return "\n".join(lines)
