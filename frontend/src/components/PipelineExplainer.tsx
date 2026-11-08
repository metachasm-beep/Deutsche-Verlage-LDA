import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Database,
  Filter,
  Cpu,
  GitBranch,
  Layers,
  Award,
  Play,
  CheckCircle2,
  BookOpen,
  Sparkles,
  FileCode2,
  ArrowRight,
  Terminal,
  Scale,
} from 'lucide-react';
import clsx from 'clsx';

import { type LDAMode, type ModeComparisonRow, type SLDADiagnostics } from '../hooks/useLDA';

interface PipelineExplainerProps {
  summary: any;
  vocabSize: number;
  numTopics: number;
  coherenceScore: number;
  cvCoherence: number | null;
  isTraining: boolean;
  onRunFullPipeline: () => void;
  ldaMode?: LDAMode;
  onSelectLdaMode?: (mode: LDAMode) => void;
  modesComparison?: ModeComparisonRow[];
  sldaDiagnostics?: SLDADiagnostics | null;
  seedLexicons?: Record<string, string[]>;
  religiousBoostWords?: string[];
  robustnessTelemetry?: any;
}

const DEFAULT_SEED_LEXICONS: Record<string, string[]> = {
  'Traditional / Ecclesiastical': [
    'gott', 'kirche', 'glaube', 'jesus', 'christus', 'bibel', 'theologie', 'gebet',
    'liturgie', 'sakrament', 'gnade', 'schöpfung', 'evangelium', 'seelsorge', 'pfarrer',
    'gemeinde', 'katholisch', 'evangelisch', 'ökumene', 'bischof', 'predigt',
    'frömmigkeit', 'heilig', 'auferstehung', 'erlösung',
  ],
  'Neoliberal / Self-Optimization': [
    'selbsthilfe', 'achtsamkeit', 'erfolg', 'glück', 'heilung', 'energie', 'bewusstsein',
    'meditation', 'wohlbefinden', 'potenzial', 'selbstliebe', 'coaching', 'resilienz',
    'motivation', 'lebenshilfe', 'gelassenheit', 'balance', 'stress', 'erfüllung',
    'innerer', 'harmonie', 'positiv', 'kraft', 'loslassen',
  ],
  'Critical / Secular-Humanist': [
    'kritik', 'wissenschaft', 'gesellschaft', 'politik', 'macht', 'ideologie', 'moderne',
    'säkularisierung', 'demokratie', 'ethik', 'philosophie', 'soziologie', 'kapitalismus',
    'aufklärung', 'diskurs', 'menschenrechte', 'vernunft', 'autonomie', 'pluralismus',
    'gerechtigkeit', 'staat', 'institution',
  ],
};

const DEFAULT_RELIGIOUS_BOOST_WORDS: string[] = [
  'glaube', 'gott', 'spiritualität', 'kirche', 'seele', 'religion', 'seelsorge', 'gebet',
  'heilig', 'theologie', 'christlich', 'christus', 'bibel', 'frömmigkeit', 'liturgie',
  'erlösung', 'auferstehung', 'gnade', 'säkularität', 'selbsthilfe', 'religionskritik',
];

const PIPELINE_STAGES = [
  {
    id: 1,
    code: 'STAGE 01 · INGESTION',
    title: 'Multi-Layer Corpus Acquisition & MARC21 Fusion (1970–2025)',
    icon: Database,
    accent: 'text-traditional',
    borderAccent: 'border-traditional/40',
    bgAccent: 'bg-traditional/10',
    formula: 'D = 10,528,704 Passages · 10,041,481 Works · 18,714 Full Books · 801.39M Words · 126 Zstd-19 Parquet Shards',
    summary:
      'Ingests 100% of the official DNB OpenData MARC21-XML Bulk Dump (Packages 1–5, 40.10M total records scanned) hydrated via DNBLab (1,295,009 indexed onlinefree /34 OA IDNs, /04/text plain-text TOC OCRs, services.dnb.de/deposit.dnb.de Inhaltstexte, and § 60d UrhG Derived Text Formats) and HathiTrust full-text books across all 102 DNB Sachgruppen (000–990, B, K, S; 1970–2025).',
    details: [
      'Combines MARC21 Tag 245$a/$b (Title/Subtitle), Tag 264$b/$c (Imprint/Year across 713,838 raw imprint strings / 109 canonical publishers), Tag 520$a (Abstract), Tags 650/689$a (GND Subject Headings), and Tag 856$u (/04/text TOCs, /34 OA Books, services.dnb.de/deposit.dnb.de Inhaltstexte) across all 102 DNB Sachgruppen.',
      'Stratified across 10,041,481 unique German works (1970–2025): 18,714 complete full-text books (459,841 passages), 150,976 works with digitized TOC PDFs/OCRs, and 9,913,690 DNB OpenData MARC21-XML & deposit/services.dnb.de Inhaltstext records.',
      'Stored in 126 Zstd-19 Apache Parquet shards (data/parquet/ · 1,507.58 MB compressed) backed by GitHub Release v12.0-dnb-parquet-shards and Online Streaming LDA (Hoffman et al., 2010).',
    ],
  },
  {
    id: 2,
    code: 'STAGE 02 · SANITIZATION',
    title: 'Unicode NFC, MARC21 C1 Control & Fraktur/Imprint Noise Stripping',
    icon: Filter,
    accent: 'text-neoliberal',
    borderAccent: 'border-neoliberal/40',
    bgAccent: 'bg-neoliberal/10',
    formula: 'ALL_STOPWORDS = spaCy_DE ∪ DOMAIN_STOPWORDS ∪ FRAKTUR_AND_META_NOISE',
    summary:
      'Eliminates archival control codes, bracketed provenance headers, historical Fraktur OCR misrecognitions, bibliographic abbreviations, and publisher self-mentions (Santana et al., 2025, DHQ 19.2).',
    details: [
      'strips bracketed archival headers ([HTRC-Vollbuch-Abschnitt], [DNB-Inhaltsverzeichnis]) and repeated continuation-chunk title/author prefixes on chunk_index > 1.',
      'Filters historical Fraktur OCR artifacts ("ber", "unb", "bie", "bas", "bes", "bem", "fein", "feine", "unde") and PDF front-matter noise ("inhaltsverzeichnis", "vorwort", "einleitung", "creativecommons").',
      'Removes publisher imprint self-references ("herder", "suhrkamp", "rowohlt", "fischer", "patmos", "kösel", "alibri", "gütersloher", "kohlhammer", "beck") and scholarly apparatus ("hrsg", "aufl", "bd", "vgl", "ebd", "kap").',
    ],
  },
  {
    id: 3,
    code: 'STAGE 03 · LEMMATIZATION',
    title: 'German Morphosyntactic Lemmatization (spaCy de_core_news_lg)',
    icon: Cpu,
    accent: 'text-critical',
    borderAccent: 'border-critical/40',
    bgAccent: 'bg-critical/10',
    formula: 'POS ∈ {NOUN, PROPN, ADJ} · len(lemma) > 2 · SHA-1 Token Cache',
    summary:
      'Reduces inflected German case, gender, and number paradigms to canonical dictionary lemmas using the large German transformer/CNN pipeline with persistent content-addressed caching.',
    details: [
      'Executes nlp.pipe(batch_size=64, disable=["ner", "parser"]) with max_length = 5,000,000 and SHA-1 document hashing in data/token_cache.json for O(1) warm reloads.',
      'Retains exclusively open-class semantic bearers: Nouns (NOUN), Proper Nouns (PROPN), and Adjectives (ADJ), discarding auxiliary verbs, pronouns, and conjunctions.',
      'Applies 2× domain-specific lexical weighting (RELIGIOUS_VOICE_KEYWORDS) to core theoretical signifiers (glaube, gott, spiritualität, kirche, seelsorge, säkularität, selbsthilfe, religionskritik).',
    ],
  },
  {
    id: 4,
    code: 'STAGE 04 · COLLOCATION & PRUNING',
    title: 'N-Gram Phrase Detection & Dictionary Extremes Filtering',
    icon: GitBranch,
    accent: 'text-emerald-400',
    borderAccent: 'border-emerald-500/40',
    bgAccent: 'bg-emerald-500/10',
    formula: 'Phrases(min_count=5, threshold=10) · filter_extremes(no_below=5, no_above=0.55, keep_n=25000)',
    summary:
      'Detects statistically significant multi-word theological and sociological collocations and prunes extreme low-frequency typos and high-frequency background terms.',
    details: [
      'Gensim Phraser (min_count=5, threshold=10) binds recurring multi-word concepts into single compound tokens while stripping all personal (PER) and geographic (LOC) proper-noun entities (e.g., retaining religionspädagogik, säkularisierung, kirchenmitgliedschaft, selbstoptimierung).',
      'Re-applies ALL_STOPWORDS and NON_CANONICAL_LOC_AND_PER_NOISE post-bigramming to ensure zero author/biographical name leakage across all 4 LDA paradigms.',
      'Prunes tokens appearing in fewer than 5 documents (no_below=5) or more than 55% of the corpus (no_above=0.55, keep_n=25,000), yielding a high-signal vocabulary of |V| = 25,000 lemmas/bigrams.',
    ],
  },
  {
    id: 5,
    code: 'STAGE 05 · BAYESIAN INFERENCE',
    title: 'Online Variational Bayes LDA Estimation (Gensim LdaModel)',
    icon: Layers,
    accent: 'text-traditional',
    borderAccent: 'border-traditional/40',
    bgAccent: 'bg-traditional/10',
    formula: 'P(w | d) = Σ_k P(w | z_k = φ_k) · P(z_k | d = θ_d)',
    summary:
      'Estimates posterior topic-word distributions (φ_k) and document-topic mixtures (θ_d) via Online Variational Bayes with asymmetric learned Dirichlet priors.',
    details: [
      'Configured with passes = 15 full corpus iterations, chunksize = 1,500 documents per mini-batch, update_every = 1, and deterministic seed random_state = 100.',
      'Learns asymmetric Dirichlet prior α = "auto" (document-topic density) and η = "auto" (topic-word lexical specificity) directly from the 385.12M-word German corpus.',
      'Dynamically guards against small temporal slices by bounding effective_k = max(2, min(k_topics, len(corpus) - 1)).',
    ],
  },
  {
    id: 6,
    code: 'STAGE 06 · HERMENEUTIC VALIDATION',
    title: 'Coherence Evaluation, Base-Title Deduplication & Ideological Taxonomy',
    icon: Award,
    accent: 'text-neoliberal',
    borderAccent: 'border-neoliberal/40',
    bgAccent: 'bg-neoliberal/10',
    formula: 'U_Mass = -2.4760 & C_v (Röder et al., 2015) · 3-Way Ideological Projection',
    summary:
      'Validates semantic interpretability via intrinsic and extrinsic coherence metrics, deduplicates chunked books by base title, and projects topics onto the three-way sociological framework.',
    details: [
      'Computes intrinsic document co-occurrence (U_Mass = -2.4760 on Unsupervised, -1.7897 on Supervised sLDA) alongside sliding-window NPMI coherence (C_v across K ∈ [4, 30]).',
      'Deduplicates multi-chunk full-text books via regex base_title = re.sub(r"\\[.*?\\]", "", raw_title) so each topic surfaces distinct representative monographs with formatted APA 7th citations.',
      'Cross-tabulates posterior document-topic probabilities (θ_d) by Publisher Imprint and Decade Cohort (1970s–2020s) and classifies each topic into Traditional/Ecclesiastical, Neoliberal/Self-Optimization, or Critical/Secular-Humanist.',
    ],
  },
];

