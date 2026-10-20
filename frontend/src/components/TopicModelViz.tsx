import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';
import { Layers, Activity, Search, BookText, Quote, Copy, Check, Building2, Sparkles, PanelRightOpen } from 'lucide-react';
import clsx from 'clsx';

export interface Keyword {
  word: string;
  weight: number;
}

export interface ArchetypeInfo {
  label: string;
  confidence: number;
  scores?: Record<string, number>;
}

export interface RepresentativeDoc {
  title: string;
  publisher: string;
  year: string;
  apa_citation?: string;
  snippet?: string;
}

export interface Topic {
  id: number;
  keywords: Keyword[];
  archetype?: ArchetypeInfo;
  top_publishers?: Record<string, number>;
  representative_docs?: RepresentativeDoc[];
}

interface TopicModelVizProps {
  topics: Topic[];
  loading: boolean;
  selectedYear?: number | null;
  selectedTopicIndex?: number;
  onSelectTopicIndex?: (index: number) => void;
  ideologicalFilter?: string | null;
  hideInlineInspector?: boolean;
  onOpenInspector?: () => void;
}

export interface ArchetypeTheme {
  id: 'Traditional' | 'Neoliberal' | 'Critical' | 'Mixed';
  hex: string;
  hexSecondary: string;
  badgeClass: string;
  borderGlow: string;
  textClass: string;
  bgSubtle: string;
  shortLabel: string;
  germanSubtitle: string;
}

export const getArchetypeTheme = (label?: string): ArchetypeTheme => {
  if (!label) {
    return {
      id: 'Mixed',
      hex: '#EAB308',
      hexSecondary: '#A16207',
      badgeClass: 'bg-traditional-subtle text-traditional border-traditional/30',
      borderGlow: 'border-traditional/40 shadow-glow-gold',
      textClass: 'text-traditional',
      bgSubtle: 'bg-traditional/10',
      shortLabel: 'Unclassified Regime',
      germanSubtitle: 'Allgemeiner Diskurs',
    };
  }
  if (label.includes('Traditional') || label.includes('Theological')) {
    return {
      id: 'Traditional',
      hex: '#EAB308',
      hexSecondary: '#CA8A04',
      badgeClass: 'bg-traditional-subtle text-traditional border-traditional/30',
      borderGlow: 'border-traditional/40 shadow-glow-gold',
      textClass: 'text-traditional',
      bgSubtle: 'bg-traditional/10',
      shortLabel: 'Traditional / Ecclesiastical',
      germanSubtitle: 'Kirchlich-Dogmatischer Diskurs',
    };
  }
  if (label.includes('Neoliberal') || label.includes('Self-Help')) {
    return {
      id: 'Neoliberal',
      hex: '#38BDF8',
      hexSecondary: '#0284C7',
      badgeClass: 'bg-neoliberal-subtle text-neoliberal border-neoliberal/30',
      borderGlow: 'border-neoliberal/40 shadow-glow-cyan',
      textClass: 'text-neoliberal',
      bgSubtle: 'bg-neoliberal/10',
      shortLabel: 'Neoliberal / Self-Optimization',
      germanSubtitle: 'Achtsamkeit & Lebenshilfe-Markt',
    };
  }
  if (label.includes('Critical') || label.includes('Secular')) {
    return {
      id: 'Critical',
      hex: '#FB7185',
      hexSecondary: '#E11D48',
      badgeClass: 'bg-critical-subtle text-critical border-critical/30',
      borderGlow: 'border-critical/40 shadow-glow-rose',
      textClass: 'text-critical',
      bgSubtle: 'bg-critical/10',
      shortLabel: 'Critical / Secular-Humanist',
      germanSubtitle: 'Kritische Theorie & Säkularisierung',
    };
  }
  return {
    id: 'Mixed',
    hex: '#A78BFA',
    hexSecondary: '#7C3AED',
    badgeClass: 'bg-violet-500/10 text-violet-300 border-violet-500/30',
    borderGlow: 'border-violet-500/40',
    textClass: 'text-violet-300',
    bgSubtle: 'bg-violet-500/10',
    shortLabel: 'Hybrid / Cross-Discursive',
    germanSubtitle: 'Interdisziplinärer Übergang',
  };
};

