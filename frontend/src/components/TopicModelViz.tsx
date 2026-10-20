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
import { Layers, Activity, Search, BookText, Quote, Copy, Check, Building2, Sparkles } from 'lucide-react';
import clsx from 'clsx';

interface Keyword {
  word: string;
  weight: number;
}

interface ArchetypeInfo {
  label: string;
  confidence: number;
  scores?: Record<string, number>;
}

interface PublisherShare {
  publisher: string;
  share: number;
}

interface Topic {
  id: number;
  prevalence: number;
  archetype?: ArchetypeInfo;
  publishers?: PublisherShare[];
  keywords: Keyword[];
}

interface StructuredEvidence {
  title?: string;
  author?: string;
  publisher?: string;
  date?: string;
  probability?: number;
  keywords?: string[];
  snippet?: string;
  apa_citation?: string;
}

interface TopicModelVizProps {
  topics: Topic[];
  isTraining: boolean;
  selectedYear?: number | null;
  selectedDecade?: number | null;
  coherenceScore?: number;
  cvCoherence?: number | null;
  representativeDocs?: Record<number, Array<string | StructuredEvidence>>;
}

function getArchetypeTheme(label?: string) {
  if (!label) {
    return {
      primaryHex: '#D4AF37',
      secondaryHex: '#A16207',
      badgeClass: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
      dotClass: 'bg-yellow-400',
      shortLabel: 'Discursive'
    };
  }
  if (label.includes('Neoliberal')) {
    return {
      primaryHex: '#38BDF8',
      secondaryHex: '#0284C7',
      badgeClass: 'bg-sky-500/10 text-sky-400 border-sky-400/30',
      dotClass: 'bg-sky-400',
      shortLabel: 'Neoliberal / Market'
    };
  }
  if (label.includes('Critical')) {
    return {
      primaryHex: '#FB7185',
      secondaryHex: '#E11D48',
      badgeClass: 'bg-rose-500/10 text-rose-400 border-rose-400/30',
      dotClass: 'bg-rose-400',
      shortLabel: 'Critical / Secular'
    };
  }
  return {
    primaryHex: '#EAB308',
    secondaryHex: '#CA8A04',
    badgeClass: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
    dotClass: 'bg-yellow-400',
    shortLabel: 'Traditional / Ecclesia'
  };
}

