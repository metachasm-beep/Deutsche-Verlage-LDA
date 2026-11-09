"""
Candidate 4: Corpus Passage & Monograph Work Storage Stream Module.

Deepens Corpus Passage streaming, temporal/Imprint slice filtering, and Monograph Work
base-title deduplication behind a local-substitutable Port & Adapter interface:
- CorpusStoragePort (Protocol)
- ParquetCsvCorpusAdapter (Production adapter over 127 Zstd-19 Parquet shards / CSVs)
- InMemoryCorpusAdapter (Deterministic in-memory adapter for tests & sub-corpus slices)
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re
from typing import Iterable, Iterator, Protocol

import lda_pipeline

_BRACKET_RE = re.compile(r"\[.*?\]")
_YEAR_RE = re.compile(r"(19[789]\d|20[012]\d)")


def normalize_monograph_base_title(raw_title: str | None) -> str:
    """
    Deduplicates multi-chunk Corpus Passages into a single distinct Monograph Work identifier
    by stripping continuation brackets (`[Abschnitt K/N]`, `[Inhaltsverzeichnis: ...]`, etc.).
    """
    cleaned = _BRACKET_RE.sub("", str(raw_title or "")).strip().lower()
    return re.sub(r"\s+", " ", cleaned)


def extract_publication_year(raw_year: str | int | None) -> int | None:
    """Extracts a canonical 4-digit publication year in [1970, 2029] from MARC21 264$c."""
    m = _YEAR_RE.search(str(raw_year or ""))
    return int(m.group(1)) if m else None


def publisher_matches_imprint_filter(row_pub: str | None, filter_pubs: Iterable[str] | None) -> bool:
    """Case-insensitive substring & token-prefix matching between a Corpus Passage Imprint and active Imprint filters."""
    if not filter_pubs:
        return True
    rp = str(row_pub or "").strip().lower()
    if not rp:
        return False
    for fp in filter_pubs:
        f_clean = str(fp or "").strip().lower()
        if not f_clean:
            continue
        if f_clean == rp or f_clean in rp or rp in f_clean:
            return True
    return False


@dataclass(frozen=True)
class CorpusSliceFilter:
    """Immutable sub-corpus conditioning predicate over Year, Decade, and Imprints."""
    year: int | None = None
    decade: int | None = None
    publishers: tuple[str, ...] = ()

    @classmethod
    def from_params(
        cls,
        year: int | None = None,
        decade: int | None = None,
        publishers: Iterable[str] | str | None = None,
    ) -> "CorpusSliceFilter":
        if isinstance(publishers, str):
            pubs = tuple(p.strip() for p in publishers.split(",") if p.strip())
        elif publishers:
            pubs = tuple(str(p).strip() for p in publishers if str(p).strip())
        else:
            pubs = ()
        return cls(
            year=int(year) if year is not None else None,
            decade=int(decade) if decade is not None else None,
            publishers=pubs,
        )

    @property
    def is_unfiltered(self) -> bool:
        return self.year is None and self.decade is None and not self.publishers

    def matches(self, row: dict) -> bool:
        if self.is_unfiltered:
            return True
        if self.year is not None or self.decade is not None:
            yr = extract_publication_year(row.get("year"))
            if yr is None:
                return False
            if self.year is not None and yr != self.year:
                return False
            if self.decade is not None and (yr // 10) * 10 != self.decade:
                return False
        if self.publishers:
            if not publisher_matches_imprint_filter(row.get("publisher"), self.publishers):
                return False
        return True


class CorpusStoragePort(Protocol):
    """Port interface for streaming Corpus Passages with optional slice conditioning."""

    def iter_passages(self, slice_filter: CorpusSliceFilter | None = None) -> Iterator[dict]:
        ...


class ParquetCsvCorpusAdapter:
    """Production adapter streaming Corpus Passages from 127 Zstd-19 Parquet shards or CSV fallback."""

    def __init__(self, data_path: str):
        self.data_path = data_path

    def iter_passages(self, slice_filter: CorpusSliceFilter | None = None) -> Iterator[dict]:
        active_filter = slice_filter or CorpusSliceFilter()
        for row in lda_pipeline.iter_corpus_rows(self.data_path):
            if active_filter.matches(row):
                yield row


class InMemoryCorpusAdapter:
    """Local-substitutable in-memory Corpus Passage adapter for fast unit tests and slice evaluation."""

    def __init__(self, passages: Iterable[dict]):
        self._passages = list(passages)

    def iter_passages(self, slice_filter: CorpusSliceFilter | None = None) -> Iterator[dict]:
        active_filter = slice_filter or CorpusSliceFilter()
        for row in self._passages:
            if active_filter.matches(row):
                yield row


def aggregate_monograph_and_passage_summary(
    storage: CorpusStoragePort,
    slice_filter: CorpusSliceFilter | None = None,
) -> dict:
    """
    Aggregates Corpus Passages and deduplicated Monograph Works across any CorpusStoragePort
    using the Ubiquitous Language defined in CONTEXT.md.
    """
    passage_count = 0
    total_words = 0
    unique_monograph_titles: set[str] = set()
    imprints: set[str] = set()
    imprint_counts: dict[str, int] = defaultdict(int)
    layer_counts: dict[str, int] = defaultdict(int)
    decade_counts: dict[str, int] = defaultdict(int)
    years: list[int] = []

    for row in storage.iter_passages(slice_filter):
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        passage_count += 1
        words = len(text.split())
        total_words += words

        base_title = normalize_monograph_base_title(row.get("title"))
        if base_title:
            unique_monograph_titles.add(base_title)

        pub = str(row.get("publisher") or "").strip()
        if pub:
            imprints.add(pub)
            imprint_counts[pub] += 1

        lyr = str(row.get("corpus_layer") or "primary_fulltext").strip()
        layer_counts[lyr] += 1

        yr = extract_publication_year(row.get("year"))
        if yr is not None:
            years.append(yr)
            decade_counts[f"{(yr // 10) * 10}s"] += 1

    sorted_pubs = sorted(imprint_counts.items(), key=lambda x: x[1], reverse=True)
    return {
        "count": passage_count,
        "total_records": passage_count,
        "corpus_passages": passage_count,
        "unique_books": len(unique_monograph_titles),
        "monograph_works": len(unique_monograph_titles),
        "total_words": total_words,
        "publishers": [p for p, _ in sorted_pubs[:14]],
        "all_publishers_count": len(imprints),
        "publisher_counts": dict(sorted_pubs[:15]),
        "corpus_layers": dict(sorted(layer_counts.items(), key=lambda x: x[1], reverse=True)),
        "decade_counts": dict(sorted(decade_counts.items())),
        "year_range": f"{min(years)}–{max(years)}" if years else "1970–2025",
    }