export const TopicModelViz: React.FC<TopicModelVizProps> = ({
  topics,
  loading,
  selectedYear,
  selectedTopicIndex: controlledIndex,
  onSelectTopicIndex,
  ideologicalFilter,
  hideInlineInspector = false,
  onOpenInspector,
}) => {
  const [internalIndex, setInternalIndex] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [copiedCitation, setCopiedCitation] = useState<string | null>(null);

  const selectedTopicIndex = controlledIndex !== undefined ? controlledIndex : internalIndex;
  const setSelectedTopicIndex = (idx: number) => {
    if (onSelectTopicIndex) {
      onSelectTopicIndex(idx);
    } else {
      setInternalIndex(idx);
    }
  };

  const safeIndex = selectedTopicIndex < topics.length ? selectedTopicIndex : 0;
  const currentTopic = topics[safeIndex];
  const currentTheme = getArchetypeTheme(currentTopic?.archetype?.label);

  const handleCopyCitation = (citation: string) => {
    navigator.clipboard.writeText(citation);
    setCopiedCitation(citation);
    setTimeout(() => setCopiedCitation(null), 2000);
  };

  const getSpectrumPercentages = (topic?: Topic) => {
    const scores = topic?.archetype?.scores;
    if (!scores) {
      return { trad: 34, neo: 33, crit: 33 };
    }
    const tradRaw = scores['Traditional / Theological'] || 0;
    const neoRaw = scores['Neoliberal / Self-Help'] || 0;
    const critRaw = scores['Critical / Secular-Academic'] || 0;
    const total = tradRaw + neoRaw + critRaw;
    if (total <= 0) {
      return { trad: 34, neo: 33, crit: 33 };
    }
    const trad = Math.round((tradRaw / total) * 100);
    const neo = Math.round((neoRaw / total) * 100);
    const crit = Math.max(0, 100 - trad - neo);
    return { trad, neo, crit };
  };

  if (loading) {
    return (
      <div className="archival-panel rounded-xl p-8 flex flex-col items-center justify-center min-h-[380px]">
        <div className="relative w-12 h-12 flex items-center justify-center mb-4">
          <div className="absolute inset-0 rounded-full border-2 border-traditional/20 animate-ping" />
          <div className="w-9 h-9 rounded-full border-2 border-t-traditional border-r-neoliberal border-b-critical border-l-transparent animate-spin" />
        </div>
        <p className="font-serif text-lg text-parchment-100 tracking-wide">
          Estimating Dirichlet-Multinomial Posterior Distributions...
        </p>
        <p className="font-mono text-[11px] text-parchment-300 mt-1.5">
          {selectedYear
            ? `Temporal Slice: Year ${selectedYear} · Lemmatizing via spaCy de_core_news_lg`
            : 'Full DNB Corpus (2005–2026) · Computing Röder et al. (2015) Cv Coherence'}
        </p>
      </div>
    );
  }

  if (!topics || topics.length === 0) {
    return (
      <div className="archival-panel rounded-xl p-8 flex flex-col items-center justify-center min-h-[340px] text-center">
        <Layers className="w-9 h-9 text-parchment-300 mb-3 opacity-60" />
        <p className="font-serif text-lg text-parchment-100 mb-1">
          No Latent Topics Available for This Slice
        </p>
        <p className="text-xs text-parchment-300 max-w-md">
          Adjust the Bayesian granularity parameter <span className="font-mono text-traditional">K</span> in the left command rail or reset the temporal year filter.
        </p>
      </div>
    );
  }

  const spectrum = getSpectrumPercentages(currentTopic);
  const filteredKeywords = (currentTopic?.keywords || []).filter((kw) =>
    kw.word.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="archival-panel rounded-xl p-4 sm:p-5 flex flex-col h-full justify-between"
    >
      {/* Top Header Strip */}
      <div>
        <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-white/[0.07]">
          <div className="flex items-center gap-2.5">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-white/[0.04] border border-white/10 font-mono text-[10px] uppercase tracking-widest text-parchment-200">
              <Sparkles className="w-3 h-3 text-traditional" />
              Dirichlet Posterior (φ<sub>k</sub>)
            </span>
            <h3 className="font-serif text-lg sm:text-xl font-bold text-parchment-50">
              Topic #{currentTopic ? currentTopic.id + 1 : 1}:{' '}
              <span className={currentTheme.textClass}>{currentTheme.shortLabel}</span>
            </h3>
          </div>

          <div className="flex items-center gap-2">
            {selectedYear && (
              <span className="px-2 py-0.5 rounded bg-traditional/15 border border-traditional/40 font-mono text-[10px] text-traditional">
                Slice: {selectedYear}
              </span>
            )}
            <span
              className={clsx(
                'px-2.5 py-0.5 rounded border font-mono text-[10px] font-semibold',
                currentTheme.badgeClass
              )}
            >
              {currentTopic?.archetype?.confidence || 0}% Alignment
            </span>
            {hideInlineInspector && onOpenInspector && (
              <button
                onClick={onOpenInspector}
                title="Inspect MARC21 Records & APA 7th Citations"
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 font-mono text-[10px] text-parchment-200 transition-colors cursor-pointer"
              >
                <PanelRightOpen className="w-3 h-3 text-traditional" />
                <span>{currentTopic?.representative_docs?.length || 0} MARC21 Docs</span>
              </button>
            )}
          </div>
        </div>

        {/* Compact Horizontal Topic Switcher Pill Bar */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-2.5 mb-3 custom-scrollbar">
          {topics.map((t, idx) => {
            const theme = getArchetypeTheme(t.archetype?.label);
            const isSelected = idx === safeIndex;
            const matchesFilter = !ideologicalFilter || theme.id === ideologicalFilter;

            return (
              <button
                key={t.id}
                onClick={() => setSelectedTopicIndex(idx)}
                className={clsx(
                  'group relative shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-left transition-all duration-150 cursor-pointer',
                  isSelected
                    ? clsx('bg-obsidian-800', theme.borderGlow)
                    : 'bg-obsidian-950/70 border-white/[0.07] hover:border-white/20 hover:bg-obsidian-850',
                  !matchesFilter && 'opacity-35'
                )}
              >
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: theme.hex }}
                />
                <span className="font-mono text-[11px] font-bold text-parchment-100">
                  T{String(t.id + 1).padStart(2, '0')}
                </span>
                <span className="text-[11px] text-parchment-300 max-w-[110px] truncate hidden sm:inline">
                  {t.keywords.slice(0, 2).map((k) => k.word).join(' · ')}
                </span>
              </button>
            );
          })}
        </div>

        {/* 3-Way Ideological Archetype Spectrum Bar */}
        <div className="bg-obsidian-950/90 border border-white/[0.07] rounded-lg p-3 mb-3">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
            <span className="font-mono text-[10px] uppercase tracking-widest text-parchment-300">
              3-Way Ideological Regime Spectrum ({currentTheme.germanSubtitle})
            </span>
            <div className="flex items-center gap-3 font-mono text-[10px] tabular-nums">
              <span className="text-traditional">● Trad: {spectrum.trad}%</span>
              <span className="text-neoliberal">● Neo: {spectrum.neo}%</span>
              <span className="text-critical">● Crit: {spectrum.crit}%</span>
            </div>
          </div>
          <div className="w-full h-2 rounded-full overflow-hidden flex bg-obsidian-900 p-0.5 gap-0.5 border border-white/[0.05]">
            <div
              style={{ width: `${spectrum.trad}%` }}
              className="h-full bg-traditional rounded-l-full transition-all duration-500"
              title={`Traditional / Theological: ${spectrum.trad}%`}
            />
            <div
              style={{ width: `${spectrum.neo}%` }}
              className="h-full bg-neoliberal transition-all duration-500"
              title={`Neoliberal / Self-Help: ${spectrum.neo}%`}
            />
            <div
              style={{ width: `${spectrum.crit}%` }}
              className="h-full bg-critical rounded-r-full transition-all duration-500"
              title={`Critical / Secular-Academic: ${spectrum.crit}%`}
            />
          </div>
        </div>
      </div>

      {/* Main Content Area: Either Chart + Compact Lexical Table (when Right Inspector is open) OR Chart + MARC21 Inspector */}
      <AnimatePresence mode="wait">
        {currentTopic && (
          <motion.div
            key={currentTopic.id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="space-y-3"
          >
            {/* Search & Lemma Filter Bar */}
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5" style={{ color: currentTheme.hex }} />
                <span className="font-mono text-[10px] uppercase tracking-wider text-parchment-200">
                  Top Lemmas Ranked by Posterior Probability P(w | z<sub>{currentTopic.id + 1}</sub>)
                </span>
              </div>
              <div className="relative w-44 sm:w-52">
                <Search className="w-3 h-3 text-parchment-300 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Filter topic lemmas..."
                  className="w-full bg-obsidian-950 border border-white/10 rounded-md pl-7 pr-2.5 py-1 text-[11px] font-mono text-parchment-100 placeholder:text-parchment-300/50 focus:outline-none focus:border-traditional"
                />
              </div>
            </div>

            {/* Bar Chart + Top Lexical Weights Pill Grid */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-stretch">
              <div className="md:col-span-8 h-[250px] bg-obsidian-950/60 border border-white/[0.06] rounded-lg p-2.5">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={filteredKeywords}
                    layout="vertical"
                    margin={{ top: 2, right: 18, left: 12, bottom: 2 }}
                  >
                    <CartesianGrid
                      strokeDasharray="2 4"
                      stroke="rgba(255,255,255,0.05)"
                      horizontal={true}
                      vertical={true}
                    />
                    <XAxis
                      type="number"
                      stroke="#6E6D68"
                      fontSize={10}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(val) => val.toFixed(3)}
                    />
                    <YAxis
                      dataKey="word"
                      type="category"
                      stroke="#ECE8DF"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      width={105}
                      fontFamily="JetBrains Mono, monospace"
                    />
                    <Tooltip
                      cursor={{ fill: 'rgba(255, 255, 255, 0.04)' }}
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload as Keyword;
                          return (
                            <div className="bg-obsidian-900 border border-white/15 px-3 py-2 rounded-lg shadow-archival">
                              <p className="font-serif text-sm font-bold text-parchment-50">
                                „{data.word}“
                              </p>
                              <p className="font-mono text-[11px] mt-0.5" style={{ color: currentTheme.hex }}>
                                φ weight: {data.weight.toFixed(4)}
                              </p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Bar dataKey="weight" radius={[0, 4, 4, 0]} barSize={15}>
                      {filteredKeywords.map((_, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={currentTheme.hex}
                          fillOpacity={Math.max(0.35, 1 - index * 0.06)}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Right Column inside Chart Box: Lexical Probability Table + Imprint Share */}
              <div className="md:col-span-4 bg-obsidian-950/60 border border-white/[0.06] rounded-lg p-3 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between pb-1.5 mb-2 border-b border-white/[0.06]">
                    <span className="font-mono text-[10px] uppercase tracking-wider text-parchment-300">
                      Lemma
                    </span>
                    <span className="font-mono text-[10px] uppercase tracking-wider text-parchment-300">
                      φ<sub>k,w</sub>
                    </span>
                  </div>
                  <div className="space-y-1 max-h-[155px] overflow-y-auto pr-1 custom-scrollbar">
                    {filteredKeywords.map((kw, i) => (
                      <div
                        key={kw.word}
                        className="flex items-center justify-between text-[11px] py-0.5 px-1.5 rounded hover:bg-white/[0.03]"
                      >
                        <span className="font-mono text-parchment-100 truncate">
                          <span className="text-parchment-300/60 mr-1.5">{i + 1}.</span>
                          {kw.word}
                        </span>
                        <span
                          className="font-mono text-[10px] tabular-nums font-semibold"
                          style={{ color: currentTheme.hex }}
                        >
                          {kw.weight.toFixed(4)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Publisher concentration mini strip */}
                {currentTopic.top_publishers && Object.keys(currentTopic.top_publishers).length > 0 && (
                  <div className="pt-2.5 mt-2 border-t border-white/[0.06]">
                    <div className="flex items-center gap-1 mb-1.5">
                      <Building2 className="w-3 h-3 text-parchment-300" />
                      <span className="font-mono text-[9px] uppercase tracking-widest text-parchment-300">
                        Leading Imprints
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(currentTopic.top_publishers)
                        .slice(0, 3)
                        .map(([pub, count]) => (
                          <span
                            key={pub}
                            className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-obsidian-900 border border-white/[0.08] text-[10px] text-parchment-200"
                          >
                            <span className="truncate max-w-[95px]">{pub}</span>
                            <span className="font-mono text-[9px] text-traditional font-bold">
                              {count}
                            </span>
                          </span>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Optional Inline MARC21 Drawer ONLY if hideInlineInspector is false */}
            {!hideInlineInspector && currentTopic.representative_docs && (
              <div className="pt-3 border-t border-white/[0.07]">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-[10px] uppercase tracking-widest text-parchment-300 flex items-center gap-1.5">
                    <BookText className="w-3.5 h-3.5 text-traditional" />
                    Representative DNB MARC21 Monographs & APA 7th Citations
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                  {currentTopic.representative_docs.map((doc, idx) => {
                    const apaText = doc.apa_citation || `${doc.publisher}. (${doc.year}). ${doc.title}.`;
                    const isCopied = copiedCitation === apaText;
                    return (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-obsidian-950/90 border border-white/[0.07] flex flex-col justify-between gap-2"
                      >
                        <div>
                          <div className="flex items-center justify-between gap-2 mb-1">
                            <span className="font-mono text-[10px] text-traditional font-semibold">
                              {doc.publisher}
                            </span>
                            <span className="font-mono text-[10px] text-parchment-300">
                              {doc.year}
                            </span>
                          </div>
                          <h5 className="font-serif text-sm font-bold text-parchment-50 leading-snug">
                            {doc.title}
                          </h5>
                        </div>
                        <div className="flex items-center justify-between gap-2 pt-2 border-t border-white/[0.05]">
                          <p className="font-mono text-[10px] text-parchment-300 truncate">
                            <Quote className="w-2.5 h-2.5 inline mr-1 text-traditional" />
                            {apaText}
                          </p>
                          <button
                            onClick={() => handleCopyCitation(apaText)}
                            className="shrink-0 px-2 py-0.5 rounded bg-white/[0.05] hover:bg-white/[0.1] font-mono text-[10px] text-parchment-200 cursor-pointer"
                          >
                            {isCopied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
