import React, { useEffect, useState, useMemo } from 'react';
import {
  X,
  BookOpen,
  Copy,
  Check,
  Download,
  ExternalLink,
  Search,
  Sparkles,
  FileText,
  Layers,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Type,
} from 'lucide-react';
import clsx from 'clsx';
import type { RepresentativeDoc } from './TopicModelViz';
import { InfoTooltip } from './InfoTooltip';

export interface FullTextChunk {
  chunk_index: number;
  title: string;
  text: string;
  word_count: number;
  corpus_layer?: string;
}

export interface Marc21FullDocumentPayload {
  title: string;
  base_title: string;
  author: string;
  publisher: string;
  year: string;
  corpus_layer: string;
  source_file?: string;
  dnb_catalog_url?: string;
  apa_citation: string;
  abstract?: string;
  keywords?: string[];
  dnb_series?: string;
  dnb_publication_type?: string;
  dnb_textplus_collection?: string;
  total_chunks_available: number;
  returned_chunks: number;
  total_words: number;
  text_access_level: 'full_book_passages' | 'toc_or_blurb_fulltext' | 'catalog_snippet';
  text_access_note: string;
  chunks: FullTextChunk[];
}

interface Marc21FullTextModalProps {
  doc: RepresentativeDoc | null;
  topicKeywords?: string[];
  topicLabel?: string;
  onClose: () => void;
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function describeAccessLayer(layer?: string): string {
  const l = (layer || '').toLowerCase();
  if (l.includes('dnb_oa_fullbook') || l.includes('entire_fulltext') || l.includes('archive_org') || l.includes('gbv_kostenfrei')) {
    return 'Open-Access Full-Text Book (complete digitized chapters extracted from DNB /34, OpenAlex, or GBV).';
  }
  if (l.includes('hathitrust')) {
    return 'HathiTrust Research Center (HTRC) Extracted Features — scholarly token stream of an in-copyright printed book (§ 60d UrhG).';
  }
  if (l.includes('toc') || l.includes('gbv_direct')) {
    return 'Digitized DNB /04 Table of Contents (Inhaltsverzeichnis) and publisher reading sample PDF.';
  }
  if (l.includes('inhaltstext') || l.includes('abstract')) {
    return 'Publisher blurb (Inhaltstext) and catalog abstract archived by Deutsche Nationalbibliothek (deposit.dnb.de).';
  }
  return 'Bibliographic MARC21 catalog record and paratextual metadata from Deutsche Nationalbibliothek (DNB).';
}

export const Marc21FullTextModal: React.FC<Marc21FullTextModalProps> = ({
  doc,
  topicKeywords = [],
  topicLabel,
  onClose,
}) => {
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [payload, setPayload] = useState<Marc21FullDocumentPayload | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'all' | 'paged'>('all');
  const [activeChunkIdx, setActiveChunkIdx] = useState<number>(0);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [highlightTopicWords, setHighlightTopicWords] = useState<boolean>(true);
  const [fontSize, setFontSize] = useState<'sm' | 'base' | 'lg'>('base');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const fetchDocument = async (targetDoc: RepresentativeDoc, maxChunks: number, isMore = false) => {
    if (isMore) setLoadingMore(true);
    else {
      setLoading(true);
      setErrorMsg(null);
      setActiveChunkIdx(0);
    }

    try {
      const params = new URLSearchParams();
      params.set('title', targetDoc.title || '');
      if (targetDoc.publisher) params.set('publisher', targetDoc.publisher);
      if (targetDoc.author) params.set('author', targetDoc.author);
      if (targetDoc.year || targetDoc.date) params.set('year', String(targetDoc.year || targetDoc.date));
      params.set('max_chunks', String(maxChunks));

      const res = await fetch(`/api/marc21-document?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Marc21FullDocumentPayload = await res.json();
      setPayload(data);
    } catch (err: any) {
      // Graceful fallback using whatever is already in the card
      const fallbackYear = String(targetDoc.year || targetDoc.date || 'o. J.');
      const fallbackText = targetDoc.snippet || 'No extended full text available for this catalog record.';
      setPayload({
        title: targetDoc.title,
        base_title: targetDoc.title,
        author: targetDoc.author || 'o. V.',
        publisher: targetDoc.publisher || 'Unknown',
        year: fallbackYear,
        corpus_layer: targetDoc.corpus_layer || 'marc21_catalog',
        dnb_catalog_url: `https://portal.dnb.de/opac/simpleSearch?query=${encodeURIComponent(targetDoc.title)}`,
        apa_citation:
          targetDoc.apa_citation || `${targetDoc.publisher}. (${fallbackYear}). ${targetDoc.title}.`,
        abstract: fallbackText,
        dnb_series: targetDoc.dnb_series,
        dnb_publication_type: targetDoc.dnb_publication_type,
        dnb_textplus_collection: targetDoc.dnb_textplus_collection,
        total_chunks_available: 1,
        returned_chunks: 1,
        total_words: fallbackText.split(/\s+/).filter(Boolean).length,
        text_access_level: 'catalog_snippet',
        text_access_note: 'Displaying indexed catalog text (backend full-text endpoint unreachable).',
        chunks: [
          {
            chunk_index: 1,
            title: targetDoc.title,
            text: fallbackText,
            word_count: fallbackText.split(/\s+/).filter(Boolean).length,
            corpus_layer: targetDoc.corpus_layer,
          },
        ],
      });
      setErrorMsg(err?.message || 'Fallback mode active');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    if (!doc) {
      setPayload(null);
      return;
    }
    fetchDocument(doc, 20, false);
  }, [doc]);