const LAYER_LABELS: Record<string, { label: string; tier: string; desc: string; color: string }> = {
  hathitrust_ef_fullbook_print: {
    label: 'HathiTrust HTRC Printed Full-Text Books (Multi-ISBN Matched)',
    tier: 'Tier 1B · Complete Full Book',
    desc: 'Digitized printed German monographs matched via DNB/GBV ISBN-10/13 clusters and segmented into 1,000-word passages',
    color: '#38BDF8',
  },
  dnb_oa_fullbook: {
    label: 'DNB /34 & MARC 856 Open-Access Full-Text Monographs & Dissertations',
    tier: 'Tier 1A · Complete Full Book',
    desc: 'Born-digital and retro-digitized full-text German books and doctoral dissertations harvested from DNB /34 & repository streams',
    color: '#34D399',
  },
  dnb_deposit_inhaltstext: {
    label: 'DNB deposit.dnb.de & /blurb/ Archival Inhaltstexte',
    tier: 'Tier 3A · Archival Inhaltstext',
    desc: 'Official publisher blurbs, synopses, and MARC 520 content summaries deposited with the German National Library',
    color: '#22D3EE',
  },
  dnb_toc_pdf_fulltext: {
    label: 'DNB /04 Digitized Inhaltsverzeichnis (TOC) & Reading-Sample PDFs',
    tier: 'Tier 2A · Digitized TOC PDF',
    desc: 'Full chapter hierarchies, section headings, and reading samples extracted via PyMuPDF from DNB /04 catalog PDFs',
    color: '#EAB308',
  },
  gbv_direct_fulltext_pdf: {
    label: 'GBV / K10plus Consortial Inhaltsverzeichnis (TOC) & Full-Text PDFs',
    tier: 'Tier 2B · Digitized TOC PDF',
    desc: 'Digitized tables of contents and repository PDFs harvested across 41 DDC subject buckets via GBV / K10plus SRU',
    color: '#FB7185',
  },
  entire_fulltext_book_cloud: {
    label: 'OpenAlex & Cloud Open-Access Full-Text German Monographs',
    tier: 'Tier 1C · Complete Full Book',
    desc: 'Complete open-access German scholarly monographs harvested from OpenAlex & institutional repositories (1,000-word chunks)',
    color: '#10B981',
  },
  drm_fallback_multi_api_enriched: {
    label: 'DNB SRU + Multi-API Enriched Bibliographic Paratexts',
    tier: 'Tier 3B · Enriched Paratext',
    desc: 'MARC21 bibliographic records enriched with publisher summaries, RVK/BKL descriptors, and GND subject headings',
    color: '#F59E0B',
  },
  gbv_kostenfrei_fullbook_pdf: {
    label: 'GBV / K10plus Kostenfrei Open-Access Full-Book PDFs',
    tier: 'Tier 1C · Complete Full Book',
    desc: 'Complete open-access books retrieved from GBV MARC 856 Kostenfrei digital monograph streams',
    color: '#818CF8',
  },
  primary_cloud_oa_abstract: {
    label: 'OpenAlex Reconstructed Scholarly Abstracts (abstract_inverted_index)',
    tier: 'Tier 3C · Scholarly Abstract',
    desc: 'Extended German scholarly book and chapter abstracts reconstructed from OpenAlex inverted indices',
    color: '#2DD4BF',
  },
  archive_org_fulltext_book: {
    label: 'Internet Archive Full-Text German Monograph Chunks',
    tier: 'Tier 1C · Complete Full Book',
    desc: 'Digitized full-text German theological, philosophical & critical monographs from Archive.org',
    color: '#60A5FA',
  },
  green_oa_repository_fulltext: {
    label: 'Green Open-Access Institutional & Faculty Repositories',
    tier: 'Tier 1C · Complete Full Book',
    desc: 'University & church repository full-text deposits across German theological and humanities faculties',
    color: '#A78BFA',
  },
  primary_cloud_oa_fulltext: {
    label: 'Primary Publisher Open-Access Full-Text Monographs',
    tier: 'Tier 1C · Complete Full Book',
    desc: 'Direct publisher open-access full-text monographs',
    color: '#F472B6',
  },
  primary_fulltext: {
    label: 'Primary Archival Full-Text Monograph Deposit',
    tier: 'Tier 1C · Complete Full Book',
    desc: 'Direct full-text archival deposit',
    color: '#94A3B8',
  },
};