const TopicModelViz: React.FC<TopicModelVizProps> = ({
  topics,
  isTraining,
  selectedYear,
  selectedDecade,
  coherenceScore = 0,
  cvCoherence = null,
  representativeDocs = {}
}) => {
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const selectedTopic = topics.find(t => t.id === selectedTopicId) || topics[0];
  const activeTheme = getArchetypeTheme(selectedTopic?.archetype?.label);

  const handleCopyCitation = (citation: string, idx: number) => {
    navigator.clipboard.writeText(citation);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  if (isTraining) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[560px] bg-midnight-900/60 backdrop-blur-xl rounded-2xl border border-white/10">
        <Activity className="animate-spin text-gold mb-6 opacity-90" size={56} />
        <p className="text-neutral-100 font-heading text-2xl italic tracking-wide">
          Estimating Variational Dirichlet Posteriors...
        </p>
        <p className="text-neutral-500 font-mono text-xs mt-2 uppercase tracking-widest">
          spaCy de_core_news_lg · Online Variational Bayes
        </p>
      </div>
    );
  }

  if (!topics || topics.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[560px] text-neutral-500 space-y-4 bg-midnight-900/40 rounded-2xl border border-white/[0.07]">
        <Layers size={48} className="opacity-20 text-gold" />
        <p className="font-heading text-2xl italic text-neutral-400">No Latent Clusters Initialized</p>
        <p className="text-xs font-mono uppercase tracking-widest text-neutral-600">
          Execute the Neural Engine to decompose the German publishing corpus
        </p>
      </div>
    );
  }

  const rawEvidenceList = representativeDocs[selectedTopic?.id ?? 0] || [];
  const archScores = selectedTopic?.archetype?.scores || {};
  const tradPct = archScores['Traditional / Ecclesiastical'] ?? 33.3;
  const neolibPct = archScores['Neoliberal / Self-Optimization'] ?? 33.3;
  const critPct = archScores['Critical / Secular-Humanist'] ?? 33.4;

  return (
    <div className="flex flex-col lg:flex-row h-full min-h-[620px] w-full bg-midnight-900/80 backdrop-blur-xl rounded-2xl overflow-hidden border border-white/[0.08] shadow-2xl">
      
      {/* Left Folio Index: Topic Cluster Selector */}
      <div className="w-full lg:w-80 border-b lg:border-b-0 lg:border-r border-white/[0.08] bg-midnight-950/60 p-5 overflow-y-auto max-h-[300px] lg:max-h-[780px] custom-scrollbar">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-2.5">
            <span className="w-1.5 h-4 bg-gold rounded-sm" />
            <h3 className="text-[11px] font-mono font-semibold text-neutral-300 uppercase tracking-[0.2em]">
              Latent Folio Index
            </h3>
          </div>
          <span className="text-[10px] font-mono text-gold bg-gold/10 px-2 py-0.5 rounded border border-gold/25">
            K = {topics.length}
          </span>
        </div>

        <div className="space-y-2.5">
          {topics.map((topic) => {
            const isActive = selectedTopicId === topic.id || (selectedTopicId === null && topic.id === topics[0].id);
            const tTheme = getArchetypeTheme(topic.archetype?.label);
            return (
              <motion.button
                key={topic.id}
                whileHover={{ x: 4 }}
                whileTap={{ scale: 0.99 }}
                onClick={() => setSelectedTopicId(topic.id)}
                className={clsx(
                  "cursor-pointer w-full text-left p-3.5 rounded-xl transition-all duration-200 border flex flex-col gap-2 group relative overflow-hidden",
                  isActive
                    ? "bg-white/[0.05] border-gold/50 shadow-lg"
                    : "bg-midnight-900/40 border-white/[0.05] hover:border-white/15 hover:bg-white/[0.02]"
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="active-cluster-bar"
                    className="absolute left-0 top-0 bottom-0 w-1"
                    style={{ backgroundColor: tTheme.primaryHex }}
                  />
                )}

                <div className="flex justify-between items-center relative z-10">
                  <div className="flex items-center gap-2">
                    <span className={clsx("w-2 h-2 rounded-full", tTheme.dotClass)} />
                    <span className={clsx(
                      "text-[11px] font-mono font-bold uppercase tracking-wider",
                      isActive ? "text-white" : "text-neutral-400"
                    )}>
                      Cluster {String(topic.id + 1).padStart(2, '0')}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono font-semibold text-neutral-200 bg-black/50 px-2 py-0.5 rounded border border-white/10">
                    {topic.prevalence}%
                  </span>
                </div>

                <div className="flex items-center justify-between gap-2">
                  <span className={clsx("text-[9px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded border", tTheme.badgeClass)}>
                    {tTheme.shortLabel}
                  </span>
                  {topic.publishers?.[0] && (
                    <span className="text-[9px] font-mono text-neutral-500 truncate">
                      {topic.publishers[0].publisher} ({topic.publishers[0].share}%)
                    </span>
                  )}
                </div>

                <div className="text-xs text-neutral-300 truncate font-body group-hover:text-white transition-colors">
                  {topic.keywords.slice(0, 4).map(k => k.word).join(' · ')}
                </div>
              </motion.button>
            );
          })}
        </div>
      </div>

      {/* Right Analytical Folio: Posterior Distribution, Tri-Archetype Split & MARC21 Evidence */}
      <div className="flex-grow p-6 lg:p-8 flex flex-col bg-gradient-to-br from-midnight-900/60 via-midnight-950/80 to-midnight-950 relative overflow-y-auto custom-scrollbar">
        <AnimatePresence mode="wait">
          <motion.div
            key={selectedTopic?.id ?? 'none'}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.25 }}
            className="flex-grow flex flex-col"
          >
            {/* Folio Header */}
            <div className="flex flex-col xl:flex-row xl:items-start justify-between gap-6 mb-6 pb-6 border-b border-white/[0.08]">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-[10px] font-mono uppercase tracking-[0.25em] text-neutral-500">
                    LATENT DISCOURSE VECTOR //
                  </span>
                  {selectedTopic?.archetype && (
                    <span className={clsx("px-2.5 py-0.5 rounded-md text-[10px] font-mono font-bold uppercase tracking-widest border", activeTheme.badgeClass)}>
                      {selectedTopic.archetype.label} · {selectedTopic.archetype.confidence}%
                    </span>
                  )}
                  {(selectedYear || selectedDecade) && (
                    <span className="px-2.5 py-0.5 rounded-md bg-gold/15 border border-gold/40 text-[10px] font-mono font-bold text-gold uppercase tracking-widest">
                      Temporal Slice: {selectedYear ? `Year ${selectedYear}` : `${selectedDecade}s`}
                    </span>
                  )}
                </div>

                <h2 className="text-3xl lg:text-4xl font-heading font-semibold italic text-white tracking-tight">
                  Discursive Cluster #{selectedTopic ? String(selectedTopic.id + 1).padStart(2, '0') : '01'}:{' '}
                  <span style={{ color: activeTheme.primaryHex }}>
                    {selectedTopic?.keywords.slice(0, 3).map(k => k.word).join(', ')}
                  </span>
                </h2>

                {/* 3-Way Ideological Archetype Spectrum Bar */}
                <div className="pt-1 max-w-xl space-y-1.5">
                  <div className="flex justify-between text-[10px] font-mono">
                    <span className="text-yellow-400">Traditional: {tradPct}%</span>
                    <span className="text-sky-400">Neoliberal: {neolibPct}%</span>
                    <span className="text-rose-400">Critical: {critPct}%</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-neutral-900 overflow-hidden flex border border-white/10">
                    <div style={{ width: `${tradPct}%` }} className="bg-yellow-500 h-full transition-all duration-500" title={`Traditional: ${tradPct}%`} />
                    <div style={{ width: `${neolibPct}%` }} className="bg-sky-400 h-full transition-all duration-500" title={`Neoliberal: ${neolibPct}%`} />
                    <div style={{ width: `${critPct}%` }} className="bg-rose-500 h-full transition-all duration-500" title={`Critical: ${critPct}%`} />
                  </div>
                </div>
              </div>

              {/* Filter & Telemetry Box */}
              <div className="flex flex-col sm:flex-row xl:flex-col gap-3 shrink-0">
                <div className="flex items-center gap-4 bg-midnight-950/90 px-4 py-3 rounded-xl border border-white/[0.08]">
                  <div>
                    <div className="text-[9px] font-mono uppercase tracking-widest text-neutral-500">Corpus Share</div>
                    <div className="text-lg font-mono font-bold text-white">{selectedTopic?.prevalence}%</div>
                  </div>
                  <div className="w-px h-8 bg-white/10" />
                  <div>
                    <div className="text-[9px] font-mono uppercase tracking-widest text-neutral-500">U_Mass</div>
                    <div className="text-lg font-mono font-bold text-emerald-400">{coherenceScore.toFixed(2)}</div>
                  </div>
                  {cvCoherence !== null && (
                    <>
                      <div className="w-px h-8 bg-white/10" />
                      <div>
                        <div className="text-[9px] font-mono uppercase tracking-widest text-neutral-500">C_v NPMI</div>
                        <div className="text-lg font-mono font-bold text-gold">{cvCoherence.toFixed(3)}</div>
                      </div>
                    </>
                  )}
                </div>

                <div className="relative group">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500 group-focus-within:text-gold transition-colors" size={14} />
                  <input
                    type="text"
                    aria-label="Filter German lemmas and bigrams"
                    placeholder="Filter German lemmas..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full bg-midnight-950/90 border border-white/10 rounded-xl py-2 pl-9 pr-4 text-xs font-mono text-neutral-200 focus:outline-none focus:border-gold/60 transition-all placeholder:text-neutral-600"
                  />
                </div>
              </div>
            </div>

            {/* Institutional Publisher Dominance Strip */}
            {selectedTopic?.publishers && selectedTopic.publishers.length > 0 && (
              <div className="mb-6 p-4 rounded-xl bg-midnight-950/60 border border-white/[0.07]">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Building2 size={14} className="text-gold" />
                    <span className="text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-neutral-300">
                      Institutional Imprint Concentration (DNB Publisher Share)
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-neutral-500">Posterior θ Aggregation</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
                  {selectedTopic.publishers.map((p, idx) => (
                    <div key={idx} className="bg-midnight-900/90 border border-white/[0.06] rounded-lg p-2.5 flex flex-col justify-between">
                      <span className="text-[11px] text-neutral-300 truncate font-medium">{p.publisher}</span>
                      <div className="flex items-center justify-between gap-2 mt-1.5">
                        <span className="text-xs font-mono font-bold" style={{ color: activeTheme.primaryHex }}>
                          {p.share}%
                        </span>
                        <div className="flex-1 h-1.5 bg-neutral-800 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{ width: `${Math.min(100, p.share)}%`, backgroundColor: activeTheme.primaryHex }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Posterior Word-Topic Distribution Chart (φ_k) */}
            <div className="w-full h-[320px] relative px-1 mb-8">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={(selectedTopic?.keywords || []).filter(k => k.word.toLowerCase().includes(searchTerm.toLowerCase()))}
                  margin={{ top: 0, right: 32, left: 24, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="rgba(255,255,255,0.05)" />
                  <XAxis type="number" hide domain={[0, 'dataMax']} />
                  <YAxis
                    dataKey="word"
                    type="category"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#E2E8F0', fontSize: 12, fontWeight: 500, fontFamily: 'var(--font-mono)' }}
                    width={135}
                  />
                  <Tooltip
                    cursor={{ fill: 'rgba(255, 255, 255, 0.03)' }}
                    contentStyle={{
                      backgroundColor: 'rgba(7, 7, 9, 0.96)',
                      borderRadius: '12px',
                      border: `1px solid ${activeTheme.primaryHex}`,
                      backdropFilter: 'blur(12px)',
                      padding: '10px 14px',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '11px'
                    }}
                    labelStyle={{ color: '#F8FAFC', fontWeight: 'bold' }}
                    itemStyle={{ color: activeTheme.primaryHex }}
                    formatter={(value: any) => [`${(Number(value) * 100).toFixed(2)}%`, 'Posterior φ(w|z)']}
                  />
                  <Bar
                    dataKey="weight"
                    radius={[0, 5, 5, 0]}
                    barSize={18}
                    animationDuration={800}
                  >
                    {selectedTopic?.keywords.map((_, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={index === 0 ? activeTheme.primaryHex : activeTheme.secondaryHex}
                        fillOpacity={Math.max(0.3, 1 - index * 0.045)}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Primary MARC21 Paratextual Evidence & APA 7th Citations */}
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-white/[0.07] pb-2.5">
                <div className="flex items-center gap-2 text-gold">
                  <BookText size={15} />
                  <h3 className="text-[11px] font-mono font-bold uppercase tracking-[0.2em]">
                    Primary MARC21 Paratextual Evidence (Tag 245 · 650 · 856 Inhaltstext)
                  </h3>
                </div>
                <span className="text-[10px] font-mono text-neutral-500">Sorted by Posterior θ(z|d)</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {rawEvidenceList.length > 0 ? (
                  rawEvidenceList.map((item, idx) => {
                    const isObj = typeof item === 'object' && item !== null;
                    const docObj: StructuredEvidence = isObj
                      ? (item as StructuredEvidence)
                      : { snippet: String(item) };

                    return (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.06 * idx }}
                        className="p-5 rounded-xl bg-midnight-950/90 border border-white/[0.08] hover:border-gold/40 transition-all duration-200 flex flex-col justify-between gap-4 relative group"
                      >
                        <div>
                          <div className="flex items-center justify-between gap-2 mb-2.5">
                            <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-gold bg-gold/10 px-2 py-0.5 rounded border border-gold/25 truncate">
                              {docObj.publisher || `Record 0${idx + 1}`} {docObj.date ? `· ${docObj.date}` : ''}
                            </span>
                            {docObj.probability !== undefined && (
                              <span className="text-[10px] font-mono font-bold text-emerald-400 shrink-0">
                                θ = {docObj.probability}%
                              </span>
                            )}
                          </div>

                          {docObj.title && (
                            <h4 className="text-sm font-heading font-semibold text-white mb-1 line-clamp-2 leading-snug">
                              {docObj.title}
                            </h4>
                          )}
                          {docObj.author && (
                            <p className="text-[11px] font-mono text-neutral-400 mb-2.5">
                              {docObj.author}
                            </p>
                          )}

                          <p className="text-xs text-neutral-300 leading-relaxed font-light line-clamp-5 italic">
                            "{docObj.snippet}"
                          </p>
                        </div>

                        <div className="pt-3 border-t border-white/[0.06] space-y-2.5">
                          {docObj.keywords && docObj.keywords.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {docObj.keywords.slice(0, 4).map((kw, kIdx) => (
                                <span
                                  key={kIdx}
                                  className="text-[9px] font-mono bg-midnight-900 text-neutral-400 px-1.5 py-0.5 rounded border border-white/[0.06]"
                                >
                                  {kw}
                                </span>
                              ))}
                            </div>
                          )}

                          {docObj.apa_citation && (
                            <button
                              onClick={() => handleCopyCitation(docObj.apa_citation!, idx)}
                              className="cursor-pointer w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-white/[0.04] hover:bg-gold hover:text-midnight-950 border border-white/10 hover:border-gold text-[10px] font-mono font-semibold text-neutral-200 transition-all duration-200"
                              title={docObj.apa_citation}
                            >
                              {copiedIndex === idx ? <Check size={12} /> : <Copy size={12} />}
                              {copiedIndex === idx ? 'APA 7th Citation Copied!' : 'Copy APA 7th Citation'}
                            </button>
                          )}
                        </div>
                      </motion.div>
                    );
                  })
                ) : (
                  <div className="col-span-3 py-10 flex flex-col items-center justify-center opacity-40 border border-dashed border-neutral-800 rounded-xl">
                    <Quote size={24} className="mb-2" />
                    <span className="text-xs font-mono uppercase tracking-widest">No matching MARC21 records</span>
                  </div>
                )}
              </div>

              {/* Hermeneutic Interpretation Callout */}
              <div className="mt-4 p-4 rounded-xl bg-midnight-950/80 border border-white/[0.08] flex gap-3.5 items-start">
                <div className="p-2 bg-gold/10 rounded-lg text-gold shrink-0 mt-0.5">
                  <Sparkles size={16} />
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h4 className="text-[11px] font-mono font-bold text-neutral-200 uppercase tracking-widest">
                      Hermeneutic Synthesis · Critical Theory Triangulation
                    </h4>
                  </div>
                  <p className="text-xs text-neutral-400 leading-relaxed font-light">
                    Anchored by primary signifier <strong className="text-white font-mono">"{selectedTopic?.keywords[0]?.word}"</strong>, this cluster exhibits a{' '}
                    <strong style={{ color: activeTheme.primaryHex }}>{selectedTopic?.archetype?.confidence ?? 33.3}%</strong> lexical affinity with the{' '}
                    <span className="text-neutral-200 font-medium">{selectedTopic?.archetype?.label || 'Hybrid'}</span> voice. Use the APA 7th citations above to integrate the highest-probability DNB monographs directly into your dissertation analysis.
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};

export default TopicModelViz;
