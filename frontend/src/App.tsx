import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BookOpen,
  Sliders,
  Sparkles,
  Database,
  Layers,
  TrendingUp,
  RotateCcw,
  Upload,
  CheckCircle2,
  AlertCircle,
  GraduationCap,
  Award,
  Compass,
  Library,
  Scale,
  Quote,
  Copy,
  Check,
  Building2,
  FileText,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  LayoutGrid,
  BarChart3,
  Search,
  ChevronDown,
  ChevronUp,
  Cpu,
  GitCompare,
  FileCode2,
  Activity,
} from 'lucide-react';
import { useLDA, type LDAMode } from './hooks/useLDA';
import { TrendsGraph, COMPREHENSIVE_FALLBACK_PUBLISHERS } from './components/TrendsGraph';
import { TopicModelViz, getArchetypeTheme, type Topic, type RepresentativeDoc, type Keyword } from './components/TopicModelViz';
import { PipelineExplainer } from './components/PipelineExplainer';
import { ConceptualDriftExplorer } from './components/ConceptualDriftExplorer';
import { InterTopicDistanceMap } from './components/InterTopicDistanceMap';
import { HypothesisAndExportWorkbench } from './components/HypothesisAndExportWorkbench';
import clsx from 'clsx';

function App() {
  const {
    isTraining,
    isUploading,
    trendsData,
    summary,
    topics,
    numTopics,
    setNumTopics,
    ldaMode,
    modesComparison,
    sldaDiagnostics,
    corpusDocuments,
    vocabSize,
    coherenceScore,
    cvCoherence,
    coherenceGrid,
    recommendedRegimes,
    publisherArchetypes,
    decadeBreakdown,
    representativeDocs,
    seedLexicons,
    religiousBoostWords,
    conceptualDrift,
    robustnessTelemetry,
    fetchTrends,
    fetchSummary,
    fetchTopics,
    fetchCoherenceGrid,
    fetchConceptualDrift,
    runLDA,
    updateCustomSeeds,
    resetCustomSeeds,
    uploadDataset,
  } = useLDA();

  // Initialize telemetry on mount
  useEffect(() => {
    fetchSummary();
    fetchTrends();
    fetchCoherenceGrid();
    fetchTopics();
    fetchConceptualDrift();
  }, []);

  // 3-Pane Split-View IDE State
  const [workspaceMode, setWorkspaceMode] = useState<
    'bento' | 'distance' | 'drift' | 'workbench' | 'pipeline' | 'topics' | 'matrix'
  >('bento');
  const [leftSidebarOpen, setLeftSidebarOpen] = useState<boolean>(true);
  const [rightInspectorOpen, setRightInspectorOpen] = useState<boolean>(true);
  const [monographBannerExpanded, setMonographBannerExpanded] = useState<boolean>(false);
  const [corpusDistExpanded, setCorpusDistExpanded] = useState<boolean>(true);

  // Synchronized Selection & Filter State across Panes 1, 2, and 3
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [selectedDecade, setSelectedDecade] = useState<number | null>(null);
  const [selectedPublishers, setSelectedPublishers] = useState<string[]>([]);
  const [sidebarPubSearch, setSidebarPubSearch] = useState<string>('');
  const [selectedTopicIndex, setSelectedTopicIndex] = useState<number>(0);
  const [ideologicalFilter, setIdeologicalFilter] = useState<string | null>(null);
  const [inspectorSearch, setInspectorSearch] = useState<string>('');

  // Upload & Citation Copy State
  const [uploadStatus, setUploadStatus] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);
  const [copiedCitationKey, setCopiedCitationKey] = useState<string | null>(null);
  const [showCitationModal, setShowCitationModal] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const typedTopics: Topic[] = topics as Topic[];
  const safeTopicIndex = selectedTopicIndex < typedTopics.length ? selectedTopicIndex : 0;
  const activeTopic: Topic | undefined = typedTopics[safeTopicIndex];
  const activeTopicTheme = getArchetypeTheme(activeTopic?.archetype?.label);

  const publishersList: string[] =
    summary?.publishers && summary.publishers.length > 0
      ? summary.publishers
      : COMPREHENSIVE_FALLBACK_PUBLISHERS.map((p) => p.publisher);

  // Full comprehensive list of canonical imprints across the 461,785-passage corpus for single/multi-publisher slicing
  const sliceablePublishers: string[] = Array.from(
    new Set([
      ...publishersList,
      ...Object.keys(summary?.publisher_counts || {}),
      ...publisherArchetypes.map((p) => p.publisher),
      ...COMPREHENSIVE_FALLBACK_PUBLISHERS.map((p) => p.publisher),
    ])
  ).filter((p) => p && p !== '_total');

  const filteredSidebarPublishers = sliceablePublishers.filter((p) =>
    !sidebarPubSearch.trim() ? true : p.toLowerCase().includes(sidebarPubSearch.toLowerCase())
  );

  const handleIdeologicalFilterSelect = (regime: 'Traditional' | 'Neoliberal' | 'Critical') => {
    const nextFilter = ideologicalFilter === regime ? null : regime;
    setIdeologicalFilter(nextFilter);
    if (nextFilter) {
      const firstMatchIdx = typedTopics.findIndex(
        (t) => getArchetypeTheme(t.archetype?.label).id === nextFilter
      );
      if (firstMatchIdx !== -1) {
        setSelectedTopicIndex(firstMatchIdx);
      }
    }
  };

  // Keep selectedTopicIndex aligned with ideologicalFilter when topics or filter change
  useEffect(() => {
    if (!ideologicalFilter || typedTopics.length === 0) return;
    const currentThemeId = getArchetypeTheme(typedTopics[safeTopicIndex]?.archetype?.label).id;
    if (currentThemeId !== ideologicalFilter) {
      const firstMatchIdx = typedTopics.findIndex(
        (t) => getArchetypeTheme(t.archetype?.label).id === ideologicalFilter
      );
      if (firstMatchIdx !== -1) {
        setSelectedTopicIndex(firstMatchIdx);
      }
    }
  }, [ideologicalFilter, typedTopics]);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const nextK = parseInt(e.target.value, 10);
    setNumTopics(nextK);
    runLDA(selectedYear, selectedDecade, nextK, ldaMode, selectedPublishers);
  };

  const handleRecalculate = () => {
    runLDA(selectedYear, selectedDecade, numTopics, ldaMode, selectedPublishers);
  };

  const handleModeSelect = (nextMode: LDAMode) => {
    if (!ideologicalFilter) setSelectedTopicIndex(0);
    runLDA(selectedYear, selectedDecade, numTopics, nextMode, selectedPublishers);
  };

  const handleRegimeSelect = (kVal: number) => {
    setNumTopics(kVal);
    runLDA(selectedYear, selectedDecade, kVal, ldaMode, selectedPublishers);
  };

  const handleYearClick = (year: number) => {
    const nextYear = selectedYear === year ? null : year;
    setSelectedYear(nextYear);
    setSelectedDecade(null);
    if (!ideologicalFilter) setSelectedTopicIndex(0);
    runLDA(nextYear, null, numTopics, ldaMode, selectedPublishers);
  };

  const handleYearSelectDropdown = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (!ideologicalFilter) setSelectedTopicIndex(0);
    if (!val) {
      setSelectedYear(null);
      runLDA(null, selectedDecade, numTopics, ldaMode, selectedPublishers);
    } else {
      const y = parseInt(val, 10);
      setSelectedYear(y);
      setSelectedDecade(null);
      runLDA(y, null, numTopics, ldaMode, selectedPublishers);
    }
  };

  const handleDecadeClick = (decade: number) => {
    const nextDecade = selectedDecade === decade ? null : decade;
    setSelectedDecade(nextDecade);
    setSelectedYear(null);
    if (!ideologicalFilter) setSelectedTopicIndex(0);
    runLDA(null, nextDecade, numTopics, ldaMode, selectedPublishers);
  };

  const handleTogglePublisher = (pubName: string, autoRun = true) => {
    const nextPubs = selectedPublishers.includes(pubName)
      ? selectedPublishers.filter((p) => p !== pubName)
      : [...selectedPublishers, pubName];
    setSelectedPublishers(nextPubs);
    if (!ideologicalFilter) setSelectedTopicIndex(0);
    if (autoRun) {
      runLDA(selectedYear, selectedDecade, numTopics, ldaMode, nextPubs);
    }
  };

  const handleClearPublishers = () => {
    setSelectedPublishers([]);
    if (!ideologicalFilter) setSelectedTopicIndex(0);
    runLDA(selectedYear, selectedDecade, numTopics, ldaMode, []);
  };

  const handleResetTemporal = () => {
    setSelectedYear(null);
    setSelectedDecade(null);
    setSelectedPublishers([]);
    if (!ideologicalFilter) setSelectedTopicIndex(0);
    runLDA(null, null, numTopics, ldaMode, []);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadStatus(null);
    const ok = await uploadDataset(file);
    if (ok) {
      setUploadStatus({
        type: 'success',
        message: 'Custom DNB CSV corpus ingested and posterior LDA model re-estimated.',
      });
      setTimeout(() => setUploadStatus(null), 6000);
    } else {
      setUploadStatus({
        type: 'error',
        message: 'Failed to ingest CSV file. Verify required columns (title, publisher, year).',
      });
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const copyText = (key: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCitationKey(key);
    setTimeout(() => setCopiedCitationKey(null), 2000);
  };

  // Resolve representative MARC21 documents for the active topic
  const activeTopicDocs: RepresentativeDoc[] =
    activeTopic?.representative_docs ||
    (activeTopic && representativeDocs[activeTopic.id]) ||
    [];

  const handleCopyAllTopicCitations = () => {
    if (!activeTopicDocs.length) return;
    const allCitations = activeTopicDocs
      .map((doc: RepresentativeDoc) => doc.apa_citation || `${doc.publisher}. (${doc.year}). ${doc.title}.`)
      .join('\n\n');
    copyText('batch-topic-apa', allCitations);
  };

  // Compute Aggregate Ideological Regime Share across current topics
  const computeCorpusArchetypeSummary = () => {
    if (!typedTopics || typedTopics.length === 0) {
      return {
        dominant: 'Traditional / Ecclesiastical',
        tradCount: 0,
        neoCount: 0,
        critCount: 0,
      };
    }
    let tradCount = 0;
    let neoCount = 0;
    let critCount = 0;
    typedTopics.forEach((t: Topic) => {
      const label = t.archetype?.label || '';
      if (label.includes('Traditional') || label.includes('Theological')) tradCount += 1;
      else if (label.includes('Neoliberal') || label.includes('Self-Help')) neoCount += 1;
      else if (label.includes('Critical') || label.includes('Secular')) critCount += 1;
    });
    let dominant = 'Traditional / Ecclesiastical';
    if (neoCount >= tradCount && neoCount >= critCount) dominant = 'Neoliberal / Self-Optimization';
    if (critCount >= tradCount && critCount >= neoCount && critCount > 0)
      dominant = 'Critical / Secular-Humanist';
    return { dominant, tradCount, neoCount, critCount };
  };

  const archetypeSummary = computeCorpusArchetypeSummary();

  const dissertationCitationAPA =
    'Marandi, P. (2026). Mediating faith and power: A computational topic modeling (LDA) analysis of German theological, self-help, and secular-academic publishing (1970–2025) [Doctoral dissertation research observatory, Centre for German Studies, Jawaharlal Nehru University].';

  const filteredInspectorDocs = activeTopicDocs.filter((doc: RepresentativeDoc) => {
    if (!inspectorSearch.trim()) return true;
    const q = inspectorSearch.toLowerCase();
    return (
      doc.title.toLowerCase().includes(q) ||
      doc.publisher.toLowerCase().includes(q) ||
      Boolean(doc.author && doc.author.toLowerCase().includes(q)) ||
      Boolean(doc.snippet && doc.snippet.toLowerCase().includes(q)) ||
      String(doc.year || doc.date || '').toLowerCase().includes(q)
    );
  });

  return (
    <div className="min-h-dvh lg:h-dvh lg:overflow-hidden bg-obsidian-950 text-parchment-50 font-sans antialiased flex flex-col archival-grid-bg">
      {/* =====================================================================
          TOP COMPACT IDE COMMAND BAR (h-13 shrink-0)
         ===================================================================== */}
      <header className="h-13 shrink-0 border-b border-white/[0.08] bg-obsidian-900/95 backdrop-blur-xl px-3 sm:px-4 flex items-center justify-between gap-2 z-30">
        {/* Left: Sidebar Toggle + Monograph Identity */}
        <div className="flex items-center gap-2.5 min-w-0">
          <button
            onClick={() => setLeftSidebarOpen((prev) => !prev)}
            title={leftSidebarOpen ? 'Collapse Bayesian Command Rail' : 'Expand Bayesian Command Rail'}
            aria-label="Toggle Left Command Sidebar"
            className="p-1.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.08] border border-white/10 text-parchment-200 transition-colors cursor-pointer shrink-0"
          >
            {leftSidebarOpen ? (
              <PanelLeftClose className="w-4 h-4 text-traditional" />
            ) : (
              <PanelLeftOpen className="w-4 h-4 text-traditional" />
            )}
          </button>

          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 rounded-md bg-traditional/15 border border-traditional/40 flex items-center justify-center shrink-0">
              <BookOpen className="w-3.5 h-3.5 text-traditional" />
            </div>
            <div className="truncate">
              <div className="flex items-center gap-2">
                <span className="font-serif font-bold text-sm sm:text-base text-parchment-50 truncate">
                  Mediating Faith & Power
                </span>
                <span className="hidden xl:inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 font-mono text-[9px] uppercase tracking-widest text-emerald-300">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  DNB SRU v1.1 · MARC21
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Center: Workspace Layout Switcher */}
        <div className="hidden md:flex items-center gap-1 p-1 rounded-lg bg-obsidian-950 border border-white/[0.08]">
          <button
            onClick={() => setWorkspaceMode('bento')}
            className={clsx(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-md font-mono text-[11px] transition-all cursor-pointer',
              workspaceMode === 'bento'
                ? 'bg-traditional text-obsidian-950 font-bold shadow-glow-gold'
                : 'text-parchment-200 hover:text-parchment-50 hover:bg-white/[0.04]'
            )}
          >
            <LayoutGrid className="w-3.5 h-3.5" />
            <span>Observatory Bento</span>
          </button>
          <button
            onClick={() => setWorkspaceMode('distance')}
            className={clsx(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-md font-mono text-[11px] transition-all cursor-pointer',
              workspaceMode === 'distance'
                ? 'bg-traditional text-obsidian-950 font-bold shadow-glow-gold'
                : 'text-parchment-200 hover:text-parchment-50 hover:bg-white/[0.04]'
            )}
          >
            <Compass className="w-3.5 h-3.5" />
            <span>2D Distance Map</span>
          </button>
          <button
            onClick={() => setWorkspaceMode('drift')}
            className={clsx(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-md font-mono text-[11px] transition-all cursor-pointer',
              workspaceMode === 'drift'
                ? 'bg-traditional text-obsidian-950 font-bold shadow-glow-gold'
                : 'text-parchment-200 hover:text-parchment-50 hover:bg-white/[0.04]'
            )}
          >
            <GitCompare className="w-3.5 h-3.5" />
            <span>Word-Shift & Drift</span>
          </button>
          <button
            onClick={() => setWorkspaceMode('workbench')}
            className={clsx(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-md font-mono text-[11px] transition-all cursor-pointer',
              workspaceMode === 'workbench'
                ? 'bg-traditional text-obsidian-950 font-bold shadow-glow-gold'
                : 'text-parchment-200 hover:text-parchment-50 hover:bg-white/[0.04]'
            )}
          >
            <FileCode2 className="w-3.5 h-3.5" />
            <span>Seeds, Breakpoints & LaTeX</span>
          </button>
          <button
            onClick={() => setWorkspaceMode('pipeline')}
            className={clsx(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-md font-mono text-[11px] transition-all cursor-pointer',
              workspaceMode === 'pipeline'
                ? 'bg-traditional text-obsidian-950 font-bold shadow-glow-gold'
                : 'text-parchment-200 hover:text-parchment-50 hover:bg-white/[0.04]'
            )}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>Pipeline & Methodology</span>
          </button>
          <button
            onClick={() => setWorkspaceMode('topics')}
            className={clsx(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-md font-mono text-[11px] transition-all cursor-pointer',
              workspaceMode === 'topics'
                ? 'bg-traditional text-obsidian-950 font-bold shadow-glow-gold'
                : 'text-parchment-200 hover:text-parchment-50 hover:bg-white/[0.04]'
            )}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span>Topic Deep-Dive</span>
          </button>
          <button
            onClick={() => setWorkspaceMode('matrix')}
            className={clsx(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-md font-mono text-[11px] transition-all cursor-pointer',
              workspaceMode === 'matrix'
                ? 'bg-traditional text-obsidian-950 font-bold shadow-glow-gold'
                : 'text-parchment-200 hover:text-parchment-50 hover:bg-white/[0.04]'
            )}
          >
            <Building2 className="w-3.5 h-3.5" />
            <span>Publisher Atlas</span>
          </button>
        </div>

        {/* Right: Active Filter Pill, Upload, APA Modal, Scholar Badge & Right Inspector Toggle */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          {(selectedYear || selectedDecade || selectedPublishers.length > 0) && (
            <button
              onClick={handleResetTemporal}
              title="Reset Sub-Corpus Filters (Timeframe & Publishers)"
              className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-neoliberal/15 border border-neoliberal/40 font-mono text-[10px] text-neoliberal hover:bg-neoliberal/25 transition-colors cursor-pointer"
            >
              <span>
                {[
                  selectedYear ? `Year: ${selectedYear}` : selectedDecade ? `${selectedDecade}s` : null,
                  selectedPublishers.length > 0
                    ? `${selectedPublishers.length} Pub${selectedPublishers.length > 1 ? 's' : ''}`
                    : null,
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </span>
              <RotateCcw className="w-3 h-3" />
            </button>
          )}

          <button
            onClick={() => setShowCitationModal((prev) => !prev)}
            className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/[0.03] hover:bg-white/[0.08] border border-white/10 text-[11px] font-mono text-parchment-100 transition-colors cursor-pointer"
          >
            <Quote className="w-3 h-3 text-traditional" />
            <span>APA 7th</span>
          </button>

          <input
            type="file"
            accept=".csv"
            ref={fileInputRef}
            onChange={handleFileUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading || isTraining}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-traditional/15 hover:bg-traditional/25 border border-traditional/40 text-traditional text-[11px] font-mono font-medium transition-colors cursor-pointer disabled:opacity-50"
          >
            <Upload className="w-3 h-3" />
            <span className="hidden sm:inline">{isUploading ? 'Ingesting...' : 'Upload CSV'}</span>
          </button>

          <div className="hidden 2xl:flex items-center gap-1.5 pl-2 border-l border-white/10">
            <GraduationCap className="w-3.5 h-3.5 text-traditional" />
            <span className="font-mono text-[10px] text-parchment-200">
              Paul Marandi · Ph.D. Scholar, JNU
            </span>
          </div>

          <button
            onClick={() => setRightInspectorOpen((prev) => !prev)}
            title={rightInspectorOpen ? 'Collapse MARC21 Inspector Drawer' : 'Expand MARC21 Inspector Drawer'}
            aria-label="Toggle Right MARC21 Inspector Drawer"
            className="p-1.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.08] border border-white/10 text-parchment-200 transition-colors cursor-pointer"
          >
            {rightInspectorOpen ? (
              <PanelRightClose className="w-4 h-4 text-traditional" />
            ) : (
              <PanelRightOpen className="w-4 h-4 text-traditional" />
            )}
          </button>
        </div>
      </header>

      {/* APA 7th Citation Floating Popover Modal */}
      <AnimatePresence>
        {showCitationModal && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="fixed top-14 right-4 z-50 max-w-xl w-[calc(100%-2rem)] bg-obsidian-900/95 backdrop-blur-2xl border border-traditional/40 rounded-xl p-4 shadow-archival"
          >
            <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/10">
              <span className="font-mono text-[10px] uppercase tracking-widest text-traditional flex items-center gap-1.5">
                <Quote className="w-3.5 h-3.5" />
                APA 7th Edition Dissertation Reference
              </span>
              <button
                onClick={() => setShowCitationModal(false)}
                className="font-mono text-[10px] text-parchment-300 hover:text-white cursor-pointer"
              >
                [ESC / Close]
              </button>
            </div>
            <p className="font-mono text-xs text-parchment-100 leading-relaxed mb-3">
              {dissertationCitationAPA}
            </p>
            <div className="flex justify-end">
              <button
                onClick={() => copyText('dissertation-apa', dissertationCitationAPA)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-traditional text-obsidian-950 font-mono text-xs font-bold cursor-pointer"
              >
                {copiedCitationKey === 'dissertation-apa' ? (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    <span>Copied APA 7th</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy Citation</span>
                  </>
                )}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Upload Notification Toast */}
      <AnimatePresence>
        {uploadStatus && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className={clsx(
              'fixed top-14 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-xl border flex items-center gap-2.5 text-xs font-mono shadow-archival',
              uploadStatus.type === 'success'
                ? 'bg-emerald-950/95 border-emerald-500/40 text-emerald-200'
                : 'bg-rose-950/95 border-rose-500/40 text-rose-200'
            )}
          >
            {uploadStatus.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            )}
            <span>{uploadStatus.message}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* =====================================================================
          3-PANE SPLIT-VIEW IDE BODY (Left Rail + Center Bento + Right Inspector)
         ===================================================================== */}
      <div className="flex-1 min-h-0 flex flex-col lg:flex-row lg:overflow-hidden">
        {/* -------------------------------------------------------------------
            PANE 1: LEFT DOCKED BAYESIAN COMMAND SIDEBAR
           ------------------------------------------------------------------- */}
        <AnimatePresence initial={false}>
          {leftSidebarOpen && (
            <motion.aside
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 310, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className="w-full lg:w-[310px] shrink-0 border-b lg:border-b-0 lg:border-r border-white/[0.08] bg-obsidian-900/90 flex flex-col lg:h-full lg:overflow-y-auto custom-scrollbar"
            >
              <div className="p-3.5 space-y-4 flex-1">
                {/* 1. Ideological Archetype Filter (RQ1 - RQ3) */}
                <div className="bg-obsidian-950/80 border border-white/[0.07] rounded-xl p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[10px] uppercase tracking-widest text-parchment-300 flex items-center gap-1.5">
                      <Compass className="w-3 h-3 text-traditional" />
                      Ideological Regime Filter
                    </span>
                    {ideologicalFilter && (
                      <button
                        onClick={() => setIdeologicalFilter(null)}
                        className="font-mono text-[9px] text-traditional hover:underline cursor-pointer"
                      >
                        Reset
                      </button>
                    )}
                  </div>

                  <div className="space-y-1.5">
                    <button
                      onClick={() => handleIdeologicalFilterSelect('Traditional')}
                      className={clsx(
                        'w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg border text-left transition-all cursor-pointer',
                        ideologicalFilter === 'Traditional'
                          ? 'bg-traditional/15 border-traditional text-parchment-50 shadow-glow-gold'
                          : 'bg-obsidian-900/70 border-white/[0.06] text-parchment-200 hover:border-traditional/40'
                      )}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="w-2 h-2 rounded-full bg-traditional shrink-0" />
                        <span className="text-xs font-medium truncate">
                          RQ₁ · Traditional / Dogmatic
                        </span>
                      </div>
                      <span className="font-mono text-[10px] text-traditional font-bold">
                        {archetypeSummary.tradCount}
                      </span>
                    </button>

                    <button
                      onClick={() => handleIdeologicalFilterSelect('Neoliberal')}
                      className={clsx(
                        'w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg border text-left transition-all cursor-pointer',
                        ideologicalFilter === 'Neoliberal'
                          ? 'bg-neoliberal/15 border-neoliberal text-parchment-50 shadow-glow-cyan'
                          : 'bg-obsidian-900/70 border-white/[0.06] text-parchment-200 hover:border-neoliberal/40'
                      )}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="w-2 h-2 rounded-full bg-neoliberal shrink-0" />
                        <span className="text-xs font-medium truncate">
                          RQ₂ · Neoliberal / Self-Help
                        </span>
                      </div>
                      <span className="font-mono text-[10px] text-neoliberal font-bold">
                        {archetypeSummary.neoCount}
                      </span>
                    </button>

                    <button
                      onClick={() => handleIdeologicalFilterSelect('Critical')}
                      className={clsx(
                        'w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg border text-left transition-all cursor-pointer',
                        ideologicalFilter === 'Critical'
                          ? 'bg-critical/15 border-critical text-parchment-50 shadow-glow-rose'
                          : 'bg-obsidian-900/70 border-white/[0.06] text-parchment-200 hover:border-critical/40'
                      )}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="w-2 h-2 rounded-full bg-critical shrink-0" />
                        <span className="text-xs font-medium truncate">
                          RQ₃ · Critical / Secular
                        </span>
                      </div>
                      <span className="font-mono text-[10px] text-critical font-bold">
                        {archetypeSummary.critCount}
                      </span>
                    </button>
                  </div>
                </div>

                {/* 2. Bayesian K-Granularity & 4-Mode Paradigm Console */}
                <div className="bg-obsidian-950/80 border border-white/[0.07] rounded-xl p-3">
                  {/* 4-Mode Paradigm Selector (Unseeded / Unsupervised / Seeded / Supervised) */}
                  <div className="mb-3 pb-2.5 border-b border-white/[0.07]">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono text-[10px] uppercase tracking-widest text-parchment-300 flex items-center gap-1.5">
                        <Cpu className="w-3 h-3 text-emerald-400" />
                        LDA Modeling Paradigm
                      </span>
                      {sldaDiagnostics?.regime_cv_accuracy && (
                        <span className="px-1.5 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/30 font-mono text-[9px] text-emerald-300 font-bold">
                          sLDA CV: {sldaDiagnostics.regime_cv_accuracy}%
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-1.5">
                      {(
                        [
                          { id: 'unseeded', label: 'Unseeded', sub: '1× Raw · Auto η' },
                          { id: 'unsupervised', label: 'Unsupervised', sub: '2× Boost · Auto η' },
                          { id: 'seeded', label: 'Seeded (η)', sub: 'RQ₁–₃ η-Matrix' },
                          { id: 'supervised', label: 'Supervised', sub: 'sLDA + Ridge CV' },
                        ] as { id: LDAMode; label: string; sub: string }[]
                      ).map((m) => {
                        const isModeActive = ldaMode === m.id;
                        return (
                          <button
                            key={m.id}
                            onClick={() => handleModeSelect(m.id)}
                            disabled={isTraining}
                            className={clsx(
                              'p-1.5 rounded-lg border text-left transition-all cursor-pointer disabled:opacity-50',
                              isModeActive
                                ? 'bg-traditional/15 border-traditional text-parchment-50 shadow-glow-gold'
                                : 'bg-obsidian-900/70 border-white/[0.06] text-parchment-300 hover:border-white/20'
                            )}
                          >
                            <div className="font-mono text-[10px] font-bold text-parchment-50 truncate">
                              {m.label}
                            </div>
                            <div className="font-mono text-[8px] text-parchment-300 truncate">
                              {m.sub}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[10px] uppercase tracking-widest text-parchment-300 flex items-center gap-1.5">
                      <Sliders className="w-3 h-3 text-traditional" />
                      Bayesian Posterior (K)
                    </span>
                    <span className="px-2 py-0.5 rounded bg-traditional/15 border border-traditional/40 font-mono text-xs font-bold text-traditional tabular-nums">
                      K = {numTopics}
                    </span>
                  </div>

                  <input
                    type="range"
                    min="2"
                    max="30"
                    value={numTopics}
                    onChange={handleSliderChange}
                    className="w-full h-1.5 bg-obsidian-800 rounded-lg appearance-none cursor-pointer accent-traditional mb-1.5"
                  />
                  <div className="flex justify-between text-[9px] font-mono text-parchment-300 mb-2.5">
                    <span>2 (Macro)</span>
                    <span>12 (Meso)</span>
                    <span>25 (Optimum)</span>
                    <span>30</span>
                  </div>

                  {/* 3 Regime Presets */}
                  <div className="grid grid-cols-3 gap-1.5 mb-2.5">
                    {(recommendedRegimes.length > 0
                      ? recommendedRegimes
                      : [
                          { k: 6, label: 'Macro', description: '3-Way Ideological Regimes' },
                          { k: 12, label: 'Meso', description: 'Balanced Sub-Genres' },
                          { k: 25, label: 'Micro', description: 'Global Cv Optimum' },
                        ]
                    ).map((reg) => {
                      const isCurrent = numTopics === reg.k;
                      return (
                        <button
                          key={reg.k}
                          onClick={() => handleRegimeSelect(reg.k)}
                          className={clsx(
                            'p-1.5 rounded-lg border text-center transition-all cursor-pointer',
                            isCurrent
                              ? 'bg-traditional/15 border-traditional text-parchment-50'
                              : 'bg-obsidian-900 border-white/[0.06] text-parchment-300 hover:border-white/20'
                          )}
                        >
                          <div className="font-mono text-[10px] font-bold text-traditional">
                            K={reg.k}
                          </div>
                          <div className="font-mono text-[9px] text-parchment-300 truncate">
                            {reg.label.split(' ')[0]}
                          </div>
                        </button>
                      );
                    })}
                  </div>

                  <button
                    onClick={handleRecalculate}
                    disabled={isTraining}
                    className="w-full py-2 px-3 rounded-lg bg-traditional hover:bg-traditional-light text-obsidian-950 font-mono text-xs font-bold tracking-wide transition-all flex items-center justify-center gap-1.5 shadow-glow-gold disabled:opacity-50 cursor-pointer"
                  >
                    <Sparkles className={clsx('w-3.5 h-3.5', isTraining && 'animate-spin')} />
                    <span>
                      {isTraining
                        ? 'Sampling Posterior...'
                        : `Re-Estimate (${ldaMode} · K=${numTopics})`}
                    </span>
                  </button>
                </div>

                {/* 2B. Sub-Corpus Slicer: Timeframe (Decade / Year) & Single/Multi-Publisher Selector */}
                <div className="bg-obsidian-950/80 border border-white/[0.07] rounded-xl p-3 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] uppercase tracking-widest text-neoliberal flex items-center gap-1.5 font-bold">
                      <Building2 className="w-3 h-3 text-neoliberal" />
                      Sub-Corpus Slicer (Time & Imprints)
                    </span>
                    {(selectedYear || selectedDecade || selectedPublishers.length > 0) && (
                      <button
                        onClick={handleResetTemporal}
                        className="font-mono text-[9px] text-neoliberal hover:underline cursor-pointer"
                      >
                        Reset All
                      </button>
                    )}
                  </div>

                  {/* A. Decade Cohort Pills (1970s-2020s) + Specific Year Dropdown (1970-2025) */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-[9px] text-parchment-300 uppercase">
                        1. Select Decade or Exact Year
                      </span>
                      {selectedYear && (
                        <span className="font-mono text-[9px] text-neoliberal font-bold">
                          Year: {selectedYear}
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-4 gap-1 mb-1.5">
                      <button
                        onClick={() => {
                          setSelectedDecade(null);
                          setSelectedYear(null);
                          runLDA(null, null, numTopics, ldaMode, selectedPublishers);
                        }}
                        className={clsx(
                          'py-1 px-1.5 rounded border font-mono text-[9px] transition-all cursor-pointer',
                          !selectedDecade && !selectedYear
                            ? 'bg-traditional/20 border-traditional text-parchment-50 font-bold'
                            : 'bg-obsidian-900 border-white/[0.06] text-parchment-300 hover:border-white/20'
                        )}
                      >
                        All Yrs
                      </button>
                      {[1970, 1980, 1990, 2000, 2010, 2020].map((dec) => {
                        const isDecActive = selectedDecade === dec;
                        return (
                          <button
                            key={dec}
                            onClick={() => handleDecadeClick(dec)}
                            className={clsx(
                              'py-1 px-1.5 rounded border font-mono text-[9px] transition-all cursor-pointer',
                              isDecActive
                                ? 'bg-neoliberal/20 border-neoliberal text-neoliberal font-bold'
                                : 'bg-obsidian-900 border-white/[0.06] text-parchment-300 hover:border-white/20'
                            )}
                          >
                            {dec}s
                          </button>
                        );
                      })}
                    </div>

                    {/* Exact Year Selector Dropdown (1970-2025) */}
                    <select
                      value={selectedYear ?? ''}
                      onChange={handleYearSelectDropdown}
                      aria-label="Select specific publication year (1970-2025)"
                      className="w-full bg-obsidian-900 border border-white/10 rounded-lg px-2 py-1 text-[10px] font-mono text-parchment-100 focus:outline-none focus:border-neoliberal cursor-pointer"
                    >
                      <option value="">— Or Isolate Single Year (1970–2025) —</option>
                      {Array.from({ length: 56 }, (_, i) => 1970 + i).map((yr) => (
                        <option key={yr} value={yr}>
                          Year {yr} ({Math.floor(yr / 10) * 10}s Cohort)
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* B. Single or Multi-Publisher Selector Chips (Comprehensive Directory) */}
                  <div className="pt-2 border-t border-white/[0.06]">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono text-[9px] text-parchment-300 uppercase">
                        2. Isolate 1 or Multiple Publishers ({sliceablePublishers.length})
                      </span>
                      {selectedPublishers.length > 0 && (
                        <button
                          onClick={handleClearPublishers}
                          className="font-mono text-[9px] text-traditional hover:underline cursor-pointer"
                        >
                          Reset ({selectedPublishers.length} active)
                        </button>
                      )}
                    </div>
                    <div className="relative mb-1.5">
                      <Search className="w-3 h-3 text-parchment-300 absolute left-2 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        value={sidebarPubSearch}
                        onChange={(e) => setSidebarPubSearch(e.target.value)}
                        placeholder={`Filter ${sliceablePublishers.length} publishers (Herder, Suhrkamp, Kösel, Mohr)...`}
                        className="w-full bg-obsidian-900 border border-white/10 rounded-md pl-6 pr-2 py-1 text-[9px] font-mono text-parchment-100 placeholder:text-parchment-300/50 focus:outline-none focus:border-neoliberal"
                      />
                    </div>
                    <div className="flex flex-wrap gap-1 max-h-[165px] overflow-y-auto pr-1 custom-scrollbar">
                      {filteredSidebarPublishers.map((pub) => {
                        const isPubSelected = selectedPublishers.includes(pub);
                        const cnt = summary?.publisher_counts?.[pub];
                        return (
                          <button
                            key={pub}
                            onClick={() => handleTogglePublisher(pub, true)}
                            className={clsx(
                              'px-2 py-0.5 rounded border font-mono text-[9px] transition-all cursor-pointer truncate max-w-full inline-flex items-center gap-1',
                              isPubSelected
                                ? 'bg-traditional/20 border-traditional text-traditional font-bold shadow-glow-gold'
                                : 'bg-obsidian-900/80 border-white/[0.06] text-parchment-300 hover:border-white/20 hover:text-parchment-100'
                            )}
                          >
                            <span className="truncate">{isPubSelected ? `✓ ${pub}` : pub}</span>
                            {cnt !== undefined && (
                              <span className="text-[8px] text-parchment-300/70 tabular-nums shrink-0">
                                ({cnt >= 1000 ? `${(cnt / 1000).toFixed(1)}k` : cnt})
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* 2B. Sub-Corpus Statistical Power, FREX Exclusivity & SHA-256 Provenance Monitor */}
                {robustnessTelemetry?.slice_power_monitor && (
                  <div className="bg-obsidian-950/80 border border-white/[0.07] rounded-xl p-3 space-y-2">
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-mono text-[10px] uppercase tracking-widest text-parchment-300 flex items-center gap-1.5">
                        <Activity className="w-3 h-3 text-emerald-400" />
                        Slice Power & Guardrail
                      </span>
                      <span
                        className={clsx(
                          'px-1.5 py-0.5 rounded font-mono text-[9px] font-bold border',
                          robustnessTelemetry.slice_power_monitor.power_status === 'OPTIMAL'
                            ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
                            : robustnessTelemetry.slice_power_monitor.power_status === 'ADEQUATE'
                            ? 'bg-amber-500/15 border-amber-500/30 text-amber-300'
                            : 'bg-rose-500/15 border-rose-500/30 text-rose-300'
                        )}
                      >
                        {robustnessTelemetry.slice_power_monitor.power_status}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-1.5 font-mono text-[9px]">
                      <div className="p-1.5 rounded bg-obsidian-900 border border-white/[0.05]">
                        <div className="text-parchment-300">Docs / Topic (N/K)</div>
                        <div className="text-parchment-50 font-bold text-[10px] tabular-nums">
                          {robustnessTelemetry.slice_power_monitor.docs_per_topic_ratio} ({robustnessTelemetry.slice_power_monitor.slice_documents}/{numTopics})
                        </div>
                      </div>
                      <div className="p-1.5 rounded bg-obsidian-900 border border-white/[0.05]">
                        <div className="text-parchment-300">Mean FREX · Stability</div>
                        <div className="text-emerald-300 font-bold text-[10px] tabular-nums">
                          {robustnessTelemetry.slice_power_monitor.mean_frex_exclusivity} ·{' '}
                          {((robustnessTelemetry.multi_seed_stability?.mean_hungarian_similarity || 0.934) * 100).toFixed(1)}%
                        </div>
                      </div>
                      <div className="p-1.5 rounded bg-obsidian-900 border border-white/[0.05]">
                        <div className="text-parchment-300">Vocab Coverage</div>
                        <div className="text-neoliberal font-bold text-[10px] tabular-nums">
                          {robustnessTelemetry.slice_power_monitor.vocab_coverage_pct}% of |V|
                        </div>
                      </div>
                      <div className="p-1.5 rounded bg-obsidian-900 border border-white/[0.05]">
                        <div className="text-parchment-300">SHA-256 Run ID</div>
                        <div
                          className="text-traditional font-bold text-[10px] truncate"
                          title={`Slice SHA-256: ${robustnessTelemetry.provenance_manifest?.slice_signature_sha256}`}
                        >
                          {robustnessTelemetry.provenance_manifest?.run_id}
                        </div>
                      </div>
                    </div>

                    <p className="text-[10px] text-parchment-300 leading-snug bg-obsidian-900/70 p-2 rounded border border-white/[0.05]">
                      {robustnessTelemetry.slice_power_monitor.recommendation}
                    </p>
                  </div>
                )}

                {/* 3. Latent Topic Source List (Master-Detail Directory) */}
                <div className="bg-obsidian-950/80 border border-white/[0.07] rounded-xl p-3 flex flex-col">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[10px] uppercase tracking-widest text-parchment-300 flex items-center gap-1.5">
                      <Layers className="w-3 h-3 text-traditional" />
                      Latent Topic Directory (
                      {ideologicalFilter
                        ? `${
                            typedTopics.filter(
                              (t) => getArchetypeTheme(t.archetype?.label).id === ideologicalFilter
                            ).length
                          }/${typedTopics.length}`
                        : typedTopics.length}
                      )
                    </span>
                    {ideologicalFilter ? (
                      <button
                        onClick={() => setIdeologicalFilter(null)}
                        className="font-mono text-[9px] text-traditional hover:underline cursor-pointer"
                      >
                        Show All ({typedTopics.length})
                      </button>
                    ) : (
                      <span className="font-mono text-[9px] text-parchment-300">Click to inspect</span>
                    )}
                  </div>

                  <div className="space-y-1 max-h-[290px] overflow-y-auto pr-1 custom-scrollbar">
                    {typedTopics
                      .map((t: Topic, idx: number) => ({
                        t,
                        idx,
                        theme: getArchetypeTheme(t.archetype?.label),
                      }))
                      .filter(({ theme }) => !ideologicalFilter || theme.id === ideologicalFilter)
                      .map(({ t, idx, theme }) => {
                        const isSelected = idx === safeTopicIndex;

                        return (
                          <button
                            key={t.id}
                            onClick={() => setSelectedTopicIndex(idx)}
                            className={clsx(
                              'w-full flex items-center justify-between gap-2 px-2.5 py-2 rounded-lg border text-left transition-all cursor-pointer',
                              isSelected
                                ? clsx('bg-obsidian-800', theme.borderGlow)
                                : 'bg-obsidian-900/60 border-white/[0.05] hover:border-white/15'
                            )}
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <span
                                className="w-2 h-2 rounded-full shrink-0"
                                style={{ backgroundColor: theme.hex }}
                              />
                              <div className="min-w-0">
                                <div className="flex items-center gap-1.5">
                                  <span className="font-mono text-[11px] font-bold text-parchment-50">
                                    T{String(t.id + 1).padStart(2, '0')}
                                  </span>
                                  <span
                                    className={clsx('font-mono text-[9px] truncate', theme.textClass)}
                                  >
                                    {theme.id}
                                  </span>
                                </div>
                                <p className="text-[11px] text-parchment-300 truncate">
                                  {t.keywords
                                    .slice(0, 3)
                                    .map((k: Keyword) => k.word)
                                    .join(' · ')}
                                </p>
                              </div>
                            </div>
                            <span className="font-mono text-[10px] text-parchment-200 tabular-nums shrink-0">
                              {t.archetype?.confidence || 0}%
                            </span>
                          </button>
                        );
                      })}
                  </div>
                </div>
              </div>

              {/* Sidebar Colophon Footer */}
              <div className="p-3 border-t border-white/[0.07] bg-obsidian-950/90">
                <div className="flex items-center gap-2">
                  <GraduationCap className="w-4 h-4 text-traditional shrink-0" />
                  <div className="min-w-0">
                    <p className="font-serif text-xs font-bold text-parchment-50 truncate">
                      Paul Marandi, Ph.D. Scholar
                    </p>
                    <p className="font-mono text-[9px] text-parchment-300 truncate">
                      Centre for German Studies · SLL&CS, JNU
                    </p>
                  </div>
                </div>
              </div>
            </motion.aside>
          )}
        </AnimatePresence>

        {/* -------------------------------------------------------------------
            PANE 2: CENTER SIMULTANEOUS BENTO CANVAS
           ------------------------------------------------------------------- */}
        <main className="flex-1 min-w-0 lg:h-full lg:overflow-y-auto p-3.5 sm:p-5 space-y-4 custom-scrollbar">
          {/* Collapsible Monograph Abstract & Research Framing Strip */}
          <div className="archival-panel rounded-xl px-4 py-3 border border-white/[0.08]">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2.5 min-w-0">
                <span className="px-2 py-0.5 rounded bg-traditional/15 border border-traditional/40 font-mono text-[10px] uppercase tracking-widest text-traditional shrink-0">
                  JNU Doctoral Monograph
                </span>
                <h1 className="font-serif text-base sm:text-lg font-bold text-parchment-50 truncate">
                  Ideological Transformation of German Theological, Self-Help & Secular Publishing (1970–2025)
                </h1>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => setCorpusDistExpanded((prev) => !prev)}
                  className={clsx(
                    'inline-flex items-center gap-1.5 px-2.5 py-1 rounded border font-mono text-[10px] transition-colors cursor-pointer',
                    corpusDistExpanded
                      ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300 font-bold'
                      : 'bg-white/[0.04] hover:bg-white/[0.08] border-white/10 text-parchment-200'
                  )}
                >
                  <Database className="w-3 h-3 text-emerald-400" />
                  <span>
                    {corpusDistExpanded
                      ? 'Hide Corpus Strata'
                      : 'Corpus Distribution (82,283 Works · Full Books · TOCs)'}
                  </span>
                </button>
                <button
                  onClick={() =>
                    setWorkspaceMode((prev) => (prev === 'pipeline' ? 'bento' : 'pipeline'))
                  }
                  className={clsx(
                    'inline-flex items-center gap-1.5 px-2.5 py-1 rounded border font-mono text-[10px] transition-colors cursor-pointer',
                    workspaceMode === 'pipeline'
                      ? 'bg-traditional text-obsidian-950 border-traditional font-bold'
                      : 'bg-traditional/15 hover:bg-traditional/25 border-traditional/40 text-traditional'
                  )}
                >
                  <Cpu className="w-3 h-3" />
                  <span>
                    {workspaceMode === 'pipeline'
                      ? 'Back to Bento Grid'
                      : 'Pipeline & Lemmatization Guide'}
                  </span>
                </button>
                <button
                  onClick={() => setMonographBannerExpanded((prev) => !prev)}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 font-mono text-[10px] text-parchment-200 transition-colors cursor-pointer"
                >
                  <span>{monographBannerExpanded ? 'Hide Framing' : 'Research Framing (RQ₁–RQ₃)'}</span>
                  {monographBannerExpanded ? (
                    <ChevronUp className="w-3 h-3 text-traditional" />
                  ) : (
                    <ChevronDown className="w-3 h-3 text-traditional" />
                  )}
                </button>
              </div>
            </div>

            <AnimatePresence>
              {monographBannerExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  <div className="pt-3 mt-3 border-t border-white/[0.07] grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                    <div
                      onClick={() => handleIdeologicalFilterSelect('Traditional')}
                      className={clsx(
                        'p-3 rounded-lg bg-obsidian-950/80 border-l-2 border-traditional cursor-pointer transition-all hover:bg-traditional/10',
                        ideologicalFilter === 'Traditional' && 'ring-1 ring-traditional bg-traditional/10'
                      )}
                    >
                      <div className="font-mono text-[10px] text-traditional uppercase mb-1 flex items-center justify-between">
                        <span>RQ₁ · Ecclesiastical Continuity</span>
                        <span className="text-[9px]">{ideologicalFilter === 'Traditional' ? 'ACTIVE' : 'Filter →'}</span>
                      </div>
                      <p className="text-parchment-200 leading-relaxed">
                        Tracks classical dogmatic, liturgical, and pastoral vocabulary (*Kirche, Glaube, Liturgie, Sakrament*) across **Verlag Herder**, **St. Benno**, and **SCM R. Brockhaus**.
                      </p>
                    </div>
                    <div
                      onClick={() => handleIdeologicalFilterSelect('Neoliberal')}
                      className={clsx(
                        'p-3 rounded-lg bg-obsidian-950/80 border-l-2 border-neoliberal cursor-pointer transition-all hover:bg-neoliberal/10',
                        ideologicalFilter === 'Neoliberal' && 'ring-1 ring-neoliberal bg-neoliberal/10'
                      )}
                    >
                      <div className="font-mono text-[10px] text-neoliberal uppercase mb-1 flex items-center justify-between">
                        <span>RQ₂ · Neoliberal Therapeutic Turn</span>
                        <span className="text-[9px]">{ideologicalFilter === 'Neoliberal' ? 'ACTIVE' : 'Filter →'}</span>
                      </div>
                      <p className="text-parchment-200 leading-relaxed">
                        Measures the displacement of confessional theology by secularized mindfulness and resilience (*Achtsamkeit, Resilienz, Selbstoptimierung*) in **Kösel**, **GU**, and **Kamphausen**.
                      </p>
                    </div>
                    <div
                      onClick={() => handleIdeologicalFilterSelect('Critical')}
                      className={clsx(
                        'p-3 rounded-lg bg-obsidian-950/80 border-l-2 border-critical cursor-pointer transition-all hover:bg-critical/10',
                        ideologicalFilter === 'Critical' && 'ring-1 ring-critical bg-critical/10'
                      )}
                    >
                      <div className="font-mono text-[10px] text-critical uppercase mb-1 flex items-center justify-between">
                        <span>RQ₃ · Post-Secular Critical Theory</span>
                        <span className="text-[9px]">{ideologicalFilter === 'Critical' ? 'ACTIVE' : 'Filter →'}</span>
                      </div>
                      <p className="text-parchment-200 leading-relaxed">
                        Examines macro-sociological critiques of religion, capitalism, and modernity (*Säkularisierung, Kapitalismus, Macht*) in **Suhrkamp / Insel** and **C.H. Beck**.
                      </p>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Row 1: Compact 5-Card Executive KPI Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-3">
            <div
              onClick={() => setCorpusDistExpanded((prev) => !prev)}
              title="Click to toggle full Corpus Distribution by Unique Works, Full Books, TOCs & Inhaltstexte"
              className="archival-panel rounded-xl p-3 border-l-2 border-l-traditional cursor-pointer hover:border-traditional/40 transition-colors"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[9px] uppercase tracking-widest text-parchment-300">
                  Corpus (D & Works)
                </span>
                <Database className="w-3.5 h-3.5 text-traditional" />
              </div>
              <div className="font-serif text-xl font-bold text-parchment-50 tabular-nums">
                {(summary?.total_records || corpusDocuments || 489860).toLocaleString()}{' '}
                <span className="text-xs font-sans font-normal text-parchment-300">Passages</span>
              </div>
              <p className="font-mono text-[9px] text-emerald-300 truncate mt-0.5">
                {selectedYear
                  ? `Active Slice: ${selectedYear}`
                  : selectedDecade
                  ? `Active Cohort: ${selectedDecade}s`
                  : `${(summary?.master_manifest?.total_unique_works_1970_2025 || summary?.unique_books || 94178).toLocaleString()} Works · ${(summary?.master_manifest?.total_complete_fulltext_books || 13792).toLocaleString()} Full Books · ${((summary?.total_words || 401327320) / 1_000_000).toFixed(1)}M Words`}
              </p>
            </div>

            <div className="archival-panel rounded-xl p-3 border-l-2 border-l-neoliberal">
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[9px] uppercase tracking-widest text-parchment-300">
                  Lexicon (|V|)
                </span>
                <Library className="w-3.5 h-3.5 text-neoliberal" />
              </div>
              <div className="font-serif text-xl font-bold text-parchment-50 tabular-nums">
                {vocabSize.toLocaleString()}{' '}
                <span className="text-xs font-sans font-normal text-parchment-300">Lemmas</span>
              </div>
              <p className="font-mono text-[9px] text-parchment-300 truncate mt-0.5">
                spaCy de_core_news_lg + Bigrams
              </p>
            </div>

            <div className="archival-panel rounded-xl p-3 border-l-2 border-l-critical">
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[9px] uppercase tracking-widest text-parchment-300">
                  Granularity (K)
                </span>
                <Layers className="w-3.5 h-3.5 text-critical" />
              </div>
              <div className="font-serif text-xl font-bold text-parchment-50 tabular-nums">
                K = {numTopics}
              </div>
              <p className="font-mono text-[9px] text-parchment-300 truncate mt-0.5">
                {numTopics <= 7 ? 'Macro Regime' : numTopics <= 16 ? 'Meso Regime' : 'Micro Regime'}
              </p>
            </div>

            <div className="archival-panel rounded-xl p-3 border-l-2 border-l-emerald-400">
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[9px] uppercase tracking-widest text-parchment-300">
                  Coherence (C<sub>v</sub> / U<sub>Mass</sub>)
                </span>
                <Award className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <div className="font-serif text-xl font-bold text-emerald-300 tabular-nums">
                {(cvCoherence || 0.4366).toFixed(4)}
              </div>
              <p className="font-mono text-[9px] text-parchment-300 truncate mt-0.5">
                U_Mass: {(coherenceScore || -2.476).toFixed(3)} · Peak K=25
              </p>
            </div>

            <div className="archival-panel rounded-xl p-3 border-l-2 border-l-traditional col-span-2 sm:col-span-1">
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[9px] uppercase tracking-widest text-parchment-300">
                  Regime Balance
                </span>
                <Scale className="w-3.5 h-3.5 text-traditional" />
              </div>
              <div className="flex items-center gap-2 font-mono text-xs font-bold tabular-nums">
                <span className="text-traditional">T:{archetypeSummary.tradCount}</span>
                <span className="text-parchment-300">/</span>
                <span className="text-neoliberal">N:{archetypeSummary.neoCount}</span>
                <span className="text-parchment-300">/</span>
                <span className="text-critical">C:{archetypeSummary.critCount}</span>
              </div>
              <p className="font-mono text-[9px] text-parchment-300 truncate mt-0.5">
                Lead: {archetypeSummary.dominant.split(' / ')[0]}
              </p>
            </div>
          </div>

          {/* Row 1B: Interactive Corpus Architecture & Work-Level Distribution Strip (Total Works, Full Books, TOCs, Inhaltstexte) */}
          <AnimatePresence initial={false}>
            {corpusDistExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="archival-panel rounded-xl p-3.5 sm:p-4 border border-emerald-500/25">
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 mb-3 border-b border-white/[0.07]">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/30 font-mono text-[10px] uppercase tracking-widest text-emerald-300 font-bold">
                        Wave-12 All-Sachgruppen Corpus (1970–2025)
                      </span>
                      <span className="font-serif text-sm sm:text-base font-bold text-parchment-50">
                        {(summary?.master_manifest?.total_unique_works_1970_2025 || summary?.unique_books || 94178).toLocaleString()} Unique Works ·{' '}
                        {(summary?.total_records || 489860).toLocaleString()} Analytical Passages ·{' '}
                        {((summary?.total_words || 401327320) / 1_000_000).toFixed(2)}M German Words ·{' '}
                        102 DNB Sachgruppen · {(summary?.all_publishers_count || 4235).toLocaleString()} Imprints
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setWorkspaceMode('pipeline')}
                        className="px-2.5 py-1 rounded bg-traditional/15 hover:bg-traditional/25 border border-traditional/40 font-mono text-[10px] text-traditional transition-colors cursor-pointer"
                      >
                        13-Layer Table & Length Stats (Mean/IQR) →
                      </button>
                      <button
                        onClick={() => setCorpusDistExpanded(false)}
                        className="font-mono text-[10px] text-parchment-300 hover:text-white cursor-pointer px-1.5"
                      >
                        [Hide]
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3 text-xs">
                    {/* Tier 1: Complete Full-Text Books */}
                    <div className="p-3 rounded-lg bg-obsidian-950/90 border border-emerald-500/30 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className="font-mono text-[10px] uppercase text-emerald-300 font-bold">
                            Tier 1 · Complete Full-Text Books
                          </span>
                          <span className="px-1.5 py-0.5 rounded bg-emerald-500/15 font-mono text-[9px] text-emerald-300 font-bold">
                            77.09% of Passages
                          </span>
                        </div>
                        <div className="font-serif text-lg font-bold text-parchment-50 tabular-nums">
                          {(summary?.master_manifest?.total_complete_fulltext_books || 13792).toLocaleString()} Books{' '}
                          <span className="text-xs font-mono font-normal text-parchment-300">
                            · 377,647 Passages · 373.48M Words
                          </span>
                        </div>
                        <p className="text-[11px] text-parchment-300 mt-1 leading-relaxed">
                          Segmented into non-overlapping 1,000-word windows (Mean: 989.0w · Median: 1,000w):
                        </p>
                      </div>
                      <div className="mt-2 pt-2 border-t border-white/[0.06] space-y-1 font-mono text-[10px]">
                        <div className="flex justify-between text-parchment-200">
                          <span>• DNB /34 & MARC 856 OA Books:</span>
                          <span className="text-emerald-300 font-bold">9,507 books (124,121 ch.)</span>
                        </div>
                        <div className="flex justify-between text-parchment-200">
                          <span>• HathiTrust HTRC Print Books:</span>
                          <span className="text-sky-300 font-bold">4,050 books (247,994 ch.)</span>
                        </div>
                        <div className="flex justify-between text-parchment-200">
                          <span>• Direct Cloud / GBV / IA OA Books:</span>
                          <span className="text-traditional font-bold">235 books (5,532 ch.)</span>
                        </div>
                      </div>
                    </div>

                    {/* Tier 2: Digitized Inhaltsverzeichnis (TOC) & Reading Sample PDFs */}
                    <div className="p-3 rounded-lg bg-obsidian-950/90 border border-traditional/30 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className="font-mono text-[10px] uppercase text-traditional font-bold">
                            Tier 2 · Digitized TOC & Sample PDFs
                          </span>
                          <span className="px-1.5 py-0.5 rounded bg-traditional/15 font-mono text-[9px] text-traditional font-bold">
                            10.30% of Passages
                          </span>
                        </div>
                        <div className="font-serif text-lg font-bold text-parchment-50 tabular-nums">
                          49,388 Works{' '}
                          <span className="text-xs font-mono font-normal text-parchment-300">
                            · 50,447 PDFs · 19.86M Words
                          </span>
                        </div>
                        <p className="text-[11px] text-parchment-300 mt-1 leading-relaxed">
                          Full chapter hierarchies, section headings & reading samples extracted from PDFs:
                        </p>
                      </div>
                      <div className="mt-2 pt-2 border-t border-white/[0.06] space-y-1 font-mono text-[10px]">
                        <div className="flex justify-between text-parchment-200">
                          <span>• DNB /04 Inhaltsverzeichnis PDFs:</span>
                          <span className="text-traditional font-bold">36,214 works (36,248 PDFs)</span>
                        </div>
                        <div className="flex justify-between text-parchment-200">
                          <span>• GBV / K10plus Consortial TOC PDFs:</span>
                          <span className="text-rose-300 font-bold">13,174 works (14,199 PDFs)</span>
                        </div>
                        <div className="flex justify-between text-parchment-300">
                          <span>• Length (DNB /04 · GBV):</span>
                          <span>Mean 453.4w · 241.2w</span>
                        </div>
                      </div>
                    </div>

                    {/* Tier 3A: DNB deposit.dnb.de Inhaltstexte */}
                    <div className="p-3 rounded-lg bg-obsidian-950/90 border border-neoliberal/30 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className="font-mono text-[10px] uppercase text-neoliberal font-bold">
                            Tier 3A · DNB Deposit Inhaltstexte
                          </span>
                          <span className="px-1.5 py-0.5 rounded bg-neoliberal/15 font-mono text-[9px] text-neoliberal font-bold">
                            11.75% of Passages
                          </span>
                        </div>
                        <div className="font-serif text-lg font-bold text-parchment-50 tabular-nums">
                          57,551 Works{' '}
                          <span className="text-xs font-mono font-normal text-parchment-300">
                            · 57,569 Records · 7.63M Words
                          </span>
                        </div>
                        <p className="text-[11px] text-parchment-300 mt-1 leading-relaxed">
                          Archival publisher blurbs, synopses & MARC 520 summaries from deposit.dnb.de:
                        </p>
                      </div>
                      <div className="mt-2 pt-2 border-t border-white/[0.06] space-y-1 font-mono text-[10px]">
                        <div className="flex justify-between text-parchment-200">
                          <span>• Primary Tier-3A Works:</span>
                          <span className="text-neoliberal font-bold">30,212 unique works</span>
                        </div>
                        <div className="flex justify-between text-parchment-200">
                          <span>• Co-Indexed with TOC / Full Book:</span>
                          <span className="text-parchment-100 font-bold">27,339 works</span>
                        </div>
                        <div className="flex justify-between text-parchment-300">
                          <span>• Document Length:</span>
                          <span>Mean 132.5w (Median 126w · IQR 119w)</span>
                        </div>
                      </div>
                    </div>

                    {/* Tier 3B/3C: Multi-API Enriched Paratexts & OpenAlex Abstracts */}
                    <div className="p-3 rounded-lg bg-obsidian-950/90 border border-critical/30 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className="font-mono text-[10px] uppercase text-critical font-bold">
                            Tier 3B/C · OpenAlex & Enriched
                          </span>
                          <span className="px-1.5 py-0.5 rounded bg-critical/15 font-mono text-[9px] text-critical font-bold">
                            0.91% of Passages
                          </span>
                        </div>
                        <div className="font-serif text-lg font-bold text-parchment-50 tabular-nums">
                          4,156 Works{' '}
                          <span className="text-xs font-mono font-normal text-parchment-300">
                            · 4,188 Records · 0.36M Words
                          </span>
                        </div>
                        <p className="text-[11px] text-parchment-300 mt-1 leading-relaxed">
                          Reconstructed OpenAlex inverted-index abstracts & multi-API MARC21 paratexts:
                        </p>
                      </div>
                      <div className="mt-2 pt-2 border-t border-white/[0.06] space-y-1 font-mono text-[10px]">
                        <div className="flex justify-between text-parchment-200">
                          <span>• Multi-API Enriched Paratexts:</span>
                          <span className="text-critical font-bold">3,530 works (3,561 docs)</span>
                        </div>
                        <div className="flex justify-between text-parchment-200">
                          <span>• OpenAlex German Abstracts:</span>
                          <span className="text-amber-300 font-bold">626 works (627 docs)</span>
                        </div>
                        <div className="flex justify-between text-parchment-300">
                          <span>• OpenAlex Abstract Length:</span>
                          <span>Mean 179.8w (Median 138w · IQR 148w)</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* =================================================================
              WORKSPACE MODE 1: OBSERVATORY BENTO (2x2 SIMULTANEOUS GRID)
             ================================================================= */}
          {workspaceMode === 'bento' && (
            <>
              {/* Upper Bento Row: Topic Posterior Distribution (7 cols) + Diachronic Trajectory (5 cols) */}
              <div className="grid grid-cols-1 2xl:grid-cols-12 gap-4 items-stretch">
                <div className="2xl:col-span-7">
                  <TopicModelViz
                    topics={typedTopics}
                    loading={isTraining}
                    selectedYear={selectedYear}
                    selectedTopicIndex={safeTopicIndex}
                    onSelectTopicIndex={setSelectedTopicIndex}
                    ideologicalFilter={ideologicalFilter}
                    hideInlineInspector={rightInspectorOpen}
                    onOpenInspector={() => setRightInspectorOpen(true)}
                  />
                </div>
                <div className="2xl:col-span-5">
                  <TrendsGraph
                    data={trendsData}
                    publishers={publishersList}
                    publisherCounts={summary?.publisher_counts}
                    publisherWorksCounts={summary?.publisher_works_counts}
                    publisherDirectory={summary?.publisher_directory}
                    selectedPublishers={selectedPublishers}
                    onTogglePublisher={(pub) => handleTogglePublisher(pub, true)}
                    decadeBreakdown={decadeBreakdown}
                    onYearClick={handleYearClick}
                    selectedYear={selectedYear}
                    onDecadeClick={handleDecadeClick}
                    selectedDecade={selectedDecade}
                    onResetTemporal={handleResetTemporal}
                    compact={true}
                  />
                </div>
              </div>

              {/* Lower Bento Row: Institutional Publisher Matrix (7 cols) + Coherence Atlas (5 cols) */}
              <div className="grid grid-cols-1 2xl:grid-cols-12 gap-4 items-stretch">
                {/* Left Cell: Publisher × Ideological Archetype Matrix */}
                <div className="2xl:col-span-7 archival-panel rounded-xl p-4 sm:p-5 flex flex-col justify-between">
                  <div>
                    <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-white/[0.07]">
                      <div>
                        <span className="font-mono text-[10px] uppercase tracking-widest text-traditional">
                          Institutional Imprint Positioning
                        </span>
                        <h3 className="font-serif text-lg sm:text-xl font-bold text-parchment-50">
                          Publisher × Ideological Archetype Matrix
                        </h3>
                      </div>
                      <div className="flex items-center gap-2 font-mono text-[10px]">
                        <span className="text-traditional">■ Trad</span>
                        <span className="text-neoliberal">■ Neo</span>
                        <span className="text-critical">■ Crit</span>
                      </div>
                    </div>

                    <div className="space-y-2.5 max-h-[320px] overflow-y-auto pr-1 custom-scrollbar">
                      {[...publisherArchetypes]
                        .sort((a, b) => {
                          if (!ideologicalFilter) return 0;
                          const key = ideologicalFilter as 'Traditional' | 'Neoliberal' | 'Critical';
                          return (b[key] ?? 0) - (a[key] ?? 0);
                        })
                        .map((item) => {
                        const trad = item.Traditional ?? 0;
                        const neo = item.Neoliberal ?? 0;
                        const crit = item.Critical ?? 0;
                        const isTrad = trad >= neo && trad >= crit;
                        const isNeo = neo > trad && neo >= crit;
                        const dominantLabel = isTrad
                          ? 'Traditional'
                          : isNeo
                          ? 'Neoliberal'
                          : 'Critical';
                        const badgeClass = isTrad
                          ? 'bg-traditional/15 text-traditional border-traditional/30'
                          : isNeo
                          ? 'bg-neoliberal/15 text-neoliberal border-neoliberal/30'
                          : 'bg-critical/15 text-critical border-critical/30';

                        const isPubActive = selectedPublishers.includes(item.publisher);
                        const matchesRq = !ideologicalFilter || dominantLabel === ideologicalFilter;

                        return (
                          <div
                            key={item.publisher}
                            onClick={() => handleTogglePublisher(item.publisher, true)}
                            title="Click to isolate/toggle this publisher in the active LDA sub-corpus"
                            className={clsx(
                              'p-2.5 rounded-lg border transition-all cursor-pointer',
                              isPubActive
                                ? 'bg-traditional/10 border-traditional shadow-glow-gold'
                                : matchesRq && ideologicalFilter
                                ? 'bg-obsidian-900 border-white/25'
                                : 'bg-obsidian-950/80 border-white/[0.06] hover:border-white/20',
                              !matchesRq && ideologicalFilter && 'opacity-50'
                            )}
                          >
                            <div className="flex items-center justify-between gap-2 mb-1.5">
                              <div className="flex items-center gap-2 min-w-0">
                                <span className="font-serif font-bold text-sm text-parchment-50 truncate">
                                  {isPubActive ? `✓ ${item.publisher}` : item.publisher}
                                </span>
                                <span
                                  className={clsx(
                                    'px-1.5 py-0.5 rounded border font-mono text-[9px] font-semibold shrink-0',
                                    badgeClass
                                  )}
                                >
                                  {dominantLabel}
                                </span>
                              </div>
                              <div className="flex items-center gap-2 font-mono text-[10px] tabular-nums shrink-0">
                                <span className="text-traditional">{trad}%</span>
                                <span className="text-neoliberal">{neo}%</span>
                                <span className="text-critical">{crit}%</span>
                              </div>
                            </div>
                            <div className="w-full h-2 rounded-full overflow-hidden flex bg-obsidian-900 p-0.5 gap-0.5">
                              <div
                                style={{ width: `${trad}%` }}
                                className="h-full bg-traditional rounded-l-full"
                              />
                              <div style={{ width: `${neo}%` }} className="h-full bg-neoliberal" />
                              <div
                                style={{ width: `${crit}%` }}
                                className="h-full bg-critical rounded-r-full"
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Right Cell: Coherence Grid Validation Atlas */}
                <div className="2xl:col-span-5 archival-panel rounded-xl p-4 sm:p-5 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/[0.07]">
                      <div>
                        <span className="font-mono text-[10px] uppercase tracking-widest text-emerald-400">
                          Röder et al. (2015) Validation
                        </span>
                        <h3 className="font-serif text-lg sm:text-xl font-bold text-parchment-50">
                          Coherence Grid (C<sub>v</sub> vs. U<sub>Mass</sub>)
                        </h3>
                      </div>
                      <TrendingUp className="w-4 h-4 text-emerald-400" />
                    </div>

                    <div className="overflow-x-auto max-h-[320px] overflow-y-auto custom-scrollbar">
                      <table className="w-full text-left border-collapse font-mono text-[11px]">
                        <thead>
                          <tr className="border-b border-white/10 text-parchment-300 text-[9px] uppercase">
                            <th className="py-1.5 px-2">K</th>
                            <th className="py-1.5 px-2">Cv (NPMI)</th>
                            <th className="py-1.5 px-2">UMass</th>
                            <th className="py-1.5 px-2 text-right">Regime</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/[0.05]">
                          {coherenceGrid.map((row) => {
                            const isActive = row.k === numTopics;
                            const isPeak = row.k === 25;
                            return (
                              <tr
                                key={row.k}
                                onClick={() => handleRegimeSelect(row.k)}
                                className={clsx(
                                  'cursor-pointer transition-colors',
                                  isActive
                                    ? 'bg-traditional/15 text-traditional font-bold'
                                    : 'hover:bg-white/[0.04] text-parchment-200'
                                )}
                              >
                                <td className="py-1.5 px-2 tabular-nums">K={row.k}</td>
                                <td className="py-1.5 px-2 tabular-nums text-emerald-300">
                                  {row.c_v.toFixed(4)}
                                </td>
                                <td className="py-1.5 px-2 tabular-nums text-neoliberal">
                                  {row.u_mass.toFixed(3)}
                                </td>
                                <td className="py-1.5 px-2 text-right">
                                  {isPeak ? (
                                    <span className="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 text-[9px]">
                                      Optimum
                                    </span>
                                  ) : row.k === 12 ? (
                                    <span className="px-1.5 py-0.5 rounded bg-traditional/15 text-traditional text-[9px]">
                                      Meso
                                    </span>
                                  ) : (
                                    <span className="text-parchment-300 text-[9px]">
                                      {row.k <= 8 ? 'Macro' : 'Micro'}
                                    </span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>

              {/* pyLDAvis-Style 2D Inter-Topic Distance Map & λ-Relevance Salience Explorer */}
              <InterTopicDistanceMap
                topics={typedTopics}
                selectedTopicIndex={safeTopicIndex}
                onSelectTopicIndex={setSelectedTopicIndex}
                ideologicalFilter={ideologicalFilter}
                numTopics={numTopics}
                ldaMode={ldaMode}
              />

              {/* Diachronic Word-Shift & Conceptual Drift Explorer (1970s-2020s) */}
              <ConceptualDriftExplorer
                driftData={conceptualDrift}
                ideologicalFilter={ideologicalFilter}
                onDecadeClick={handleDecadeClick}
                onPublisherClick={(pub) => handleTogglePublisher(pub, true)}
              />

              {/* Modules 3, 5, 6: Statistical Breakpoint Tests, Custom Seed Workbench & LaTeX/BibTeX Exporter */}
              <HypothesisAndExportWorkbench
                topics={typedTopics}
                numTopics={numTopics}
                ldaMode={ldaMode}
                coherenceScore={coherenceScore}
                cvCoherence={cvCoherence}
                modesComparison={modesComparison}
                sldaDiagnostics={sldaDiagnostics}
                publisherArchetypes={publisherArchetypes}
                seedLexicons={seedLexicons}
                isTraining={isTraining}
                onUpdateCustomSeeds={updateCustomSeeds}
                onResetCustomSeeds={resetCustomSeeds}
                onYearClick={handleYearClick}
                robustnessTelemetry={robustnessTelemetry}
              />

              {/* Full End-to-End Pipeline & Methodology Explainer Section */}
              <PipelineExplainer
                summary={summary}
                vocabSize={vocabSize}
                numTopics={numTopics}
                coherenceScore={coherenceScore}
                cvCoherence={cvCoherence}
                isTraining={isTraining}
                onRunFullPipeline={() =>
                  runLDA(selectedYear, selectedDecade, numTopics, ldaMode, selectedPublishers)
                }
                ldaMode={ldaMode}
                onSelectLdaMode={handleModeSelect}
                modesComparison={modesComparison}
                sldaDiagnostics={sldaDiagnostics}
                seedLexicons={seedLexicons}
                religiousBoostWords={religiousBoostWords}
                robustnessTelemetry={robustnessTelemetry}
              />
            </>
          )}

          {/* =================================================================
              WORKSPACE MODE 1Z: 2D INTER-TOPIC DISTANCE MAP (pyLDAvis)
             ================================================================= */}
          {workspaceMode === 'distance' && (
            <InterTopicDistanceMap
              topics={typedTopics}
              selectedTopicIndex={safeTopicIndex}
              onSelectTopicIndex={setSelectedTopicIndex}
              ideologicalFilter={ideologicalFilter}
              numTopics={numTopics}
              ldaMode={ldaMode}
            />
          )}

          {/* =================================================================
              WORKSPACE MODE 1A: DIACHRONIC WORD-SHIFT & CONCEPTUAL DRIFT EXPLORER
             ================================================================= */}
          {workspaceMode === 'drift' && (
            <ConceptualDriftExplorer
              driftData={conceptualDrift}
              ideologicalFilter={ideologicalFilter}
              onDecadeClick={handleDecadeClick}
              onPublisherClick={(pub) => handleTogglePublisher(pub, true)}
            />
          )}

          {/* =================================================================
              WORKSPACE MODE 1W: HYPOTHESIS TESTS, CUSTOM SEEDS & LaTeX EXPORTER
             ================================================================= */}
          {workspaceMode === 'workbench' && (
            <HypothesisAndExportWorkbench
              topics={typedTopics}
              numTopics={numTopics}
              ldaMode={ldaMode}
              coherenceScore={coherenceScore}
              cvCoherence={cvCoherence}
              modesComparison={modesComparison}
              sldaDiagnostics={sldaDiagnostics}
              publisherArchetypes={publisherArchetypes}
              seedLexicons={seedLexicons}
              isTraining={isTraining}
              onUpdateCustomSeeds={updateCustomSeeds}
              onResetCustomSeeds={resetCustomSeeds}
              onYearClick={handleYearClick}
              robustnessTelemetry={robustnessTelemetry}
            />
          )}

          {/* =================================================================
              WORKSPACE MODE 1B: FULL PIPELINE & METHODOLOGY ARCHITECTURE
             ================================================================= */}
          {workspaceMode === 'pipeline' && (
            <PipelineExplainer
              summary={summary}
              vocabSize={vocabSize}
              numTopics={numTopics}
              coherenceScore={coherenceScore}
              cvCoherence={cvCoherence}
              isTraining={isTraining}
              onRunFullPipeline={() =>
                runLDA(selectedYear, selectedDecade, numTopics, ldaMode, selectedPublishers)
              }
              ldaMode={ldaMode}
              onSelectLdaMode={handleModeSelect}
              modesComparison={modesComparison}
              sldaDiagnostics={sldaDiagnostics}
              seedLexicons={seedLexicons}
              religiousBoostWords={religiousBoostWords}
              robustnessTelemetry={robustnessTelemetry}
            />
          )}

          {/* =================================================================
              WORKSPACE MODE 2: TOPIC & LEXICAL DEEP-DIVE
             ================================================================= */}
          {workspaceMode === 'topics' && (
            <div className="space-y-4">
              <InterTopicDistanceMap
                topics={typedTopics}
                selectedTopicIndex={safeTopicIndex}
                onSelectTopicIndex={setSelectedTopicIndex}
                ideologicalFilter={ideologicalFilter}
                numTopics={numTopics}
                ldaMode={ldaMode}
              />
              <TopicModelViz
                topics={typedTopics}
                loading={isTraining}
                selectedYear={selectedYear}
                selectedTopicIndex={safeTopicIndex}
                onSelectTopicIndex={setSelectedTopicIndex}
                ideologicalFilter={ideologicalFilter}
                hideInlineInspector={false}
              />
            </div>
          )}

          {/* =================================================================
              WORKSPACE MODE 3: PUBLISHER & COHERENCE ATLAS
             ================================================================= */}
          {workspaceMode === 'matrix' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 2xl:grid-cols-12 gap-4 items-stretch">
                {/* Publisher Matrix */}
                <div className="2xl:col-span-7 archival-panel rounded-xl p-4 sm:p-5">
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-white/[0.07]">
                    <div>
                      <span className="font-mono text-[10px] uppercase tracking-widest text-traditional">
                        Institutional Imprint Positioning
                      </span>
                      <h3 className="font-serif text-lg sm:text-xl font-bold text-parchment-50">
                        Publisher × Ideological Archetype Matrix
                      </h3>
                    </div>
                    <div className="flex items-center gap-2 font-mono text-[10px]">
                      <span className="text-traditional">■ Trad</span>
                      <span className="text-neoliberal">■ Neo</span>
                      <span className="text-critical">■ Crit</span>
                    </div>
                  </div>
                  <div className="space-y-2.5">
                    {publisherArchetypes.map((item) => {
                      const trad = item.Traditional ?? 0;
                      const neo = item.Neoliberal ?? 0;
                      const crit = item.Critical ?? 0;
                      const isTrad = trad >= neo && trad >= crit;
                      const isNeo = neo > trad && neo >= crit;
                      const dominantLabel = isTrad
                        ? 'Traditional'
                        : isNeo
                        ? 'Neoliberal'
                        : 'Critical';
                      const badgeClass = isTrad
                        ? 'bg-traditional/15 text-traditional border-traditional/30'
                        : isNeo
                        ? 'bg-neoliberal/15 text-neoliberal border-neoliberal/30'
                        : 'bg-critical/15 text-critical border-critical/30';
                      return (
                        <div
                          key={item.publisher}
                          className="p-2.5 rounded-lg bg-obsidian-950/80 border border-white/[0.06]"
                        >
                          <div className="flex items-center justify-between gap-2 mb-1.5">
                            <div className="flex items-center gap-2 min-w-0">
                              <span className="font-serif font-bold text-sm text-parchment-50 truncate">
                                {item.publisher}
                              </span>
                              <span
                                className={clsx(
                                  'px-1.5 py-0.5 rounded border font-mono text-[9px] font-semibold shrink-0',
                                  badgeClass
                                )}
                              >
                                {dominantLabel}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 font-mono text-[10px] tabular-nums shrink-0">
                              <span className="text-traditional">{trad}%</span>
                              <span className="text-neoliberal">{neo}%</span>
                              <span className="text-critical">{crit}%</span>
                            </div>
                          </div>
                          <div className="w-full h-2 rounded-full overflow-hidden flex bg-obsidian-900 p-0.5 gap-0.5">
                            <div
                              style={{ width: `${trad}%` }}
                              className="h-full bg-traditional rounded-l-full"
                            />
                            <div style={{ width: `${neo}%` }} className="h-full bg-neoliberal" />
                            <div
                              style={{ width: `${crit}%` }}
                              className="h-full bg-critical rounded-r-full"
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Coherence Grid Validation Table */}
                <div className="2xl:col-span-5 archival-panel rounded-xl p-4 sm:p-5">
                  <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/[0.07]">
                    <div>
                      <span className="font-mono text-[10px] uppercase tracking-widest text-emerald-400">
                        Röder et al. (2015) Validation
                      </span>
                      <h3 className="font-serif text-lg sm:text-xl font-bold text-parchment-50">
                        Coherence Grid (C<sub>v</sub> vs. U<sub>Mass</sub>)
                      </h3>
                    </div>
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                  </div>
                  <table className="w-full text-left border-collapse font-mono text-[11px]">
                    <thead>
                      <tr className="border-b border-white/10 text-parchment-300 text-[9px] uppercase">
                        <th className="py-1.5 px-2">K</th>
                        <th className="py-1.5 px-2">Cv (NPMI)</th>
                        <th className="py-1.5 px-2">UMass</th>
                        <th className="py-1.5 px-2 text-right">Regime</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.05]">
                      {coherenceGrid.map((row) => {
                        const isActive = row.k === numTopics;
                        const isPeak = row.k === 25;
                        return (
                          <tr
                            key={row.k}
                            onClick={() => handleRegimeSelect(row.k)}
                            className={clsx(
                              'cursor-pointer transition-colors',
                              isActive
                                ? 'bg-traditional/15 text-traditional font-bold'
                                : 'hover:bg-white/[0.04] text-parchment-200'
                            )}
                          >
                            <td className="py-1.5 px-2 tabular-nums">K={row.k}</td>
                            <td className="py-1.5 px-2 tabular-nums text-emerald-300">
                              {row.c_v.toFixed(4)}
                            </td>
                            <td className="py-1.5 px-2 tabular-nums text-neoliberal">
                              {row.u_mass.toFixed(3)}
                            </td>
                            <td className="py-1.5 px-2 text-right">
                              {isPeak ? (
                                <span className="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 text-[9px]">
                                  Optimum
                                </span>
                              ) : row.k === 12 ? (
                                <span className="px-1.5 py-0.5 rounded bg-traditional/15 text-traditional text-[9px]">
                                  Meso
                                </span>
                              ) : (
                                <span className="text-parchment-300 text-[9px]">
                                  {row.k <= 8 ? 'Macro' : 'Micro'}
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              <TrendsGraph
                data={trendsData}
                publishers={publishersList}
                publisherCounts={summary?.publisher_counts}
                publisherWorksCounts={summary?.publisher_works_counts}
                publisherDirectory={summary?.publisher_directory}
                selectedPublishers={selectedPublishers}
                onTogglePublisher={(pub) => handleTogglePublisher(pub, true)}
                decadeBreakdown={decadeBreakdown}
                onYearClick={handleYearClick}
                selectedYear={selectedYear}
                onDecadeClick={handleDecadeClick}
                selectedDecade={selectedDecade}
                onResetTemporal={handleResetTemporal}
                compact={false}
              />
            </div>
          )}
        </main>

        {/* -------------------------------------------------------------------
            PANE 3: RIGHT DOCKED MARC21 & APA 7th INSPECTOR DRAWER
           ------------------------------------------------------------------- */}
        <AnimatePresence initial={false}>
          {rightInspectorOpen && (
            <motion.aside
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 370, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className="w-full lg:w-[360px] xl:w-[385px] shrink-0 border-t lg:border-t-0 lg:border-l border-white/[0.08] bg-obsidian-900/90 flex flex-col lg:h-full lg:overflow-y-auto custom-scrollbar"
            >
              {/* Sticky Inspector Header */}
              <div className="p-3.5 border-b border-white/[0.08] bg-obsidian-950/90 sticky top-0 z-10 space-y-2.5">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-traditional" />
                    <span className="font-mono text-[10px] uppercase tracking-widest text-parchment-200">
                      MARC21 & APA 7th Inspector
                    </span>
                  </div>
                  <button
                    onClick={handleCopyAllTopicCitations}
                    title="Copy all APA 7th citations for this topic"
                    className="inline-flex items-center gap-1 px-2 py-1 rounded bg-traditional/15 hover:bg-traditional/25 border border-traditional/40 font-mono text-[10px] text-traditional transition-colors cursor-pointer"
                  >
                    {copiedCitationKey === 'batch-topic-apa' ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-400" />
                        <span>Copied All!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy All APA</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Currently Inspected Topic Summary Pill */}
                {activeTopic && (
                  <div className="p-2.5 rounded-lg bg-obsidian-900 border border-white/[0.07] flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span
                          className="w-2 h-2 rounded-full shrink-0"
                          style={{ backgroundColor: activeTopicTheme.hex }}
                        />
                        <span className="font-serif font-bold text-sm text-parchment-50 truncate">
                          Topic #{activeTopic.id + 1}: {activeTopicTheme.shortLabel}
                        </span>
                      </div>
                      <p className="font-mono text-[10px] text-parchment-300 truncate mt-0.5">
                        {activeTopic.keywords
                          .slice(0, 4)
                          .map((k: Keyword) => k.word)
                          .join(' · ')}
                      </p>
                    </div>
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-white/[0.05] text-parchment-200 shrink-0">
                      {filteredInspectorDocs.length} Docs
                    </span>
                  </div>
                )}

                {/* Search Input inside Inspector */}
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-parchment-300 absolute left-2.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={inspectorSearch}
                    onChange={(e) => setInspectorSearch(e.target.value)}
                    placeholder="Search MARC21 titles, publishers, blurbs..."
                    className="w-full bg-obsidian-900 border border-white/10 rounded-lg pl-8 pr-3 py-1.5 text-xs font-mono text-parchment-100 placeholder:text-parchment-300/50 focus:outline-none focus:border-traditional"
                  />
                </div>
              </div>

              {/* Inspector Body: Publisher Imprint Concentration + MARC21 Cards */}
              <div className="p-3.5 space-y-3 flex-1">
                {activeTopic?.top_publishers &&
                  Object.keys(activeTopic.top_publishers).length > 0 && (
                    <div className="p-3 rounded-xl bg-obsidian-950/70 border border-white/[0.06]">
                      <div className="flex items-center gap-1.5 mb-2">
                        <Building2 className="w-3.5 h-3.5 text-traditional" />
                        <span className="font-mono text-[10px] uppercase tracking-widest text-parchment-300">
                          Topic Imprint Concentration
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {Object.entries(activeTopic.top_publishers).map(([pub, count]) => (
                          <span
                            key={pub}
                            className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-obsidian-900 border border-white/[0.08] text-[10px] text-parchment-100"
                          >
                            <span>{pub}</span>
                            <span
                              className="font-mono font-bold"
                              style={{ color: activeTopicTheme.hex }}
                            >
                              {Number(count)}
                            </span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                {/* Representative MARC21 Cards */}
                <div className="space-y-2.5">
                  {filteredInspectorDocs.length > 0 ? (
                    filteredInspectorDocs.map((doc: RepresentativeDoc, idx: number) => {
                      const docYear = doc.year || doc.date || 'o. J.';
                      const apaText =
                        doc.apa_citation || `${doc.publisher}. (${docYear}). ${doc.title}.`;
                      const copyKey = `inspector-doc-${idx}`;
                      const isCopied = copiedCitationKey === copyKey;

                      return (
                        <div
                          key={idx}
                          className="p-3 rounded-xl bg-obsidian-950/90 border border-white/[0.07] hover:border-white/20 transition-all space-y-2"
                        >
                          <div className="flex items-center justify-between gap-2 flex-wrap">
                            <span
                              className="px-2 py-0.5 rounded font-mono text-[9px] font-semibold border border-white/10 bg-white/[0.03]"
                              style={{ color: activeTopicTheme.hex }}
                            >
                              {doc.publisher}
                            </span>
                            <div className="flex items-center gap-1.5">
                              {doc.probability !== undefined && (
                                <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 font-mono text-[9px] text-emerald-300 font-bold">
                                  θ = {doc.probability}%
                                </span>
                              )}
                              <span className="font-mono text-[10px] text-parchment-300">
                                Tag 264$c · {docYear}
                              </span>
                            </div>
                          </div>

                          <h4 className="font-serif text-sm font-bold text-parchment-50 leading-snug">
                            {doc.title}
                          </h4>

                          {(doc.author || doc.corpus_layer) && (
                            <div className="flex flex-wrap items-center justify-between gap-1.5 text-[10px] font-mono text-parchment-300">
                              {doc.author && doc.author !== 'N/A' && (
                                <span className="truncate">Tag 100$a · {doc.author}</span>
                              )}
                              {doc.corpus_layer && (
                                <span className="px-1.5 py-0.5 rounded bg-white/[0.04] border border-white/[0.07] text-[9px] text-neoliberal">
                                  {doc.corpus_layer}
                                </span>
                              )}
                            </div>
                          )}

                          {doc.snippet && (
                            <p className="text-[11px] text-parchment-200 leading-relaxed line-clamp-3 italic border-l-2 border-white/15 pl-2.5">
                              „{doc.snippet}“
                            </p>
                          )}

                          <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between gap-2">
                            <p className="font-mono text-[9px] text-parchment-300 truncate">
                              {apaText}
                            </p>
                            <button
                              onClick={() => copyText(copyKey, apaText)}
                              className="shrink-0 inline-flex items-center gap-1 px-2 py-1 rounded bg-white/[0.05] hover:bg-white/[0.12] border border-white/10 font-mono text-[9px] text-parchment-100 cursor-pointer"
                            >
                              {isCopied ? (
                                <>
                                  <Check className="w-2.5 h-2.5 text-emerald-400" />
                                  <span className="text-emerald-300">Copied</span>
                                </>
                              ) : (
                                <>
                                  <Copy className="w-2.5 h-2.5 text-traditional" />
                                  <span>APA 7th</span>
                                </>
                              )}
                            </button>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="p-6 rounded-xl bg-obsidian-950/50 border border-white/[0.05] text-center">
                      <p className="font-mono text-xs text-parchment-300">
                        No MARC21 monographs match "{inspectorSearch}".
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default App;