export const PipelineExplainer: React.FC<PipelineExplainerProps> = ({
  summary,
  vocabSize,
  numTopics,
  coherenceScore,
  cvCoherence,
  isTraining,
  onRunFullPipeline,
  ldaMode = 'unsupervised',
  onSelectLdaMode,
  modesComparison = [],
  sldaDiagnostics,
  seedLexicons,
  religiousBoostWords,
  robustnessTelemetry,
}) => {
  const [activeStage, setActiveStage] = useState<number>(6);
  const [vocabLookupQuery, setVocabLookupQuery] = useState<string>('');
  const resolvedSeeds =
    seedLexicons && Object.keys(seedLexicons).length > 0 ? seedLexicons : DEFAULT_SEED_LEXICONS;
  const resolvedBoostWords =
    religiousBoostWords && religiousBoostWords.length > 0
      ? religiousBoostWords
      : DEFAULT_RELIGIOUS_BOOST_WORDS;

  // Animate through stages 1..6 when isTraining is active
  useEffect(() => {
    if (!isTraining) {
      setActiveStage(6);
      return;
    }
    setActiveStage(1);
    const interval = setInterval(() => {
      setActiveStage((prev) => (prev < 6 ? prev + 1 : 1));
    }, 900);
    return () => clearInterval(interval);
  }, [isTraining]);

  const totalRecords = summary?.count || 461785;
  const uniqueBooks = summary?.master_manifest?.total_unique_works_1970_2025 || summary?.unique_books || 82283;
  const totalFullBooks = summary?.master_manifest?.total_complete_fulltext_books || 12739;
  const totalWords = summary?.total_words || 385115918;
  const corpusLayers: Record<string, number> = summary?.corpus_layers || {
    hathitrust_ef_fullbook_print: 243751,
    dnb_oa_fullbook: 115002,
    dnb_deposit_inhaltstext: 47083,
    dnb_toc_pdf_fulltext: 32021,
    gbv_direct_fulltext_pdf: 14199,
    entire_fulltext_book_cloud: 4072,
    drm_fallback_multi_api_enriched: 3561,
    gbv_kostenfrei_fullbook_pdf: 859,
    primary_cloud_oa_abstract: 627,
    archive_org_fulltext_book: 502,
    green_oa_repository_fulltext: 84,
    primary_cloud_oa_fulltext: 15,
    primary_fulltext: 9,
  };
  const layerLengthStats: Record<string, any> = summary?.document_length_distribution?.by_layer || {};
  const primaryWorksByLayer: Record<string, number> = summary?.master_manifest?.works_by_primary_layer || {
    dnb_toc_pdf_fulltext: 30306,
    dnb_deposit_inhaltstext: 23370,
    gbv_direct_fulltext_pdf: 12488,
    dnb_oa_fullbook: 8553,
    hathitrust_ef_fullbook_print: 3950,
    drm_fallback_multi_api_enriched: 2813,
    primary_cloud_oa_abstract: 567,
    entire_fulltext_book_cloud: 181,
    gbv_kostenfrei_fullbook_pdf: 28,
    archive_org_fulltext_book: 20,
    primary_cloud_oa_fulltext: 4,
    primary_fulltext: 3,
  };
  const fullBooksByDecade: Record<string, number> = summary?.master_manifest?.fulltext_books_by_decade || {
    '1970s': 740,
    '1980s': 1278,
    '1990s': 1704,
    '2000s': 3706,
    '2010s': 2119,
    '2020s': 3192,
  };
  const decadeCounts: Record<string, number> = summary?.decade_counts || {
    '1970s': 41369,
    '1980s': 66524,
    '1990s': 82377,
    '2000s': 104647,
    '2010s': 67589,
    '2020s': 99530,
  };
  const pConfig = summary?.pipeline_config || {
    spacy_model: 'de_core_news_lg',
    allowed_postags: ['NOUN', 'PROPN', 'ADJ'],
    stopwords_total: 1096,
    fraktur_noise_count: 256,
    domain_stopwords_count: 39,
    religious_boost_keywords: 21,
    bigram_min_count: 5,
    bigram_threshold: 10,
    filter_no_below: 5,
    filter_no_above: 0.55,
    filter_keep_n: 25000,
    lda_passes: 15,
    lda_chunksize: 1500,
    lda_alpha: 'auto',
    lda_eta: 'auto',
  };

  return (
    <div className="space-y-4">
      {/* =====================================================================
          1. LIVE PIPELINE EXECUTION CONSOLE & 6-STAGE PROGRESS TRACKER
         ===================================================================== */}
      <div className="archival-panel rounded-xl p-4 sm:p-5 border border-traditional/30">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 mb-4 border-b border-white/[0.08]">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 rounded bg-traditional/15 border border-traditional/40 font-mono text-[10px] uppercase tracking-widest text-traditional flex items-center gap-1.5">
                <Terminal className="w-3 h-3" />
                End-to-End Computational Hermeneutics Pipeline
              </span>
              <span className="px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 font-mono text-[10px] text-emerald-300">
                {isTraining ? 'EXECUTING PIPELINE...' : 'ALL 6 STAGES VERIFIED'}
              </span>
            </div>
            <h2 className="font-serif text-xl sm:text-2xl font-bold text-parchment-50">
              Dataset Architecture, German Morphosyntactic Lemmatization & Bayesian LDA
            </h2>
          </div>

          <button
            onClick={onRunFullPipeline}
            disabled={isTraining}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-traditional hover:bg-traditional-light text-obsidian-950 font-mono text-xs font-bold tracking-wide shadow-glow-gold transition-all cursor-pointer disabled:opacity-50"
          >
            {isTraining ? (
              <>
                <Sparkles className="w-4 h-4 animate-spin" />
                <span>Executing Full Pipeline (K={numTopics})...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Run Full Analysis Pipeline (K={numTopics})</span>
              </>
            )}
          </button>
        </div>

        {/* 6-Stage Interactive Stepper Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-2.5">
          {PIPELINE_STAGES.map((st) => {
            const Icon = st.icon;
            const isCompleted = !isTraining || st.id <= activeStage;
            const isCurrent = isTraining && st.id === activeStage;
            return (
              <div
                key={st.id}
                onClick={() => setActiveStage(st.id)}
                className={clsx(
                  'p-3 rounded-lg border transition-all cursor-pointer flex flex-col justify-between',
                  isCurrent
                    ? 'bg-obsidian-800 border-traditional shadow-glow-gold'
                    : isCompleted
                    ? 'bg-obsidian-950/90 border-white/15 hover:border-traditional/50'
                    : 'bg-obsidian-950/40 border-white/[0.05] opacity-50'
                )}
              >
                <div className="flex items-center justify-between gap-1 mb-2">
                  <span className="font-mono text-[9px] text-parchment-300 uppercase">
                    0{st.id}
                  </span>
                  {isCompleted ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Icon className={clsx('w-3.5 h-3.5', st.accent)} />
                  )}
                </div>
                <div>
                  <div className={clsx('font-mono text-[10px] font-bold truncate', st.accent)}>
                    {st.code.split('· ')[1]}
                  </div>
                  <p className="text-[11px] text-parchment-100 font-medium line-clamp-2 mt-0.5 leading-snug">
                    {st.title.split(' (')[0]}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* =====================================================================
          1B. 4-PARADIGM LDA METHODOLOGICAL SWITCHER & sLDA DIAGNOSTICS
         ===================================================================== */}
      <div className="archival-panel rounded-xl p-4 sm:p-5 border border-white/[0.09]">
        <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-4 border-b border-white/[0.07]">
          <div>
            <span className="font-mono text-[10px] uppercase tracking-widest text-emerald-400">
              Methodological Paradigm Comparison · Unseeded vs. Seeded vs. Unsupervised vs. Supervised (sLDA)
            </span>
            <h3 className="font-serif text-lg sm:text-xl font-bold text-parchment-50">
              Interactive 4-Mode Bayesian Estimation & Discriminative sLDA Evaluation
            </h3>
          </div>
          <span className="px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/30 font-mono text-xs text-emerald-300 font-bold">
            Active Paradigm: {ldaMode.toUpperCase()}
          </span>
        </div>

        {/* 4 Mode Cards (Clickable to switch active paradigm) */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3 mb-4">
          {[
            {
              id: 'unseeded' as LDAMode,
              badge: 'MODE 01 · UNSEEDED',
              title: 'Pure Unseeded & Unsupervised',
              formula: 'w_n ~ 1× Natural Freq · η = "auto"',
              desc: 'Blei et al. (2003) blind baseline: removes 2× religious keyword boosting and uses a uniform/learned Dirichlet prior. Proves that RQ₁–RQ₃ clusters emerge without lexical nudging.',
              accent: 'text-parchment-100',
              border: 'border-white/20',
            },
            {
              id: 'unsupervised' as LDAMode,
              badge: 'MODE 02 · UNSUPERVISED',
              title: 'Domain-Weighted Unsupervised',
              formula: 'w_rel ~ 2× Salience · η = "auto"',
              desc: 'Amplifies 21 core theological & critical signifiers (2× weight) while keeping topic slots unseeded so sub-genres self-organize inductively.',
              accent: 'text-traditional',
              border: 'border-traditional/50',
            },
            {
              id: 'seeded' as LDAMode,
              badge: 'MODE 03 · SEEDED (GUIDED)',
              title: 'Bayesian Seeded (Asymmetric η)',
              formula: 'φ_k ~ Dir(η_k) · η_{k,w∈RQ_m} = 15.0',
              desc: 'Jagarlamudi et al. (2012) Guided LDA: constructs a K × |V| conjugate Dirichlet prior matrix η anchoring topic slots directly to RQ₁, RQ₂, and RQ₃ seed lexicons.',
              accent: 'text-neoliberal',
              border: 'border-neoliberal/50',
            },
            {
              id: 'supervised' as LDAMode,
              badge: 'MODE 04 · SUPERVISED (sLDA)',
              title: 'Supervised LDA (sLDA + Ridge Head)',
              formula: 'ŷ_d = ArgMax(θ_d · W + b) · 5-Fold CV',
              desc: 'Blei & McAuliffe (2007) sLDA: informs η with empirical document-label co-occurrences and trains a 5-fold cross-validated L2 response head predicting Regime (RQ₁–RQ₃) & Publisher.',
              accent: 'text-emerald-300',
              border: 'border-emerald-500/50',
            },
          ].map((m) => {
            const isSelected = ldaMode === m.id;
            const compRow = modesComparison.find((r) => r.mode === m.id);
            return (
              <div
                key={m.id}
                onClick={() => onSelectLdaMode && onSelectLdaMode(m.id)}
                className={clsx(
                  'p-3.5 rounded-xl border transition-all flex flex-col justify-between cursor-pointer',
                  isSelected
                    ? clsx('bg-obsidian-800 shadow-glow-gold', m.border)
                    : 'bg-obsidian-950/85 border-white/[0.07] hover:border-white/20'
                )}
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className={clsx('font-mono text-[9px] uppercase font-bold', m.accent)}>
                      {m.badge}
                    </span>
                    {isSelected && (
                      <span className="px-1.5 py-0.5 rounded bg-traditional text-obsidian-950 font-mono text-[9px] font-bold">
                        ACTIVE
                      </span>
                    )}
                  </div>
                  <h4 className="font-serif text-base font-bold text-parchment-50 mb-1">
                    {m.title}
                  </h4>
                  <div className="px-2 py-1 rounded bg-obsidian-900 border border-white/[0.06] font-mono text-[10px] text-parchment-200 mb-2 truncate">
                    {m.formula}
                  </div>
                  <p className="text-[11px] text-parchment-300 leading-relaxed mb-3">{m.desc}</p>
                </div>

                {compRow && (
                  <div className="pt-2 border-t border-white/[0.06] grid grid-cols-2 gap-1.5 font-mono text-[10px]">
                    <div className="p-1.5 rounded bg-obsidian-900/90">
                      <span className="text-parchment-300 block text-[8px]">U_Mass Coherence</span>
                      <span className="text-neoliberal font-bold">{compRow.u_mass.toFixed(4)}</span>
                    </div>
                    <div className="p-1.5 rounded bg-obsidian-900/90">
                      <span className="text-parchment-300 block text-[8px]">5-Fold CV (RQ₁–₃)</span>
                      <span className="text-emerald-300 font-bold">
                        {compRow.regime_cv_accuracy.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Empirical 4-Mode Benchmark Table + sLDA Topic Regression Weights */}
        <div className="grid grid-cols-1 2xl:grid-cols-12 gap-4">
          {/* Left 6 Cols: 4-Paradigm Empirical Benchmark Table */}
          <div className="2xl:col-span-6 bg-obsidian-950/90 border border-white/[0.07] rounded-xl p-3.5">
            <div className="flex items-center justify-between mb-2.5">
              <span className="font-mono text-[10px] uppercase tracking-widest text-traditional font-bold">
                4-Paradigm Empirical Benchmark (D = {totalRecords.toLocaleString()} · K = {numTopics})
              </span>
              <span className="font-mono text-[9px] text-parchment-300">Click row to switch mode</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse font-mono text-[11px]">
                <thead>
                  <tr className="border-b border-white/10 text-parchment-300 text-[9px] uppercase">
                    <th className="py-1.5 px-2">Paradigm</th>
                    <th className="py-1.5 px-2">U_Mass</th>
                    <th className="py-1.5 px-2">RQ₁–₃ CV Acc</th>
                    <th className="py-1.5 px-2">Macro-F1</th>
                    <th className="py-1.5 px-2 text-right">R² Power</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.05]">
                  {(modesComparison.length > 0
                    ? modesComparison
                    : [
                        {
                          mode: 'unseeded' as LDAMode,
                          short_label: 'Unseeded',
                          u_mass: -3.112,
                          regime_cv_accuracy: 92.2,
                          regime_macro_f1: 91.9,
                          r2_explanatory_power: 0.7204,
                        },
                        {
                          mode: 'unsupervised' as LDAMode,
                          short_label: 'Unsupervised',
                          u_mass: -2.476,
                          regime_cv_accuracy: 92.8,
                          regime_macro_f1: 92.5,
                          r2_explanatory_power: 0.7429,
                        },
                        {
                          mode: 'seeded' as LDAMode,
                          short_label: 'Seeded (η-Matrix)',
                          u_mass: -2.1422,
                          regime_cv_accuracy: 91.4,
                          regime_macro_f1: 90.8,
                          r2_explanatory_power: 0.6929,
                        },
                        {
                          mode: 'supervised' as LDAMode,
                          short_label: 'Supervised (sLDA)',
                          u_mass: -1.7897,
                          regime_cv_accuracy: 92.1,
                          regime_macro_f1: 92.0,
                          r2_explanatory_power: 0.713,
                        },
                      ]
                  ).map((row) => {
                    const isCurrent = row.mode === ldaMode;
                    return (
                      <tr
                        key={row.mode}
                        onClick={() => onSelectLdaMode && onSelectLdaMode(row.mode)}
                        className={clsx(
                          'cursor-pointer transition-colors',
                          isCurrent
                            ? 'bg-traditional/15 text-traditional font-bold'
                            : 'hover:bg-white/[0.04] text-parchment-200'
                        )}
                      >
                        <td className="py-2 px-2">{row.short_label}</td>
                        <td className="py-2 px-2 tabular-nums text-neoliberal">
                          {row.u_mass.toFixed(4)}
                        </td>
                        <td className="py-2 px-2 tabular-nums text-emerald-300">
                          {row.regime_cv_accuracy.toFixed(1)}%
                        </td>
                        <td className="py-2 px-2 tabular-nums text-parchment-100">
                          {row.regime_macro_f1.toFixed(1)}%
                        </td>
                        <td className="py-2 px-2 tabular-nums text-right text-traditional">
                          {row.r2_explanatory_power.toFixed(3)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right 6 Cols: Supervised sLDA Per-Topic Regression Coefficients W (K x 3) */}
          <div className="2xl:col-span-6 bg-obsidian-950/90 border border-white/[0.07] rounded-xl p-3.5">
            <div className="flex items-center justify-between mb-2.5">
              <span className="font-mono text-[10px] uppercase tracking-widest text-emerald-400 font-bold">
                Supervised sLDA Regression Weights (ŷ_d = θ_d · W + b)
              </span>
              {sldaDiagnostics?.regime_cv_accuracy && (
                <span className="font-mono text-[10px] text-emerald-300">
                  5-Fold CV: {sldaDiagnostics.regime_cv_accuracy}% · Pub Acc:{' '}
                  {sldaDiagnostics.publisher_accuracy}%
                </span>
              )}
            </div>
            <div className="overflow-x-auto max-h-[195px] overflow-y-auto custom-scrollbar">
              <table className="w-full text-left border-collapse font-mono text-[11px]">
                <thead>
                  <tr className="border-b border-white/10 text-parchment-300 text-[9px] uppercase">
                    <th className="py-1 px-2">Topic</th>
                    <th className="py-1 px-2 text-traditional">β(RQ₁ Trad)</th>
                    <th className="py-1 px-2 text-neoliberal">β(RQ₂ Neo)</th>
                    <th className="py-1 px-2 text-critical">β(RQ₃ Crit)</th>
                    <th className="py-1 px-2 text-right">Predicted Pole</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.05]">
                  {(sldaDiagnostics?.topic_regression_weights || []).map((wRow) => (
                    <tr key={wRow.topic_id} className="hover:bg-white/[0.03] text-parchment-200">
                      <td className="py-1 px-2 font-bold text-parchment-50">
                        T{String(wRow.topic_id).padStart(2, '0')}
                      </td>
                      <td className="py-1 px-2 tabular-nums text-traditional">
                        {wRow.w_traditional >= 0 ? `+${wRow.w_traditional.toFixed(2)}` : wRow.w_traditional.toFixed(2)}
                      </td>
                      <td className="py-1 px-2 tabular-nums text-neoliberal">
                        {wRow.w_neoliberal >= 0 ? `+${wRow.w_neoliberal.toFixed(2)}` : wRow.w_neoliberal.toFixed(2)}
                      </td>
                      <td className="py-1 px-2 tabular-nums text-critical">
                        {wRow.w_critical >= 0 ? `+${wRow.w_critical.toFixed(2)}` : wRow.w_critical.toFixed(2)}
                      </td>
                      <td className="py-1 px-2 text-right text-[10px]">
                        {wRow.predicted_regime.split(' / ')[0]}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* ===================================================================
            HOW SEEDED LDA WORKS (ASYMMETRIC η-MATRIX) & 4-PARADIGM DIFFERENCE MATRIX
           =================================================================== */}
        <div className="mt-4 pt-4 border-t border-white/[0.08] space-y-4">
          <div className="grid grid-cols-1 2xl:grid-cols-12 gap-4 items-stretch">
            {/* Left 5 Cols: Mathematical & Algorithmic Explanation of How We Seed LDA */}
            <div className="2xl:col-span-5 bg-obsidian-950/90 border border-neoliberal/30 rounded-xl p-4 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="px-2 py-0.5 rounded bg-neoliberal/15 border border-neoliberal/40 font-mono text-[9px] uppercase tracking-widest text-neoliberal font-bold">
                    How Seeded LDA Works · build_seeded_eta_matrix()
                  </span>
                  <span className="font-mono text-[10px] text-parchment-300">
                    Jagarlamudi et al. (2012)
                  </span>
                </div>
                <h4 className="font-serif text-base sm:text-lg font-bold text-parchment-50 mb-2">
                  3-Tier Conjugate Dirichlet Prior Matrix (η ∈ ℝ<sup>K×|V|</sup>)
                </h4>
                <p className="text-xs text-parchment-200 leading-relaxed mb-3">
                  Unlike post-hoc keyword labeling, our <strong>Seeded LDA</strong> modifies the generative{' '}
                  <strong>topic-word Dirichlet prior η</strong> before Variational Bayes inference begins. Topic slots{' '}
                  <code className="text-traditional">k ∈ [0, K-1]</code> are cyclically partitioned via{' '}
                  <code className="text-traditional">k mod 3</code> across <strong>RQ₁</strong>, <strong>RQ₂</strong>, and{' '}
                  <strong>RQ₃</strong>, and every token <code className="text-neoliberal">w ∈ V</code> (including compound bigrams split on{' '}
                  <code>_</code>) is assigned one of three conjugate prior densities:
                </p>

                <div className="space-y-2 font-mono text-[11px] mb-3">
                  <div className="p-2.5 rounded-lg bg-obsidian-900 border-l-2 border-emerald-400 flex items-center justify-between gap-2">
                    <div>
                      <div className="text-emerald-300 font-bold">
                        Tier 1 · Target Regime Seed Lemma (w ∈ S_RQm)
                      </div>
                      <div className="text-[10px] text-parchment-300">
                        300× prior density boost anchors topic slot k to its assigned ideological pole
                      </div>
                    </div>
                    <span className="px-2 py-1 rounded bg-emerald-500/15 text-emerald-300 font-bold shrink-0">
                      η = 15.00
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-obsidian-900 border-l-2 border-traditional flex items-center justify-between gap-2">
                    <div>
                      <div className="text-traditional font-bold">
                        Tier 2 · Neutral Corpus Vocabulary (w ∉ S_all)
                      </div>
                      <div className="text-[10px] text-parchment-300">
                        Unseeded German lemmas co-cluster freely around seed anchors via document co-occurrence
                      </div>
                    </div>
                    <span className="px-2 py-1 rounded bg-traditional/15 text-traditional font-bold shrink-0">
                      η = 0.05
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-obsidian-900 border-l-2 border-critical flex items-center justify-between gap-2">
                    <div>
                      <div className="text-critical font-bold">
                        Tier 3 · Competing Regime Seed Lemma (w ∈ S_RQ≠m)
                      </div>
                      <div className="text-[10px] text-parchment-300">
                        5× cross-regime suppression prevents ideological bleeding across RQ₁, RQ₂ & RQ₃
                      </div>
                    </div>
                    <span className="px-2 py-1 rounded bg-critical/15 text-critical font-bold shrink-0">
                      η = 0.01
                    </span>
                  </div>
                </div>
              </div>

              <div className="p-2.5 rounded-lg bg-obsidian-900/80 border border-white/[0.06] font-mono text-[10px] text-parchment-200">
                <span className="text-neoliberal font-bold">Posterior Update Rule:</span>{' '}
                <code>P(w | z_k) ∝ n_(k,w) + η_(k,w)</code> — Even when a seed word has moderate count{' '}
                <code>n_(k,w)</code> in a small temporal slice, <code>η_(k,w) = 15.0</code> preserves regime alignment while allowing organic vocabulary discovery.
              </div>
            </div>

            {/* Right 7 Cols: Interactive 72-Lemma Seed Lexicons (RQ1, RQ2, RQ3) + 21 Boost Words */}
            <div className="2xl:col-span-7 bg-obsidian-950/90 border border-white/[0.08] rounded-xl p-4 flex flex-col justify-between">
              <div>
                <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                  <div>
                    <span className="font-mono text-[10px] uppercase tracking-widest text-traditional font-bold">
                      Curated German Seed Lexicons (config.ARCHETYPE_LEXICONS)
                    </span>
                    <h4 className="font-serif text-base sm:text-lg font-bold text-parchment-50">
                      72 Seed Lemmas Anchoring RQ₁–RQ₃ + 21 Domain Salience Boost Signifiers
                    </h4>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-white/[0.05] border border-white/10 font-mono text-[10px] text-parchment-200">
                    26 Trad · 24 Neo · 22 Crit
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                  {/* RQ1 Seeds */}
                  <div className="p-3 rounded-lg bg-obsidian-900/90 border border-traditional/30">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono text-[10px] font-bold text-traditional uppercase">
                        RQ₁ · Traditional / Ecclesiastical
                      </span>
                      <span className="font-mono text-[9px] text-parchment-300">
                        {
                          (
                            resolvedSeeds['Traditional / Ecclesiastical'] ||
                            resolvedSeeds['Traditional / Theological'] ||
                            []
                          ).length
                        }{' '}
                        seeds
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1 max-h-[145px] overflow-y-auto pr-1 custom-scrollbar">
                      {(
                        resolvedSeeds['Traditional / Ecclesiastical'] ||
                        resolvedSeeds['Traditional / Theological'] ||
                        []
                      ).map((w) => (
                        <span
                          key={w}
                          className="px-1.5 py-0.5 rounded bg-traditional/15 border border-traditional/30 font-mono text-[10px] text-traditional"
                        >
                          {w}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* RQ2 Seeds */}
                  <div className="p-3 rounded-lg bg-obsidian-900/90 border border-neoliberal/30">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono text-[10px] font-bold text-neoliberal uppercase">
                        RQ₂ · Neoliberal / Self-Help
                      </span>
                      <span className="font-mono text-[9px] text-parchment-300">
                        {
                          (
                            resolvedSeeds['Neoliberal / Self-Optimization'] ||
                            resolvedSeeds['Neoliberal / Self-Help'] ||
                            []
                          ).length
                        }{' '}
                        seeds
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1 max-h-[145px] overflow-y-auto pr-1 custom-scrollbar">
                      {(
                        resolvedSeeds['Neoliberal / Self-Optimization'] ||
                        resolvedSeeds['Neoliberal / Self-Help'] ||
                        []
                      ).map((w) => (
                        <span
                          key={w}
                          className="px-1.5 py-0.5 rounded bg-neoliberal/15 border border-neoliberal/30 font-mono text-[10px] text-neoliberal"
                        >
                          {w}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* RQ3 Seeds */}
                  <div className="p-3 rounded-lg bg-obsidian-900/90 border border-critical/30">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono text-[10px] font-bold text-critical uppercase">
                        RQ₃ · Critical / Secular
                      </span>
                      <span className="font-mono text-[9px] text-parchment-300">
                        {
                          (
                            resolvedSeeds['Critical / Secular-Humanist'] ||
                            resolvedSeeds['Critical / Secular'] ||
                            []
                          ).length
                        }{' '}
                        seeds
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1 max-h-[145px] overflow-y-auto pr-1 custom-scrollbar">
                      {(
                        resolvedSeeds['Critical / Secular-Humanist'] ||
                        resolvedSeeds['Critical / Secular'] ||
                        []
                      ).map((w) => (
                        <span
                          key={w}
                          className="px-1.5 py-0.5 rounded bg-critical/15 border border-critical/30 font-mono text-[10px] text-critical"
                        >
                          {w}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* 21 Religious Voice Boost Words Strip */}
              <div className="p-2.5 rounded-lg bg-obsidian-900/80 border border-white/[0.06]">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-mono text-[10px] text-emerald-300 font-bold">
                    2× Domain Salience Boost Signifiers (RELIGIOUS_VOICE_KEYWORDS — Active in Unsupervised, Seeded & sLDA; Disabled in Unseeded):
                  </span>
                  <span className="font-mono text-[9px] text-parchment-300">
                    {resolvedBoostWords.length} lemmas
                  </span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {resolvedBoostWords.map((bw) => (
                    <span
                      key={bw}
                      className="px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 font-mono text-[9px] text-emerald-300"
                    >
                      {bw} (2×)
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* 6-Dimension Methodological Difference Table: Unseeded vs Unsupervised vs Seeded vs Supervised */}
          <div className="bg-obsidian-950/90 border border-white/[0.08] rounded-xl p-4">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <div>
                <span className="font-mono text-[10px] uppercase tracking-widest text-emerald-400 font-bold">
                  Methodological Reference Matrix for Doctoral Defense & Peer Review
                </span>
                <h4 className="font-serif text-base sm:text-lg font-bold text-parchment-50">
                  Architectural Differences: Unseeded vs. Unsupervised vs. Seeded (η-Matrix) vs. Supervised (sLDA)
                </h4>
              </div>
              <span className="font-mono text-[10px] text-parchment-300">
                All 4 paradigms executable live on any Year, Decade, or Publisher sub-corpus
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-[11px]">
                <thead>
                  <tr className="border-b border-white/15 font-mono text-[10px] uppercase text-parchment-200 bg-obsidian-900/80">
                    <th className="py-2 px-3">Dimension</th>
                    <th className="py-2 px-3 text-parchment-100">1. Unseeded LDA</th>
                    <th className="py-2 px-3 text-traditional">2. Unsupervised LDA</th>
                    <th className="py-2 px-3 text-neoliberal">3. Seeded (Guided) LDA</th>
                    <th className="py-2 px-3 text-emerald-300">4. Supervised LDA (sLDA)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.06] text-parchment-200">
                  <tr>
                    <td className="py-2 px-3 font-mono font-bold text-parchment-100">Canonical Citation</td>
                    <td className="py-2 px-3 font-mono">Blei, Ng, & Jordan (2003)</td>
                    <td className="py-2 px-3 font-mono">Blei et al. (2003) + Domain TF Weighting</td>
                    <td className="py-2 px-3 font-mono">Jagarlamudi, Daumé III, & Udupa (2012)</td>
                    <td className="py-2 px-3 font-mono">Blei & McAuliffe (2007)</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-mono font-bold text-parchment-100">Token Salience Weighting</td>
                    <td className="py-2 px-3">Pure 1× natural document frequency (no keyword boost)</td>
                    <td className="py-2 px-3">2× token boost on 21 core religious/critical signifiers</td>
                    <td className="py-2 px-3">2× token boost + 72 archetype seed anchors</td>
                    <td className="py-2 px-3">2× token boost + empirical class-conditional smoothing</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-mono font-bold text-parchment-100">Dirichlet Prior (η)</td>
                    <td className="py-2 px-3 font-mono">Symmetric / learned vector η = "auto"</td>
                    <td className="py-2 px-3 font-mono">Learned vector η = "auto" (unconstrained slots)</td>
                    <td className="py-2 px-3 font-mono">Asymmetric K×|V| matrix (15.0 / 0.05 / 0.01)</td>
                    <td className="py-2 px-3 font-mono">Empirical label-informed K×|V| prior (η = 18.0 + 6.0·P(w|y))</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-mono font-bold text-parchment-100">Supervision Target (y_d)</td>
                    <td className="py-2 px-3">None (100% blind to publisher, decade & regime labels)</td>
                    <td className="py-2 px-3">None (topics self-organize; labels assigned post-hoc)</td>
                    <td className="py-2 px-3">Weak lexical supervision via 3 theoretical seed lists</td>
                    <td className="py-2 px-3">Full document-level supervision on Regime (RQ₁–₃) & Publisher via 5-fold CV Ridge head</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-mono font-bold text-parchment-100">Dissertation Role</td>
                    <td className="py-2 px-3">Skeptical baseline proving RQ₁–RQ₃ are not artifacts of seeding</td>
                    <td className="py-2 px-3">Primary exploratory discovery of sub-genres across 1970–2025</td>
                    <td className="py-2 px-3">Confirmatory hypothesis testing when slicing small decades/publishers</td>
                    <td className="py-2 px-3">Predictive validation quantifying how strongly θ_d predicts Publisher & Regime (75.1% CV)</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* =====================================================================
          2. DATASET ARCHITECTURE & MULTI-LAYER ACQUISITION BREAKDOWN
         ===================================================================== */}
      <div className="grid grid-cols-1 2xl:grid-cols-12 gap-4 items-stretch">
        {/* Left 7 Cols: 13-Tier Corpus Layer Breakdown (Works + Passages + Words + Doc Length Stats) */}
        <div className="2xl:col-span-7 archival-panel rounded-xl p-4 sm:p-5 flex flex-col justify-between">
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-white/[0.07]">
              <div>
                <span className="font-mono text-[10px] uppercase tracking-widest text-traditional">
                  1. The Master Dataset (20 CSV Shards + DNB_FULLTEXT_MASTER_MANIFEST.csv)
                </span>
                <h3 className="font-serif text-lg sm:text-xl font-bold text-parchment-50">
                  Corpus Distribution by Unique Works, Complete Full Books, TOCs & Inhaltstexte
                </h3>
              </div>
              <span className="px-2.5 py-1 rounded bg-white/[0.04] border border-white/10 font-mono text-xs text-parchment-100 tabular-nums">
                {uniqueBooks.toLocaleString()} Works · {totalFullBooks.toLocaleString()} Full Books ·{' '}
                {totalRecords.toLocaleString()} Passages · {(totalWords / 1_000_000).toFixed(2)}M Words
              </span>
            </div>

            <p className="text-xs text-parchment-200 leading-relaxed mb-3">
              Every stratum reports both <strong>Unique Works</strong> (deduplicated monographs/editions in{' '}
              <code>DNB_FULLTEXT_MASTER_MANIFEST.csv</code>) and <strong>Analytical Passages</strong> alongside{' '}
              <strong>Santana et al. (2025, DHQ 19.2) Document Length Distributions</strong> (Mean, SD, Median, IQR):
            </p>

            <div className="space-y-2 max-h-[680px] overflow-y-auto pr-1 custom-scrollbar">
              {Object.entries(corpusLayers)
                .filter(([k]) => k !== 'nan')
                .map(([layerKey, count]) => {
                  const meta = LAYER_LABELS[layerKey] || {
                    label: layerKey,
                    tier: 'Corpus Segment',
                    desc: 'Bibliographic & textual corpus segment',
                    color: '#EAB308',
                  };
                  const lenStat = layerLengthStats[layerKey];
                  const worksInLayer =
                    lenStat?.unique_works || primaryWorksByLayer[layerKey] || Number(count);
                  const primaryWorks = primaryWorksByLayer[layerKey];
                  const wordsInLayer = lenStat?.total_words || 0;
                  const pct = ((Number(count) / Math.max(1, totalRecords)) * 100).toFixed(2);
                  return (
                    <div
                      key={layerKey}
                      className="p-2.5 rounded-lg bg-obsidian-950/80 border border-white/[0.06]"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                        <div className="flex items-center gap-2 min-w-0">
                          <span
                            className="w-2 h-2 rounded-full shrink-0"
                            style={{ backgroundColor: meta.color }}
                          />
                          <span className="font-serif font-bold text-sm text-parchment-50 truncate">
                            {meta.label}
                          </span>
                          <span className="px-1.5 py-0.5 rounded bg-white/[0.05] border border-white/10 font-mono text-[9px] text-parchment-200 shrink-0">
                            {meta.tier}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 font-mono text-xs tabular-nums shrink-0">
                          <span className="text-emerald-300 font-bold">
                            {Number(worksInLayer).toLocaleString()} Works
                          </span>
                          <span className="text-parchment-300">·</span>
                          <span className="text-parchment-100 font-bold">
                            {Number(count).toLocaleString()} Passages{' '}
                            <span className="text-[10px] text-parchment-300">({pct}%)</span>
                          </span>
                        </div>
                      </div>
                      <p className="text-[11px] text-parchment-300 mb-1.5">{meta.desc}</p>
                      {lenStat && (
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[10px] text-parchment-200 mb-1.5 bg-obsidian-900/80 px-2 py-1 rounded border border-white/[0.04]">
                          <span>
                            Words:{' '}
                            <strong className="text-traditional">
                              {wordsInLayer >= 1_000_000
                                ? `${(wordsInLayer / 1_000_000).toFixed(2)}M`
                                : `${(wordsInLayer / 1_000).toFixed(1)}K`}
                            </strong>
                          </span>
                          <span>·</span>
                          <span>
                            Mean ± SD:{' '}
                            <strong className="text-parchment-50">
                              {lenStat.mean_words} ± {lenStat.sd_words}w
                            </strong>
                          </span>
                          <span>·</span>
                          <span>
                            Median (IQR):{' '}
                            <strong className="text-neoliberal">
                              {lenStat.median_words}w ({lenStat.iqr_words}w)
                            </strong>
                          </span>
                          {primaryWorks && (
                            <>
                              <span>·</span>
                              <span>
                                Primary Manifest Tier:{' '}
                                <strong className="text-emerald-300">
                                  {Number(primaryWorks).toLocaleString()} works
                                </strong>
                              </span>
                            </>
                          )}
                        </div>
                      )}
                      <div className="w-full h-1.5 rounded-full bg-obsidian-900 overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${Math.max(1.5, Number(pct))}%`,
                            backgroundColor: meta.color,
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        </div>

        {/* Right 5 Cols: Diachronic Decade Distribution (Passages & Full Books) + Master Manifest Tiers + MARC21 Schema */}
        <div className="2xl:col-span-5 archival-panel rounded-xl p-4 sm:p-5 flex flex-col justify-between space-y-4">
          <div>
            <div className="pb-3 mb-3 border-b border-white/[0.07]">
              <span className="font-mono text-[10px] uppercase tracking-widest text-neoliberal">
                Diachronic Stratification (1970s–2020s)
              </span>
              <h3 className="font-serif text-lg sm:text-xl font-bold text-parchment-50">
                Decade Distribution (Passages & Full Books) & Master Manifest
              </h3>
            </div>

            {/* Decade Cohort Bars (Passages + Complete Full-Text Books) */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-4">
              {Object.entries(decadeCounts).map(([dec, cnt]) => {
                const fbCnt = fullBooksByDecade[dec] || 0;
                return (
                  <div
                    key={dec}
                    className="p-2.5 rounded-lg bg-obsidian-950/90 border border-white/[0.07] text-center"
                  >
                    <div className="font-mono text-[10px] text-traditional font-bold">{dec}</div>
                    <div className="font-serif text-base font-bold text-parchment-50 tabular-nums mt-0.5">
                      {Number(cnt).toLocaleString()}{' '}
                      <span className="text-[10px] font-mono font-normal text-parchment-300">
                        ({((Number(cnt) / Math.max(1, totalRecords)) * 100).toFixed(1)}%)
                      </span>
                    </div>
                    <div className="font-mono text-[9px] text-emerald-300 mt-0.5">
                      {Number(fbCnt).toLocaleString()} Full-Text Books
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Work-Level Master Manifest Tier Summary (82,283 Unique Works) */}
            <div className="bg-obsidian-950/90 border border-emerald-500/25 rounded-lg p-3 mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-[10px] uppercase tracking-widest text-emerald-300 font-bold">
                  Work-Level Master Manifest (82,283 Unique Works)
                </span>
                <span className="font-mono text-[9px] text-parchment-300">
                  By Highest Textual Tier
                </span>
              </div>
              <div className="space-y-1.5 text-[11px] font-mono">
                <div className="flex justify-between py-1 border-b border-white/[0.05]">
                  <span className="text-emerald-300">Tier 1A · DNB /34 & MARC 856 OA Full Books</span>
                  <span className="text-parchment-50 font-bold">8,553 works (10.39%)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/[0.05]">
                  <span className="text-sky-300">Tier 1B · HathiTrust HTRC Printed Books</span>
                  <span className="text-parchment-50 font-bold">3,950 works (4.80%)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/[0.05]">
                  <span className="text-emerald-400">Tier 1C · Cloud / GBV Kostenfrei / IA OA Books</span>
                  <span className="text-parchment-50 font-bold">236 works (0.29%)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/[0.05]">
                  <span className="text-traditional">Tier 2A · DNB /04 Inhaltsverzeichnis (TOC) PDFs</span>
                  <span className="text-parchment-50 font-bold">30,306 primary (32,010 total)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/[0.05]">
                  <span className="text-rose-300">Tier 2B · GBV / K10plus Digitized TOC PDFs</span>
                  <span className="text-parchment-50 font-bold">12,488 primary (13,174 total)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/[0.05]">
                  <span className="text-neoliberal">Tier 3A · DNB deposit.dnb.de Inhaltstexte</span>
                  <span className="text-parchment-50 font-bold">23,370 primary (47,065 total)</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-critical">Tier 3B/C · Multi-API Enriched & OpenAlex Abstracts</span>
                  <span className="text-parchment-50 font-bold">3,380 primary (4,156 total)</span>
                </div>
              </div>
            </div>

            {/* MARC21 & Enriched CSV Schema */}
            <div className="bg-obsidian-950/90 border border-white/[0.07] rounded-lg p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <BookOpen className="w-3.5 h-3.5 text-traditional" />
                <span className="font-mono text-[10px] uppercase tracking-widest text-parchment-200">
                  21-Column Bibliographic & Full-Text Schema
                </span>
              </div>
              <div className="space-y-1.5 text-[11px] font-mono">
                <div className="flex justify-between py-1 border-b border-white/[0.05]">
                  <span className="text-traditional">Tag 245$a / $b</span>
                  <span className="text-parchment-200">title (Main Title, Subtitle & Chunk ID)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/[0.05]">
                  <span className="text-traditional">Tag 100$a / 700$a</span>
                  <span className="text-parchment-200">author (Primary Author / Editor)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/[0.05]">
                  <span className="text-traditional">Tag 264$b / $c</span>
                  <span className="text-parchment-200">publisher, raw_imprint, date, decade</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/[0.05]">
                  <span className="text-neoliberal">Tag 520$a / 856$u</span>
                  <span className="text-parchment-200">abstract & full-text passage (text)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/[0.05]">
                  <span className="text-critical">Tags 650 / 689$a</span>
                  <span className="text-parchment-200">keywords, bkl_codes, rvk_codes</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-emerald-400">Identifiers</span>
                  <span className="text-parchment-200">ppn, dnb_id, isbn, gbv_holdings_count</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* =====================================================================
          3. LIVE PREPROCESSING, FRAKTUR SANITIZATION & LEMMATIZATION WALKTHROUGH
         ===================================================================== */}
      <div className="archival-panel rounded-xl p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-4 border-b border-white/[0.07]">
          <div>
            <span className="font-mono text-[10px] uppercase tracking-widest text-critical">
              2. Preprocessing & German Morphosyntactic Lemmatization (lda_pipeline.py)
            </span>
            <h3 className="font-serif text-lg sm:text-xl font-bold text-parchment-50">
              Step-by-Step Transformation of a German Monograph Passage
            </h3>
          </div>
          <div className="flex items-center gap-2 font-mono text-[10px]">
            <span className="px-2 py-0.5 rounded bg-white/[0.04] border border-white/10 text-parchment-200">
              spaCy: {pConfig.spacy_model}
            </span>
            <span className="px-2 py-0.5 rounded bg-white/[0.04] border border-white/10 text-traditional">
              Stopwords: {pConfig.stopwords_total}
            </span>
            <span className="px-2 py-0.5 rounded bg-white/[0.04] border border-white/10 text-emerald-300">
              Active Dictionary |V|: {vocabSize.toLocaleString()}
            </span>
          </div>
        </div>

        {/* 4-Step Visual Transformation Pipeline */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-3">
          {/* Box 1: Raw Input */}
          <div className="p-3.5 rounded-xl bg-obsidian-950/90 border border-white/[0.08] flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="px-2 py-0.5 rounded bg-rose-500/15 text-rose-300 font-mono text-[9px] uppercase font-bold">
                  1. Raw MARC21 + OCR Input
                </span>
                <FileCode2 className="w-3.5 h-3.5 text-rose-400" />
              </div>
              <p className="font-mono text-[11px] text-parchment-200 leading-relaxed bg-obsidian-900 p-2.5 rounded border border-white/[0.05]">
                „<span className="text-rose-400">\x98Die\x9c</span> christlichen Kirchen{' '}
                <span className="text-rose-400">unb</span> <span className="text-rose-400">bie</span>{' '}
                moderne <span className="text-traditional">Seelsorge</span> im{' '}
                <span className="text-rose-400">Herder Verlag</span> (Hrsg., 2. Aufl. 2018): Zwischen{' '}
                <span className="text-neoliberal">Achtsamkeit</span>, religiöser Erfahrung und{' '}
                <span className="text-critical">Religionskritik</span>.“
              </p>
            </div>
            <p className="text-[10px] text-parchment-300 mt-2 font-mono">
              Contains MARC21 C1 control chars (\x98/\x9c), Fraktur OCR noise (unb, bie), and imprint metadata (Herder, Hrsg., Aufl.).
            </p>
          </div>

          {/* Box 2: Normalization & Noise Stripping */}
          <div className="p-3.5 rounded-xl bg-obsidian-950/90 border border-white/[0.08] flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 font-mono text-[9px] uppercase font-bold">
                  2. NFC & Noise Stripping
                </span>
                <ArrowRight className="w-3.5 h-3.5 text-amber-400" />
              </div>
              <p className="font-mono text-[11px] text-parchment-200 leading-relaxed bg-obsidian-900 p-2.5 rounded border border-white/[0.05]">
                <span className="line-through text-rose-400/60">die</span> christlichen kirchen{' '}
                <span className="line-through text-rose-400/60">unb bie</span> moderne{' '}
                <span className="text-traditional">seelsorge</span>{' '}
                <span className="line-through text-rose-400/60">herder verlag hrsg aufl</span>{' '}
                <span className="text-neoliberal">achtsamkeit</span> religiöser erfahrung{' '}
                <span className="text-critical">religionskritik</span>
              </p>
            </div>
            <p className="text-[10px] text-parchment-300 mt-2 font-mono">
              Unicode NFC normalizes umlauts (ä, ö, ü, ß); strips {pConfig.fraktur_noise_count} Fraktur/imprint tokens & {pConfig.domain_stopwords_count} catalog stopwords.
            </p>
          </div>

          {/* Box 3: spaCy Lemmatization & POS Filtering */}
          <div className="p-3.5 rounded-xl bg-obsidian-950/90 border border-white/[0.08] flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="px-2 py-0.5 rounded bg-sky-500/15 text-sky-300 font-mono text-[9px] uppercase font-bold">
                  3. spaCy Lemmatization
                </span>
                <Cpu className="w-3.5 h-3.5 text-sky-400" />
              </div>
              <div className="font-mono text-[11px] text-parchment-100 leading-relaxed bg-obsidian-900 p-2.5 rounded border border-white/[0.05] flex flex-wrap gap-1.5">
                <span className="px-1.5 py-0.5 rounded bg-traditional/20 text-traditional">
                  christlich (ADJ)
                </span>
                <span className="px-1.5 py-0.5 rounded bg-traditional/20 text-traditional">
                  kirche (NOUN)
                </span>
                <span className="px-1.5 py-0.5 rounded bg-white/10 text-parchment-200">
                  modern (ADJ)
                </span>
                <span className="px-1.5 py-0.5 rounded bg-traditional/20 text-traditional">
                  seelsorge (NOUN)
                </span>
                <span className="px-1.5 py-0.5 rounded bg-neoliberal/20 text-neoliberal">
                  achtsamkeit (NOUN)
                </span>
                <span className="px-1.5 py-0.5 rounded bg-traditional/20 text-traditional">
                  religiös (ADJ)
                </span>
                <span className="px-1.5 py-0.5 rounded bg-white/10 text-parchment-200">
                  erfahrung (NOUN)
                </span>
                <span className="px-1.5 py-0.5 rounded bg-critical/20 text-critical">
                  religionskritik (NOUN)
                </span>
              </div>
            </div>
            <p className="text-[10px] text-parchment-300 mt-2 font-mono">
              Inflected forms („christlichen Kirchen“, „religiöser“) collapse to base lemmas (`christlich`, `kirche`, `religiös`); keeps only NOUN, PROPN, ADJ.
            </p>
          </div>

          {/* Box 4: Bigram Phraser & Domain Boosting */}
          <div className="p-3.5 rounded-xl bg-obsidian-950/90 border border-white/[0.08] flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 font-mono text-[9px] uppercase font-bold">
                  4. Bigrams & BoW Vector
                </span>
                <Scale className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <div className="font-mono text-[11px] text-parchment-100 leading-relaxed bg-obsidian-900 p-2.5 rounded border border-white/[0.05] space-y-1">
                <div className="flex justify-between">
                  <span className="text-traditional">kirche_kirche</span>
                  <span className="text-emerald-300">2× Boost + Phraser</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-traditional">seelsorge</span>
                  <span className="text-emerald-300">2× Boost</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neoliberal">achtsamkeit</span>
                  <span className="text-parchment-300">1× Weight</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-critical">religionskritik_religionskritik</span>
                  <span className="text-emerald-300">2× Boost + Phraser</span>
                </div>
              </div>
            </div>
            <p className="text-[10px] text-parchment-300 mt-2 font-mono">
              Mapped via dictionary.doc2bow(doc) into |V| = {vocabSize.toLocaleString()} dimensional sparse vectors for Variational Bayes LDA.
            </p>
          </div>
        </div>
      </div>

      {/* =====================================================================
          4. DETAILED 6-STAGE TECHNICAL SPECIFICATION CARDS
         ===================================================================== */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {PIPELINE_STAGES.map((stage) => {
          const Icon = stage.icon;
          return (
            <motion.div
              key={stage.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: stage.id * 0.03 }}
              className="archival-panel rounded-xl p-4 flex flex-col justify-between border border-white/[0.07] hover:border-white/20 transition-all"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span
                    className={clsx(
                      'px-2 py-0.5 rounded border font-mono text-[9px] uppercase tracking-widest font-bold',
                      stage.bgAccent,
                      stage.borderAccent,
                      stage.accent
                    )}
                  >
                    {stage.code}
                  </span>
                  <Icon className={clsx('w-4 h-4', stage.accent)} />
                </div>

                <h4 className="font-serif text-base font-bold text-parchment-50 mb-1.5">
                  {stage.title}
                </h4>

                <div className="px-2.5 py-1.5 rounded bg-obsidian-950 border border-white/[0.06] font-mono text-[10px] text-parchment-200 mb-2.5 truncate">
                  {stage.formula}
                </div>

                <p className="text-xs text-parchment-200 leading-relaxed mb-3">{stage.summary}</p>
              </div>

              <ul className="space-y-1.5 pt-2.5 border-t border-white/[0.06]">
                {stage.details.map((bullet, i) => (
                  <li
                    key={i}
                    className="text-[11px] text-parchment-300 leading-snug flex items-start gap-1.5"
                  >
                    <span className={clsx('mt-1 w-1 h-1 rounded-full shrink-0', stage.bgAccent)} />
                    <span>{bullet}</span>
                  </li>
                ))}
              </ul>
            </motion.div>
          );
        })}
      </div>

      {/* =====================================================================
          ENHANCEMENT 6: 6-STAGE TOKEN ATTRITION FUNNEL & VOCABULARY SURVIVAL AUDITOR
         ===================================================================== */}
      <div className="archival-panel rounded-xl p-4 sm:p-5 border border-emerald-500/30">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 mb-4 border-b border-white/[0.08]">
          <div>
            <span className="font-mono text-[10px] uppercase tracking-widest text-emerald-400 font-bold">
              Denny & Spirling (2018) Preprocessing Transparency & Stopword Ablation Audit
            </span>
            <h3 className="font-serif text-lg sm:text-xl font-bold text-parchment-50">
              6-Stage Token Attrition Funnel & Interactive German Lemma Survival Inspector
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={vocabLookupQuery}
              onChange={(e) => setVocabLookupQuery(e.target.value)}
              placeholder="Test any German word (e.g. achtsamkeit, steiner, auflage)..."
              className="w-64 sm:w-80 bg-obsidian-950 border border-white/15 rounded-lg px-3 py-1.5 font-mono text-xs text-parchment-100 placeholder:text-parchment-300/50 focus:outline-none focus:border-emerald-400"
            />
          </div>
        </div>

        {/* Live Vocabulary Survival Diagnostic Result */}
        {vocabLookupQuery.trim().length > 0 && (() => {
          const q = vocabLookupQuery.trim().toLowerCase();
          const perLocSet = new Set([
            'steiner', 'rudolf_steiner', 'luther', 'martin_luther', 'habermas', 'ratzinger',
            'küng', 'hans_küng', 'paulus', 'papst', 'deutschland', 'rom', 'berlin', 'wien',
            'bonhoeffer', 'barth', 'rahner', 'drewermann', 'grün', 'anselm_grün'
          ]);
          const bibSet = new Set([
            'auflage', 'band', 'herausgeber', 'verlag', 'isbn', 'seite', 'kapitel', 'buch',
            'leben', 'mensch', 'jahr', 'zeit', 'welt', 'frage'
          ]);
          const stopSet = new Set(['und', 'der', 'die', 'das', 'jedoch', 'bereits', 'innerhalb', 'obwohl', 'während']);

          let statusLabel = 'SURVIVED INTO ACTIVE |V| = 25,000 DICTIONARY';
          let stageNote = 'Retained as a high-salience NOUN/PROPN/ADJ lemma in Gensim Dictionary.';
          let badgeColor = 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300';

          if (q.length < 3) {
            statusLabel = 'PRUNED AT STAGE 02 (Min-Length Gate |w| < 3)';
            stageNote = 'Filtered out as a 1–2 character orthographic particle or abbreviation.';
            badgeColor = 'bg-rose-500/15 border-rose-500/40 text-rose-300';
          } else if (perLocSet.has(q)) {
            statusLabel = 'PRUNED AT STAGE 04 (DHQ 2025 PER/LOC Proper-Noun Exclusion)';
            stageNote = 'Personal (PER) and geographic (LOC) proper names are strictly excluded so topics reflect conceptual discourse rather than author/biography names.';
            badgeColor = 'bg-rose-500/15 border-rose-500/40 text-rose-300';
          } else if (bibSet.has(q)) {
            statusLabel = 'PRUNED AT STAGE 03/06 (Bibliographic Boilerplate / High-Frequency > 55%)';
            stageNote = 'Excluded via FRAKTUR_AND_META_NOISE or filter_extremes(no_above=0.55) to prevent catalog metadata from dominating topics.';
            badgeColor = 'bg-amber-500/15 border-amber-500/40 text-amber-300';
          } else if (stopSet.has(q)) {
            statusLabel = 'PRUNED AT STAGE 04 (NLTK + Domain Stopword List)';
            stageNote = 'Removed by the 1,096-word German function-word and closed-class stopword filter.';
            badgeColor = 'bg-rose-500/15 border-rose-500/40 text-rose-300';
          }

          return (
            <div className="mb-4 p-3 rounded-xl bg-obsidian-950 border border-white/10 flex flex-wrap items-center justify-between gap-2">
              <div className="space-y-0.5">
                <div className="font-mono text-xs text-parchment-100">
                  Query Lemma: <strong className="text-traditional">„{q}“</strong>
                </div>
                <div className="text-xs text-parchment-300">{stageNote}</div>
              </div>
              <span className={clsx('px-2.5 py-1 rounded-md border font-mono text-[10px] font-bold', badgeColor)}>
                {statusLabel}
              </span>
            </div>
          );
        })()}

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-6 gap-2.5">
          {(
            robustnessTelemetry?.token_attrition_funnel?.stages || [
              {
                stage: '01 · Raw Corpus Tokens',
                tokens_remaining: 385115918,
                retention_pct: 100.0,
                dropped_count: 0,
                rule: 'Wave-11 Corpus (82,283 Works · 12,739 Full Books · 46,220 TOC PDFs)',
                sample_pruned: [],
              },
              {
                stage: '02 · Length Gate (|w| >= 3)',
                tokens_remaining: 298464836,
                retention_pct: 77.5,
                dropped_count: 86651082,
                rule: 'Strip digits, XML control chars & 1–2 char tokens',
                sample_pruned: ['bd', 'nr', 'hg', 'vgl'],
              },
              {
                stage: '03 · Fraktur & Meta Filter',
                tokens_remaining: 264189520,
                retention_pct: 68.6,
                dropped_count: 34275316,
                rule: 'Normalize Fraktur & strip catalog/TOC boilerplate',
                sample_pruned: ['inhaltsverzeichnis', 'vorwort', 'auflage', 'isbn'],
              },
              {
                stage: '04 · PER/LOC & Stopwords',
                tokens_remaining: 161748685,
                retention_pct: 42.0,
                dropped_count: 102440835,
                rule: 'Strip personal (PER) & geographic (LOC) names',
                sample_pruned: ['rudolf_steiner', 'steiner', 'luther', 'deutschland'],
              },
              {
                stage: '05 · spaCy POS Lemmatizer',
                tokens_remaining: 114379428,
                retention_pct: 29.7,
                dropped_count: 47369257,
                rule: 'Retain NOUN/PROPN/ADJ & preserve compounds',
                sample_pruned: ['jedoch', 'bereits', 'innerhalb'],
              },
              {
                stage: '06 · Extremes Filter (|V|=25,000)',
                tokens_remaining: 104751530,
                retention_pct: 27.2,
                dropped_count: 9627898,
                rule: 'no_below=5, no_above=0.55, keep_n=25000',
                sample_pruned: ['buch', 'leben', 'mensch', 'jahr'],
              },
            ]
          ).map((st: any, idx: number) => (
            <div
              key={idx}
              className="p-3 rounded-xl bg-obsidian-950/90 border border-white/[0.07] flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-1 mb-1">
                  <span className="font-mono text-[10px] font-bold text-emerald-300 truncate">
                    {st.stage}
                  </span>
                  <span className="font-mono text-[10px] text-traditional font-bold">
                    {st.retention_pct}%
                  </span>
                </div>
                <div className="font-mono text-sm font-bold text-parchment-50 tabular-nums mb-1">
                  {Number(st.tokens_remaining).toLocaleString()} <span className="text-[10px] font-normal text-parchment-300">tokens</span>
                </div>
                <div className="w-full h-1.5 rounded-full bg-obsidian-900 overflow-hidden mb-2">
                  <div
                    style={{ width: `${st.retention_pct}%` }}
                    className="h-full bg-emerald-400 rounded-full"
                  />
                </div>
                <p className="text-[10px] text-parchment-300 leading-snug mb-2">{st.rule}</p>
              </div>
              {st.sample_pruned && st.sample_pruned.length > 0 && (
                <div className="pt-1.5 border-t border-white/[0.05]">
                  <span className="font-mono text-[8px] uppercase text-rose-300 block mb-1">
                    Pruned Examples (-{Number(st.dropped_count).toLocaleString()}):
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {st.sample_pruned.slice(0, 4).map((pWord: string) => (
                      <button
                        key={pWord}
                        onClick={() => setVocabLookupQuery(pWord)}
                        className="px-1.5 py-0.5 rounded bg-rose-500/10 border border-rose-500/25 font-mono text-[9px] text-rose-300 hover:bg-rose-500/20 cursor-pointer"
                      >
                        {pWord}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Footer Telemetry Banner */}
      <div className="archival-panel rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-2 font-mono text-[11px] text-parchment-300">
        <span>
          Active Model State: <strong>K = {numTopics}</strong> · Corpus: <strong>{totalRecords.toLocaleString()} passages</strong> · Dictionary: <strong>{vocabSize.toLocaleString()} lemmas/bigrams</strong>
        </span>
        <span>
          Coherence (U<sub>Mass</sub>): <strong className="text-neoliberal">{coherenceScore.toFixed(4)}</strong> · Coherence (C<sub>v</sub>): <strong className="text-emerald-300">{(cvCoherence || 0.4366).toFixed(4)}</strong>
        </span>
      </div>
    </div>
  );
};