  useEffect(() => {
    if (!doc) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [doc, onClose]);

  const combinedFullText = useMemo(() => {
    if (!payload) return '';
    return payload.chunks
      .map((c, idx) =>
        payload.chunks.length > 1
          ? `--- Passage ${idx + 1} / ${payload.chunks.length} (${c.word_count.toLocaleString()} words) ---\n${c.text}`
          : c.text
      )
      .join('\n\n');
  }, [payload]);

  const searchRegex = useMemo(() => {
    const q = searchTerm.trim();
    if (!q || q.length < 2) return null;
    try {
      return new RegExp(`(${escapeRegExp(q)})`, 'gi');
    } catch {
      return null;
    }
  }, [searchTerm]);

  const topicRegex = useMemo(() => {
    if (!highlightTopicWords || !topicKeywords.length) return null;
    const clean = topicKeywords
      .map((w) => w.trim())
      .filter((w) => w.length >= 3)
      .slice(0, 12);
    if (!clean.length) return null;
    try {
      return new RegExp(`\\b(${clean.map(escapeRegExp).join('|')}[a-zäöüß]*)\\b`, 'gi');
    } catch {
      return null;
    }
  }, [highlightTopicWords, topicKeywords]);

  const renderHighlightedText = (rawText: string) => {
    if (!rawText) return null;
    // Prioritize explicit user search highlight; also highlight active topic lemmas gently
    if (searchRegex) {
      const parts = rawText.split(searchRegex);
      return parts.map((part, i) =>
        i % 2 === 1 ? (
          <mark
            key={i}
            className="bg-traditional text-obsidian-950 font-semibold px-0.5 rounded-sm"
          >
            {part}
          </mark>
        ) : (
          <React.Fragment key={i}>{part}</React.Fragment>
        )
      );
    }
    if (topicRegex) {
      const parts = rawText.split(topicRegex);
      return parts.map((part, i) =>
        i % 2 === 1 ? (
          <mark
            key={i}
            title={topicLabel ? `Matches active topic: ${topicLabel}` : 'Matches active topic lemma'}
            className="bg-traditional/20 text-traditional border-b border-traditional/50 px-0.5 rounded-sm"
          >
            {part}
          </mark>
        ) : (
          <React.Fragment key={i}>{part}</React.Fragment>
        )
      );
    }
    return rawText;
  };

  const matchCount = useMemo(() => {
    if (!searchRegex || !combinedFullText) return 0;
    const matches = combinedFullText.match(searchRegex);
    return matches ? matches.length : 0;
  }, [searchRegex, combinedFullText]);

  if (!doc) return null;

  const copyValue = (key: string, val: string) => {
    navigator.clipboard.writeText(val);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleDownloadTxt = () => {
    if (!payload) return;
    const header = [
      `TITLE: ${payload.title}`,
      `AUTHOR: ${payload.author}`,
      `PUBLISHER: ${payload.publisher}`,
      `YEAR: ${payload.year}`,
      `CORPUS LAYER: ${payload.corpus_layer}`,
      `APA 7TH: ${payload.apa_citation}`,
      payload.source_file ? `SOURCE: ${payload.source_file}` : '',
      `WORDS: ${payload.total_words}`,
      '====================================================================',
      '',
    ]
      .filter(Boolean)
      .join('\n');
    const blob = new Blob([header + combinedFullText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const slug = (payload.base_title || 'document').slice(0, 50).replace(/[^a-zA-Z0-9äöüÄÖÜß]+/g, '_');
    a.download = `${payload.year}_${slug}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const chunksToRender =
    payload && payload.chunks.length > 0
      ? viewMode === 'all'
        ? payload.chunks
        : [payload.chunks[Math.min(activeChunkIdx, payload.chunks.length - 1)]]
      : [];

  const externalSourceUrl =
    payload?.source_file && /^https?:\/\//i.test(payload.source_file)
      ? payload.source_file
      : null;

  const dnbPortalUrl =
    payload?.dnb_catalog_url ||
    `https://portal.dnb.de/opac/simpleSearch?query=${encodeURIComponent(doc.title.replace(/\[.*?\]/g, '').trim())}`;

  const fontSizeClass =
    fontSize === 'sm'
      ? 'text-xs leading-relaxed'
      : fontSize === 'lg'
      ? 'text-base leading-loose'
      : 'text-sm leading-7';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-2 sm:p-5"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="MARC21 Full-Text Reader"
    >
      <div
        className="w-full max-w-5xl max-h-[92vh] bg-obsidian-900 border border-traditional/40 rounded-2xl shadow-2xl flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Modal Header */}
        <div className="p-4 sm:p-5 border-b border-white/[0.08] bg-obsidian-950/95 space-y-3 shrink-0">
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1.5 min-w-0">
              <div className="flex flex-wrap items-center gap-1.5 font-mono text-[10px]">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-traditional/15 border border-traditional/40 text-traditional font-bold uppercase tracking-wider">
                  <BookOpen className="w-3 h-3" />
                  MARC21 Full-Text Reader
                </span>
                <InfoTooltip
                  title="Publisher (MARC Tag 264$b)"
                  content="The German publishing house that issued this monograph or archival volume."
                >
                  <span className="px-2 py-0.5 rounded bg-white/[0.05] border border-white/10 text-parchment-100 font-semibold">
                    {payload?.publisher || doc.publisher}
                  </span>
                </InfoTooltip>
                <InfoTooltip
                  title="Publication Year (MARC Tag 264$c)"
                  content="The cataloged publication date in the Deutsche Nationalbibliothek (DNB) record."
                >
                  <span className="px-2 py-0.5 rounded bg-white/[0.05] border border-white/10 text-parchment-200">
                    {payload?.year || doc.year || doc.date || 'o. J.'}
                  </span>
                </InfoTooltip>
                {doc.probability !== undefined && (
                  <InfoTooltip
                    title="Topic Fit Score (θ)"
                    content="How strongly this work belongs to the currently selected LDA topic. Higher percentages mean this topic dominates the book's vocabulary."
                  >
                    <span className="px-2 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/35 text-emerald-300 font-bold">
                      θ = {doc.probability}%
                    </span>
                  </InfoTooltip>
                )}
                {(payload?.corpus_layer || doc.corpus_layer) && (
                  <InfoTooltip
                    title="Corpus Text Layer"
                    content={describeAccessLayer(payload?.corpus_layer || doc.corpus_layer)}
                  >
                    <span className="px-2 py-0.5 rounded bg-neoliberal/15 border border-neoliberal/35 text-neoliberal cursor-help">
                      {payload?.corpus_layer || doc.corpus_layer}
                    </span>
                  </InfoTooltip>
                )}
              </div>

              <h2 className="font-serif text-lg sm:text-2xl font-bold text-parchment-50 leading-snug break-words select-text">
                {payload?.title || doc.title}
              </h2>

              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] text-parchment-300">
                <span>
                  <strong className="text-parchment-200">Author (100$a):</strong>{' '}
                  {payload?.author || doc.author || 'o. V.'}
                </span>
                {payload && (
                  <>
                    <span>•</span>
                    <span>
                      <strong className="text-traditional">
                        {payload.total_words.toLocaleString()}
                      </strong>{' '}
                      words loaded ({payload.returned_chunks} of {payload.total_chunks_available}{' '}
                      section{payload.total_chunks_available === 1 ? '' : 's'})
                    </span>
                  </>
                )}
              </div>
            </div>

            <button
              onClick={onClose}
              title="Close Full-Text Reader (Esc)"
              aria-label="Close Full-Text Reader"
              className="p-2 rounded-lg bg-white/[0.05] hover:bg-white/[0.12] border border-white/10 text-parchment-200 hover:text-white transition-colors cursor-pointer shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Interactive Reader Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-white/[0.06]">
            {/* Search within document */}
            <div className="relative flex-1 min-w-[200px] max-w-sm">
              <Search className="w-3.5 h-3.5 text-parchment-300 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Find word or phrase inside this text..."
                className="w-full bg-obsidian-900 border border-white/10 rounded-lg pl-8 pr-16 py-1.5 text-xs font-mono text-parchment-100 placeholder:text-parchment-300/60 focus:outline-none focus:border-traditional"
              />
              {searchTerm.trim().length >= 2 && (
                <span className="absolute right-2.5 top-1/2 -translate-y-1/2 font-mono text-[10px] text-traditional font-bold">
                  {matchCount} hit{matchCount === 1 ? '' : 's'}
                </span>
              )}
            </div>

            {/* Action buttons */}
            <div className="flex flex-wrap items-center gap-1.5 font-mono text-[10px]">
              {topicKeywords.length > 0 && (
                <InfoTooltip
                  title="Highlight Active Topic Words"
                  content="Softly underlines words in this text that belong to the currently selected LDA topic so you can verify why the model assigned this book here."
                >
                  <button
                    onClick={() => setHighlightTopicWords((p) => !p)}
                    className={clsx(
                      'inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border transition-colors cursor-pointer',
                      highlightTopicWords
                        ? 'bg-traditional/20 border-traditional/50 text-traditional font-bold'
                        : 'bg-obsidian-900 border-white/10 text-parchment-300 hover:text-parchment-100'
                    )}
                  >
                    <Sparkles className="w-3 h-3" />
                    <span>Topic Words</span>
                  </button>
                </InfoTooltip>
              )}

              {payload && payload.chunks.length > 1 && (
                <div className="inline-flex items-center rounded-lg bg-obsidian-900 border border-white/10 p-0.5">
                  <button
                    onClick={() => setViewMode('all')}
                    className={clsx(
                      'px-2 py-1 rounded transition-colors cursor-pointer',
                      viewMode === 'all'
                        ? 'bg-traditional text-obsidian-950 font-bold'
                        : 'text-parchment-300 hover:text-parchment-100'
                    )}
                  >
                    Full Continuous
                  </button>
                  <button
                    onClick={() => setViewMode('paged')}
                    className={clsx(
                      'px-2 py-1 rounded transition-colors cursor-pointer',
                      viewMode === 'paged'
                        ? 'bg-traditional text-obsidian-950 font-bold'
                        : 'text-parchment-300 hover:text-parchment-100'
                    )}
                  >
                    By Passage ({payload.chunks.length})
                  </button>
                </div>
              )}

              <div className="inline-flex items-center rounded-lg bg-obsidian-900 border border-white/10 p-0.5">
                <Type className="w-3 h-3 text-parchment-300 mx-1.5" />
                {(['sm', 'base', 'lg'] as const).map((sz) => (
                  <button
                    key={sz}
                    onClick={() => setFontSize(sz)}
                    title={`Text size: ${sz.toUpperCase()}`}
                    className={clsx(
                      'px-1.5 py-1 rounded uppercase cursor-pointer',
                      fontSize === sz
                        ? 'bg-white/15 text-parchment-50 font-bold'
                        : 'text-parchment-300 hover:text-parchment-100'
                    )}
                  >
                    {sz === 'sm' ? 'A-' : sz === 'base' ? 'A' : 'A+'}
                  </button>
                ))}
              </div>

              <button
                onClick={() => copyValue('fulltext', combinedFullText)}
                disabled={!combinedFullText}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.12] border border-white/10 text-parchment-100 transition-colors cursor-pointer disabled:opacity-40"
              >
                {copiedKey === 'fulltext' ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-400" />
                    <span className="text-emerald-300">Copied Text</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3 text-traditional" />
                    <span>Copy Text</span>
                  </>
                )}
              </button>

              <button
                onClick={handleDownloadTxt}
                disabled={!combinedFullText}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.12] border border-white/10 text-parchment-100 transition-colors cursor-pointer disabled:opacity-40"
              >
                <Download className="w-3 h-3 text-neoliberal" />
                <span>.TXT</span>
              </button>
            </div>
          </div>
        </div>

        {/* Main Scrollable Full-Text Reading Body */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-4 sm:p-6 space-y-4 bg-obsidian-900">
          {loading ? (
            <div className="py-16 flex flex-col items-center justify-center gap-3 text-parchment-300 font-mono text-xs">
              <Loader2 className="w-6 h-6 text-traditional animate-spin" />
              <span>Retrieving complete German text &amp; archival passages from corpus...</span>
            </div>
          ) : payload ? (
            <>
              {/* Access Level Notice Strip */}
              <div className="p-3 rounded-xl bg-obsidian-950/80 border border-white/[0.08] flex flex-wrap items-center justify-between gap-2 text-[11px]">
                <div className="flex items-center gap-2 text-parchment-200">
                  <FileText className="w-4 h-4 text-traditional shrink-0" />
                  <span>{payload.text_access_note}</span>
                  {errorMsg && (
                    <span className="font-mono text-[10px] text-amber-300">({errorMsg})</span>
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-2 font-mono text-[10px]">
                  {externalSourceUrl && (
                    <a
                      href={externalSourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 text-emerald-300 font-bold transition-colors"
                    >
                      <span>Open Original Source</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                  <a
                    href={dnbPortalUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-traditional/15 hover:bg-traditional/25 border border-traditional/40 text-traditional font-bold transition-colors"
                  >
                    <span>Open in DNB Catalog</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>

              {/* Paged Controls when viewing by passage */}
              {viewMode === 'paged' && payload.chunks.length > 1 && (
                <div className="flex items-center justify-between gap-2 p-2.5 rounded-lg bg-obsidian-950/70 border border-white/[0.07] font-mono text-xs">
                  <button
                    onClick={() => setActiveChunkIdx((i) => Math.max(0, i - 1))}
                    disabled={activeChunkIdx === 0}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-white/[0.05] hover:bg-white/[0.12] border border-white/10 disabled:opacity-35 cursor-pointer"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                    <span>Previous Passage</span>
                  </button>
                  <span className="text-parchment-200">
                    Passage <strong className="text-traditional">{activeChunkIdx + 1}</strong> of{' '}
                    <strong>{payload.chunks.length}</strong>
                  </span>
                  <button
                    onClick={() =>
                      setActiveChunkIdx((i) => Math.min(payload.chunks.length - 1, i + 1))
                    }
                    disabled={activeChunkIdx >= payload.chunks.length - 1}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-white/[0.05] hover:bg-white/[0.12] border border-white/10 disabled:opacity-35 cursor-pointer"
                  >
                    <span>Next Passage</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}

              {/* Rendered Text Passages */}
              <div className="space-y-4">
                {chunksToRender.map((chunk, i) => (
                  <article
                    key={`${chunk.chunk_index}-${i}`}
                    className="p-4 sm:p-5 rounded-xl bg-obsidian-950/90 border border-white/[0.08] space-y-2.5"
                  >
                    {payload.chunks.length > 1 && (
                      <div className="flex items-center justify-between gap-2 pb-2 border-b border-white/[0.06] font-mono text-[10px] text-parchment-300">
                        <span className="inline-flex items-center gap-1.5 text-traditional font-bold">
                          <Layers className="w-3 h-3" />
                          <span>
                            Section {chunk.chunk_index} · {chunk.title}
                          </span>
                        </span>
                        <span>{chunk.word_count.toLocaleString()} words</span>
                      </div>
                    )}
                    <div
                      className={clsx(
                        'font-sans text-parchment-100 whitespace-pre-wrap select-text break-words',
                        fontSizeClass
                      )}
                    >
                      {renderHighlightedText(chunk.text)}
                    </div>
                  </article>
                ))}
              </div>

              {/* Load More Passages Button if book has additional chunks */}
              {payload.returned_chunks < payload.total_chunks_available && (
                <div className="flex justify-center pt-1">
                  <button
                    onClick={() =>
                      fetchDocument(doc, Math.min(payload.total_chunks_available, payload.returned_chunks + 30), true)
                    }
                    disabled={loadingMore}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-traditional/15 hover:bg-traditional/25 border border-traditional/40 font-mono text-xs font-bold text-traditional transition-colors cursor-pointer disabled:opacity-50"
                  >
                    {loadingMore ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Loading remaining book passages...</span>
                      </>
                    ) : (
                      <>
                        <Layers className="w-3.5 h-3.5" />
                        <span>
                          Load More Passages ({payload.returned_chunks} of{' '}
                          {payload.total_chunks_available} loaded)
                        </span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </>
          ) : null}
        </div>

        {/* Sticky APA 7th Footer */}
        <div className="p-3.5 sm:px-5 border-t border-white/[0.08] bg-obsidian-950/95 flex flex-wrap items-center justify-between gap-3 shrink-0">
          <div className="min-w-0 flex-1">
            <span className="block font-mono text-[9px] uppercase tracking-widest text-traditional mb-0.5">
              APA 7th Edition Reference
            </span>
            <p className="font-mono text-[11px] text-parchment-100 break-words select-text">
              {payload?.apa_citation ||
                doc.apa_citation ||
                `${doc.publisher}. (${doc.year || doc.date || 'o. J.'}). ${doc.title}.`}
            </p>
          </div>
          <button
            onClick={() =>
              copyValue(
                'apa',
                payload?.apa_citation ||
                  doc.apa_citation ||
                  `${doc.publisher}. (${doc.year || doc.date || 'o. J.'}). ${doc.title}.`
              )
            }
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-traditional text-obsidian-950 font-mono text-xs font-bold hover:opacity-95 transition-opacity cursor-pointer shrink-0"
          >
            {copiedKey === 'apa' ? (
              <>
                <Check className="w-3.5 h-3.5" />
                <span>Copied APA 7th</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy APA 7th</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
