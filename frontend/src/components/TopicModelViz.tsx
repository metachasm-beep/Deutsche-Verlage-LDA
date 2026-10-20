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
import { Layers, Info, Activity, Search, BookText, Quote, Copy, Check, Building2 } from 'lucide-react';
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

  const handleCopyCitation = (citation: string, idx: number) => {
    navigator.clipboard.writeText(citation);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  if (isTraining) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[550px] bg-midnight-950/20 backdrop-blur-xl rounded-2xl">
        <Activity className="animate-spin text-gold mb-6 opacity-80" size={64} />
        <p className="text-neutral-200 font-heading text-xl animate-pulse tracking-[0.1em] uppercase">Synthesizing Topic Clusters...</p>
        <p className="text-neutral-500 text-sm mt-2 font-light">Decomposing semantic vectors into latent dimensions</p>
      </div>
    );
  }

  if (!topics || topics.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[550px] text-neutral-500 space-y-4 bg-midnight-950/10 rounded-2xl border border-neutral-800/40">
        <Layers size={48} className="opacity-10" />
        <p className="font-heading text-lg tracking-wide uppercase text-neutral-600">No clusters detected</p>
        <p className="text-sm max-w-xs text-center opacity-70 font-light">
          Trigger the Neural Engine to generate topic models from the current corpus.
        </p>
      </div>
    );
  }

  const rawEvidenceList = representativeDocs[selectedTopic?.id ?? 0] || [];

  return (
    <div className="flex flex-col lg:flex-row h-full min-h-[550px] w-full bg-midnight-950/30 backdrop-blur-md rounded-2xl overflow-hidden border border-neutral-800/50 shadow-2xl shadow-black/40">
      
      {/* Sidebar: Topic Selection */}
      <div className="w-full lg:w-72 border-r border-neutral-800/50 bg-neutral-900/60 p-5 overflow-y-auto max-h-[280px] lg:max-h-none custom-scrollbar">
        <div className="flex items-center justify-between mb-6 px-1">
          <div className="flex items-center gap-3">
            <div className="w-2 h-6 bg-gold rounded-full" />
            <h3 className="text-xs font-heading font-black text-neutral-300 uppercase tracking-[0.2em]">Clusters (K={topics.length})</h3>
          </div>
        </div>
        
        <div className="space-y-3">
          {topics.map((topic) => {
            const isActive = selectedTopicId === topic.id || (selectedTopicId === null && topic.id === topics[0].id);
            return (
              <motion.button
                key={topic.id}
                whileHover={{ x: 6, backgroundColor: 'rgba(202, 138, 4, 0.08)' }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setSelectedTopicId(topic.id)}
                className={clsx(
                  "w-full text-left p-4 rounded-xl transition-all duration-500 border flex flex-col gap-2 group relative overflow-hidden",
                  isActive
                    ? "bg-gold/10 border-gold/40 shadow-[0_4px_15px_rgba(202,138,4,0.15)] ring-1 ring-gold/20"
                    : "bg-neutral-950/40 border-neutral-800/50 hover:border-neutral-600/50"
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="active-indicator"
                    className="absolute left-0 top-0 bottom-0 w-1 bg-gold shadow-[0_0_10px_#CA8A04]"
                  />
                )}
                
                <div className="flex justify-between items-center relative z-10">
                  <span className={clsx(
                    "text-[10px] font-black font-heading uppercase tracking-[0.15em]",
                    isActive ? "text-gold" : "text-neutral-500"
                  )}>
                    Pattern {topic.id + 1}
                  </span>
                  <span className="text-[10px] font-bold text-neutral-100 bg-neutral-800/80 backdrop-blur-sm px-2 py-0.5 rounded-full border border-neutral-700/50">
                    {topic.prevalence}%
                  </span>
                </div>

                {topic.archetype?.label && (
                  <div className="text-[9px] uppercase tracking-wider font-semibold text-gold/80 truncate">
                    {topic.archetype.label}
                  </div>
                )}

                <div className="text-[11px] text-neutral-400 truncate font-medium group-hover:text-neutral-200 transition-colors">
                  {topic.keywords.slice(0, 3).map(k => k.word).join(' · ')}
                </div>
              </motion.button>
            );
          })}
        </div>
      </div>

      {/* Main Content: Keyword Distribution, Publisher Dominance & Evidence */}
      <div className="flex-grow p-8 flex flex-col bg-gradient-to-br from-midnight-950/40 to-neutral-950/40 relative overflow-y-auto custom-scrollbar">
        <AnimatePresence mode="wait">
          <motion.div
            key={selectedTopic?.id ?? 'none'}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="flex-grow flex flex-col h-full"
          >
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 mb-6 pb-6 border-b border-neutral-800/40">
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="text-3xl lg:text-4xl font-heading font-light text-neutral-50 tracking-tight">
                    Discursive Pattern <span className="text-gold font-bold">#{selectedTopic ? selectedTopic.id + 1 : '?'}</span>
                  </h2>

                  {selectedTopic?.archetype && (
                    <div className="px-3 py-1 bg-gold/10 border border-gold/30 rounded-full text-[10px] font-black text-gold uppercase tracking-widest">
                      {selectedTopic.archetype.label} ({selectedTopic.archetype.confidence}%)
                    </div>
                  )}

                  <div className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
                    <Activity size={12} className="text-emerald-400" />
                    <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">
                      U_Mass: {coherenceScore.toFixed(2)} {cvCoherence !== null ? `| C_v: ${cvCoherence.toFixed(3)}` : ''}
                    </span>
                  </div>

                  {(selectedYear || selectedDecade) && (
                    <div className="text-[10px] text-neutral-400 font-bold tracking-[0.2em] uppercase border-l border-neutral-800 pl-3">
                      Slice: {selectedYear ? `Year ${selectedYear}` : `${selectedDecade}s`}
                    </div>
                  )}
                </div>
                
                <div className="relative max-w-sm group">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500 group-focus-within:text-gold transition-colors" size={14} />
                  <input
                    type="text"
                    placeholder="Filter German lemmas & bigrams..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full bg-neutral-900/50 border border-neutral-800 rounded-xl py-2 pl-9 pr-4 text-xs text-neutral-200 focus:outline-none focus:ring-1 focus:ring-gold/50 transition-all placeholder:text-neutral-600"
                  />
                </div>
              </div>

              <div className="flex items-center gap-6 bg-black/30 backdrop-blur-xl p-4 rounded-2xl border border-neutral-800/80 shadow-2xl">
                <div className="flex flex-col items-center px-2">
                  <span className="text-[10px] text-neutral-500 uppercase font-black tracking-widest mb-1">Prevalence</span>
                  <span className="text-xl text-neutral-100 font-black tabular-nums">{selectedTopic?.prevalence}%</span>
                </div>
                <div className="w-[1px] h-10 bg-neutral-800/80" />
                <div className="flex flex-col items-center px-2">
                  <span className="text-[10px] text-neutral-500 uppercase font-black tracking-widest mb-1">Top Lemmas</span>
                  <span className="text-xl text-neutral-100 font-black tabular-nums">{selectedTopic?.keywords.length}</span>
                </div>
              </div>
            </div>

            {/* Institutional Publisher Dominance Strip */}
            {selectedTopic?.publishers && selectedTopic.publishers.length > 0 && (
              <div className="mb-6 p-4 rounded-xl bg-neutral-900/40 border border-neutral-800/60">
                <div className="flex items-center gap-2 mb-3">
                  <Building2 size={14} className="text-gold" />
                  <span className="text-[10px] font-black uppercase tracking-[0.2em] text-neutral-300">
                    Institutional Publisher Dominance (Topic Share)
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                  {selectedTopic.publishers.map((p, idx) => (
                    <div key={idx} className="bg-neutral-950/60 border border-neutral-800/80 rounded-lg p-2.5 flex flex-col">
                      <span className="text-[10px] text-neutral-400 truncate font-medium">{p.publisher}</span>
                      <div className="flex items-baseline justify-between mt-1">
                        <span className="text-xs font-bold text-gold">{p.share}%</span>
                        <div className="w-12 h-1.5 bg-neutral-800 rounded-full overflow-hidden">
                          <div className="h-full bg-gold rounded-full" style={{ width: `${Math.min(100, p.share)}%` }} />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex-grow w-full min-h-[340px] relative px-2 mb-8">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={(selectedTopic?.keywords || []).filter(k => k.word.toLowerCase().includes(searchTerm.toLowerCase()))}
                  margin={{ top: 0, right: 40, left: 30, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#1e293b" />
                  <XAxis type="number" hide domain={[0, 'dataMax']} />
                  <YAxis
                    dataKey="word"
                    type="category"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#CBD5E1', fontSize: 12, fontWeight: 500, fontFamily: 'var(--font-heading)' }}
                    width={120}
                  />
                  <Tooltip
                    cursor={{ fill: 'rgba(255, 255, 255, 0.03)' }}
                    contentStyle={{
                      backgroundColor: 'rgba(15, 23, 42, 0.95)',
                      borderRadius: '16px',
                      border: '1px solid rgba(202, 138, 4, 0.3)',
                      backdropFilter: 'blur(12px)',
                      padding: '12px'
                    }}
                    labelStyle={{ color: '#F8FAFC', fontWeight: 'bold' }}
                    itemStyle={{ color: '#F59E0B' }}
                    formatter={(value: any) => [`${(Number(value) * 100).toFixed(2)}%`, 'Posterior Weight (φ)']}
                  />
                  <Bar
                    dataKey="weight"
                    radius={[0, 6, 6, 0]}
                    barSize={22}
                    animationDuration={1200}
                  >
                    {selectedTopic?.keywords.map((_, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={index === 0 ? '#F59E0B' : '#D97706'}
                        fillOpacity={Math.max(0.25, 1 - index * 0.05)}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Representative MARC21 Evidence Layer with APA Citations */}
            <div className="space-y-6">
              <div className="flex items-center gap-4">
                <div className="h-px flex-1 bg-white/5"></div>
                <div className="flex items-center gap-2 text-gold/80">
                  <BookText size={14} />
                  <h3 className="text-[10px] font-black uppercase tracking-[0.3em] italic">
                    Primary MARC21 Evidence & APA 7th Citations
                  </h3>
                </div>
                <div className="h-px flex-1 bg-white/5"></div>
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
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 * idx }}
                        className="p-5 rounded-2xl bg-neutral-950/60 border border-neutral-800/70 hover:border-gold/40 transition-all duration-500 flex flex-col justify-between gap-3 relative group"
                      >
                        <div>
                          <div className="flex items-center justify-between gap-2 mb-2">
                            <span className="text-[9px] font-black uppercase tracking-widest text-gold bg-gold/10 px-2 py-0.5 rounded border border-gold/20">
                              {docObj.publisher || `Evidence 0${idx + 1}`} {docObj.date ? `(${docObj.date})` : ''}
                            </span>
                            {docObj.probability !== undefined && (
                              <span className="text-[9px] font-bold text-emerald-400">
                                θ = {docObj.probability}%
                              </span>
                            )}
                          </div>

                          {docObj.title && (
                            <h4 className="text-xs font-bold text-neutral-100 mb-1 line-clamp-2 leading-snug">
                              {docObj.title}
                            </h4>
                          )}
                          {docObj.author && (
                            <p className="text-[10px] text-neutral-400 mb-2 font-medium">
                              {docObj.author}
                            </p>
                          )}

                          <p className="text-[11px] text-neutral-400 leading-relaxed font-light line-clamp-4 italic">
                            "{docObj.snippet}"
                          </p>
                        </div>

                        <div className="pt-3 border-t border-neutral-800/60 space-y-2">
                          {docObj.keywords && docObj.keywords.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {docObj.keywords.slice(0, 3).map((kw, kIdx) => (
                                <span key={kIdx} className="text-[9px] bg-neutral-900 text-neutral-400 px-1.5 py-0.5 rounded border border-neutral-800">
                                  {kw}
                                </span>
                              ))}
                            </div>
                          )}

                          {docObj.apa_citation && (
                            <button
                              onClick={() => handleCopyCitation(docObj.apa_citation!, idx)}
                              className="w-full flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg bg-neutral-900 hover:bg-gold/20 border border-neutral-800 hover:border-gold/40 text-[10px] text-neutral-300 hover:text-gold transition-colors font-semibold"
                              title={docObj.apa_citation}
                            >
                              {copiedIndex === idx ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                              {copiedIndex === idx ? 'APA Citation Copied' : 'Copy APA 7th Citation'}
                            </button>
                          )}
                        </div>
                      </motion.div>
                    );
                  })
                ) : (
                  <div className="col-span-3 py-10 flex flex-col items-center justify-center opacity-30 border border-dashed border-neutral-800 rounded-2xl">
                    <Quote size={24} className="mb-2" />
                    <span className="text-[10px] font-bold uppercase tracking-widest">No matching evidence extracted</span>
                  </div>
                )}
              </div>

              <div className="mt-4 p-5 rounded-2xl bg-neutral-900/60 border border-neutral-800/80 flex gap-4 items-start shadow-xl">
                <div className="p-2 bg-gold/10 rounded-lg text-gold mt-1">
                  <Info size={18} />
                </div>
                <div className="space-y-1">
                  <h4 className="text-xs font-bold text-neutral-300 uppercase tracking-widest">
                    Critical Theory & Discursive Mediation Diagnostics
                  </h4>
                  <p className="text-[12px] text-neutral-400 leading-relaxed font-light">
                    Dominant lemma <strong className="text-gold font-bold uppercase tracking-tight">"{selectedTopic?.keywords[0]?.word}"</strong> anchors this cluster within the{' '}
                    <span className="text-neutral-200 font-medium">{selectedTopic?.archetype?.label || 'Discursive'}</span> archetype. Cross-referencing publisher shares above with the MARC21 *Inhaltstext* blurbs quantifies how institutional imprints mediate faith and market rationality.
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
