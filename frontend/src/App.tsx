import { useEffect, useState, useRef, useMemo } from 'react';
import { motion } from 'framer-motion';
import type { Variants } from 'framer-motion';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import ShinyText from './components/ShinyText';
import SpotlightCard from './components/SpotlightCard';
import TrendsGraph from './components/TrendsGraph';
import Particles from './components/Particles';
import BlurText from './components/BlurText';
import { useLDA } from './hooks/useLDA';
import {
  Database,
  Cpu,
  BarChart3,
  Loader2,
  Upload,
  RotateCcw,
  BookOpen,
  Sliders,
  Layers,
  Building2,
  Activity,
  Download,
  Compass,
  Sparkles
} from 'lucide-react';
import TopicModelViz from './components/TopicModelViz';
import clsx from 'clsx';

type WorkbenchTab = 'clusters' | 'matrix' | 'diachronic';

function App() {
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [selectedDecade, setSelectedDecade] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<WorkbenchTab>('clusters');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    isTraining,
    isUploading,
    trendsData,
    summary,
    topics,
    numTopics,
    setNumTopics,
    vocabSize,
    coherenceScore,
    cvCoherence,
    coherenceGrid,
    recommendedRegimes,
    publisherArchetypes,
    representativeDocs,
    fetchTrends,
    fetchSummary,
    fetchTopics,
    fetchCoherenceGrid,
    runLDA,
    uploadDataset,
    resetToMock
  } = useLDA();

  useEffect(() => {
    fetchTrends();
    fetchSummary();
    fetchTopics();
    fetchCoherenceGrid();
  }, []);

  // Compute dominant ideological archetype across active topics
  const dominantArchetype = useMemo(() => {
    if (!topics || topics.length === 0) {
      return { label: 'Initializing...', share: 0 };
    }
    const tally: Record<string, number> = {};
    for (const t of topics) {
      const arch = t.archetype?.label || 'Hybrid / Discursive';
      tally[arch] = (tally[arch] || 0) + (Number(t.prevalence) || 0);
    }
    let bestLabel = 'Hybrid / Discursive';
    let bestVal = 0;
    for (const [k, v] of Object.entries(tally)) {
      if (v > bestVal) {
        bestVal = v;
        bestLabel = k;
      }
    }
    return { label: bestLabel, share: Math.round(bestVal * 10) / 10 };
  }, [topics]);

  const handleYearSelect = async (year: number) => {
    setSelectedYear(year);
    setSelectedDecade(null);
    await runLDA(year, null, numTopics);
  };

  const handleDecadeSelect = async (decade: number) => {
    setSelectedDecade(decade);
    setSelectedYear(null);
    await runLDA(null, decade, numTopics);
  };

  const handleRegimeSelect = async (k: number) => {
    setNumTopics(k);
    await runLDA(selectedYear, selectedDecade, k);
  };

  const handleFullAnalysis = async () => {
    setSelectedYear(null);
    setSelectedDecade(null);
    await runLDA(null, null, numTopics);
  };

  const handleExport = () => {
    const report = {
      researchTitle: "Mediating Faith and Power: German Publishing LDA",
      author: "Paul Marandi, Ph.D. Scholar, CGS, SLL&CS, JNU",
      generatedAt: new Date().toISOString(),
      corpusSummary: summary,
      vocabSize,
      numTopics,
      modelCoherenceUMass: coherenceScore,
      modelCoherenceCv: cvCoherence,
      coherenceGrid,
      publisherArchetypes,
      topics,
      representativeEvidence: representativeDocs,
      temporalContext: { selectedYear, selectedDecade }
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `LDA_Dissertation_Dossier_K${numTopics}_${new Date().getTime()}.json`;
    a.click();
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      await uploadDataset(file);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.1
      }
    }
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: 18 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] }
    }
  };

  const defaultRegimes = recommendedRegimes.length > 0 ? recommendedRegimes : [
    { k: 4, label: "Macro (K=4)", description: "Optimal U_Mass Archetypes" },
    { k: 12, label: "Meso (K=12)", description: "Sub-disciplinary Inflection" },
    { k: 20, label: "High-Res (K=20)", description: "Thematic Differentiation" },
    { k: 30, label: "Micro (K=30)", description: "Global C_v NPMI Peak" }
  ];

  return (
    <div className="relative min-h-screen bg-midnight-950 archival-grid-bg font-body text-neutral-300 overflow-x-hidden">
      
      {/* Ambient WebGL Particle Constellation */}
      <div className="fixed inset-0 z-0 pointer-events-none opacity-55">
        <Particles
          particleColors={['#D4AF37', '#38BDF8', '#FB7185', '#A16207']}
          particleCount={220}
          particleSpread={16}
          speed={0.12}
          particleBaseSize={70}
          moveParticlesOnHover={true}
          alphaParticles={true}
          disableRotation={false}
          cameraDistance={32}
        />
      </div>

      {/* Floating Archival Masthead Bar (Compliant with UI/UX Pro Max spacing) */}
      <header className="fixed top-4 left-4 right-4 z-50 max-w-7xl mx-auto">
        <nav className="bg-midnight-900/85 backdrop-blur-2xl border border-white/10 rounded-2xl px-5 py-3 flex flex-wrap justify-between items-center gap-4 shadow-2xl">
          <div className="flex items-center gap-3.5">
            <div className="w-9 h-9 bg-gold/10 border border-gold/40 rounded-xl flex items-center justify-center">
              <Compass className="text-gold" size={18} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-gold">
                  EDITION CGS · JNU
                </span>
                <span className="text-neutral-700">|</span>
                <span className="text-[10px] font-mono uppercase tracking-widest text-neutral-400">
                  Paul Marandi, Ph.D.
                </span>
              </div>
              <h1 className="text-base font-heading font-bold italic text-white tracking-tight">
                Mediating Faith &amp; Power · Computational Hermeneutics Observatory
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <input
              type="file"
              accept=".csv"
              ref={fileInputRef}
              className="hidden"
              onChange={handleFileUpload}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="cursor-pointer px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-gold/15 border border-white/10 hover:border-gold/40 text-[11px] font-mono font-semibold text-neutral-200 hover:text-gold transition-all duration-200 flex items-center gap-1.5 disabled:opacity-50"
            >
              {isUploading ? <Loader2 size={13} className="animate-spin" /> : <Upload size={13} />}
              <span className="hidden sm:inline">Ingest CSV</span>
            </button>

            <button
              onClick={handleExport}
              disabled={!topics.length}
              className="cursor-pointer px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-emerald-500/15 border border-white/10 hover:border-emerald-500/40 text-[11px] font-mono font-semibold text-neutral-200 hover:text-emerald-400 transition-all duration-200 flex items-center gap-1.5 disabled:opacity-30"
            >
              <Download size={13} />
              <span className="hidden sm:inline">Export Dossier</span>
            </button>

            <div className="px-3 py-1.5 rounded-lg bg-midnight-950 border border-white/10 flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${isTraining ? 'bg-gold animate-pulse' : 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]'}`} />
              <span className="text-[10px] font-mono font-bold text-neutral-300 uppercase tracking-wider">
                {isTraining ? 'Inference Active' : `K=${numTopics} Ready`}
              </span>
            </div>
          </div>
        </nav>
      </header>

      <div className="relative z-10 w-full px-4 sm:px-8 lg:px-12 pt-28 pb-12 min-h-screen flex flex-col justify-between">
        <motion.main
          className="max-w-7xl mx-auto w-full space-y-8"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {/* Suhrkamp Editorial Monograph Banner */}
          <motion.section
            variants={itemVariants}
            className="relative rounded-2xl bg-gradient-to-r from-midnight-900/95 via-midnight-900/80 to-midnight-950/90 border border-white/[0.08] p-6 lg:p-8 overflow-hidden shadow-2xl"
          >
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-yellow-500 via-sky-400 to-rose-500 opacity-85" />
            <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
              <div className="space-y-2 max-w-3xl">
                <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono uppercase tracking-[0.25em] text-gold">
                  <span>BAND I · DISKURSANALYSE DEUTSCHER VERLAGE</span>
                  <span>//</span>
                  <span className="text-neutral-400">DNB SRU MARC21 · DDC 200/230</span>
                </div>
                <h2 className="text-3xl sm:text-5xl font-heading font-bold italic text-white tracking-tight leading-none">
                  <ShinyText text="Voices on Religion & the Neoliberal Moral Order" speed={4} />
                </h2>
                <p className="text-sm sm:text-base text-neutral-400 font-light leading-relaxed pt-1">
                  Mapping the dialectical tension between <span className="text-yellow-400 font-medium">Ecclesiastical Tradition</span>,{' '}
                  <span className="text-sky-400 font-medium">Neoliberal Self-Optimization</span>, and{' '}
                  <span className="text-rose-400 font-medium">Secular-Humanist Critique</span> across contemporary German publishing imprints.
                </p>
              </div>

              {/* Active Slice / Reset Quick Controls */}
              <div className="flex flex-wrap items-center gap-2.5 shrink-0">
                {(selectedYear || selectedDecade) && (
                  <button
                    onClick={handleFullAnalysis}
                    className="cursor-pointer px-3.5 py-2 rounded-xl bg-gold/15 border border-gold/40 text-xs font-mono font-bold text-gold hover:bg-gold hover:text-midnight-950 transition-all"
                  >
                    Clear Slice ({selectedYear || `${selectedDecade}s`}) ×
                  </button>
                )}
                <button
                  onClick={resetToMock}
                  disabled={isUploading || isTraining}
                  className="cursor-pointer px-3.5 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 text-xs font-mono text-neutral-300 flex items-center gap-2 transition-all"
                >
                  <RotateCcw size={13} />
                  <span>Sync DNB Corpus</span>
                </button>
              </div>
            </div>
          </motion.section>

          {/* 5-Card Executive Scholarly KPI Ribbon (kpi-dashboard-design pattern) */}
          <motion.section variants={itemVariants} className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <div className="glass-panel p-4 border-l-2 border-l-gold">
              <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-widest text-neutral-400 mb-1">
                <span>Corpus Volume (M)</span>
                <Database size={13} className="text-gold" />
              </div>
              <div className="text-2xl font-mono font-bold text-white tabular-nums">
                {summary?.count?.toLocaleString() || '160'}
              </div>
              <div className="text-[10px] font-mono text-neutral-500 mt-1 truncate">
                {summary?.source || 'DNB SRU Harvest'} · {summary?.year_range || '2020–2027'}
              </div>
            </div>

            <div className="glass-panel p-4 border-l-2 border-l-sky-400">
              <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-widest text-neutral-400 mb-1">
                <span>Lexical Space (|V|)</span>
                <BookOpen size={13} className="text-sky-400" />
              </div>
              <div className="text-2xl font-mono font-bold text-white tabular-nums">
                {vocabSize.toLocaleString()}
              </div>
              <div className="text-[10px] font-mono text-neutral-500 mt-1 truncate">
                NOUN · PROPN · ADJ + Bigrams
              </div>
            </div>

            <div className="glass-panel p-4 border-l-2 border-l-emerald-400">
              <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-widest text-neutral-400 mb-1">
                <span>Granularity (K)</span>
                <Layers size={13} className="text-emerald-400" />
              </div>
              <div className="text-2xl font-mono font-bold text-white tabular-nums">
                K = {numTopics}
              </div>
              <div className="text-[10px] font-mono text-emerald-400 mt-1 truncate">
                {numTopics <= 5 ? 'Macro-Archetypes' : numTopics <= 15 ? 'Meso-Inflection' : 'Micro-Thematic'}
              </div>
            </div>

            <div className="glass-panel p-4 border-l-2 border-l-purple-400">
              <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-widest text-neutral-400 mb-1">
                <span>Model Coherence</span>
                <Activity size={13} className="text-purple-400" />
              </div>
              <div className="text-xl font-mono font-bold text-white tabular-nums">
                {cvCoherence !== null ? `C_v ${cvCoherence.toFixed(3)}` : `U_M ${coherenceScore.toFixed(2)}`}
              </div>
              <div className="text-[10px] font-mono text-neutral-500 mt-1 truncate">
                U_Mass: {coherenceScore.toFixed(3)} · Variational
              </div>
            </div>

            <div className="glass-panel p-4 border-l-2 border-l-rose-400 col-span-2 md:col-span-1">
              <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-widest text-neutral-400 mb-1">
                <span>Hegemonic Voice</span>
                <Sparkles size={13} className="text-rose-400" />
              </div>
              <div className="text-sm font-mono font-bold text-white truncate pt-1">
                {dominantArchetype.label}
              </div>
              <div className="text-[10px] font-mono text-rose-400 mt-1 truncate">
                {dominantArchetype.share}% Corpus Share ({summary?.publishers?.length || 8} Houses)
              </div>
            </div>
          </motion.section>

          {/* Main Workspace Grid: Left Control Console (1 Col) + Right Multi-Tab Analytical Workbench (3 Cols) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            
            {/* Left Column (4 Cols on LG): Neural Engine & Hyperparameter Console */}
            <motion.aside variants={itemVariants} className="lg:col-span-4 space-y-6">
              <SpotlightCard className="border-white/10 bg-midnight-900/85">
                <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/[0.07]">
                  <div className="flex items-center gap-2.5">
                    <Cpu className="text-gold" size={18} />
                    <h2 className="text-xs font-mono font-bold uppercase tracking-[0.2em] text-white">
                      Bayesian Neural Console
                    </h2>
                  </div>
                  <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/25">
                    SHA1 Cached
                  </span>
                </div>

                {/* Dynamic Topic Granularity (K) Selector */}
                <div className="space-y-3.5 mb-5">
                  <div className="flex items-center justify-between">
                    <label htmlFor="k-slider" className="flex items-center gap-1.5 text-[11px] font-mono font-semibold text-neutral-300">
                      <Sliders size={13} className="text-gold" />
                      <span>Latent Topics (K = {numTopics})</span>
                    </label>
                    <span className="text-[10px] font-mono text-gold">
                      α = auto · η = auto
                    </span>
                  </div>

                  <input
                    id="k-slider"
                    type="range"
                    min={2}
                    max={30}
                    value={numTopics}
                    onChange={(e) => setNumTopics(Number(e.target.value))}
                    className="w-full accent-yellow-500 cursor-pointer h-1.5 bg-neutral-800 rounded-lg"
                  />

                  <div className="grid grid-cols-2 gap-2">
                    {defaultRegimes.map((reg) => (
                      <button
                        key={reg.k}
                        onClick={() => handleRegimeSelect(reg.k)}
                        disabled={isTraining}
                        className={clsx(
                          "cursor-pointer p-2.5 rounded-xl text-left transition-all duration-200 border flex flex-col",
                          numTopics === reg.k
                            ? "bg-gold/15 border-gold text-gold shadow-md"
                            : "bg-midnight-950/70 border-white/[0.06] text-neutral-400 hover:border-white/20 hover:text-neutral-200"
                        )}
                      >
                        <span className="text-[11px] font-mono font-bold">
                          K = {reg.k} · {reg.label.split(' ')[0]}
                        </span>
                        <span className="text-[9px] text-neutral-500 truncate mt-0.5">
                          {reg.description}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Interactive Mini Coherence Optimization Curve */}
                {coherenceGrid.length > 0 && (
                  <div className="mb-5 p-3.5 rounded-xl bg-midnight-950/80 border border-white/[0.06]">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-400">
                        Empirical C_v Optimization Curve
                      </span>
                      <span className="text-[9px] font-mono text-gold">Click node to train K</span>
                    </div>
                    <div className="h-28 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart
                          data={coherenceGrid}
                          onClick={(e: any) => {
                            if (e && e.activeLabel) {
                              handleRegimeSelect(Number(e.activeLabel));
                            }
                          }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                          <XAxis dataKey="k" tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} />
                          <YAxis domain={['auto', 'auto']} hide />
                          <RechartsTooltip
                            contentStyle={{
                              backgroundColor: '#070709',
                              border: '1px solid rgba(212,175,55,0.4)',
                              borderRadius: '8px',
                              fontSize: '10px',
                              fontFamily: 'var(--font-mono)'
                            }}
                            formatter={(val: any) => [Number(val).toFixed(4), 'C_v NPMI']}
                            labelFormatter={(label) => `Topics K = ${label}`}
                          />
                          <Line
                            type="monotone"
                            dataKey="c_v"
                            stroke="#D4AF37"
                            strokeWidth={2}
                            dot={{ r: 3.5, fill: '#FACC15' }}
                            activeDot={{ r: 5.5, fill: '#ffffff' }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                <button
                  onClick={handleFullAnalysis}
                  disabled={isTraining || isUploading}
                  className="cursor-pointer w-full py-3.5 rounded-xl bg-gold text-midnight-950 hover:bg-gold-light transition-all duration-200 text-xs font-mono font-bold uppercase tracking-[0.15em] flex items-center justify-center gap-2.5 disabled:opacity-50 shadow-lg shadow-gold/10 mb-6"
                >
                  {isTraining ? <Loader2 size={16} className="animate-spin" /> : <Cpu size={16} />}
                  <span>{isTraining ? `Synthesizing K=${numTopics}...` : `Execute Posterior Inference (K=${numTopics})`}</span>
                </button>

                {/* Diachronic Decade Segmentation */}
                <div className="space-y-3 pt-4 border-t border-white/[0.07]">
                  <div className="flex items-center justify-between">
                    <h3 className="text-[10px] font-mono font-bold uppercase tracking-widest text-neutral-400">
                      Diachronic Decade Filter
                    </h3>
                    {selectedDecade && (
                      <button
                        onClick={handleFullAnalysis}
                        className="cursor-pointer text-[10px] font-mono text-gold hover:underline"
                      >
                        Reset All
                      </button>
                    )}
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    {[1970, 1980, 1990, 2000, 2010, 2020].map((d) => (
                      <button
                        key={d}
                        onClick={() => handleDecadeSelect(d)}
                        className={clsx(
                          "cursor-pointer py-2 rounded-lg text-[11px] font-mono font-bold uppercase transition-all duration-200 border",
                          selectedDecade === d
                            ? "bg-gold border-gold text-midnight-950 shadow-md"
                            : "bg-midnight-950/60 border-white/[0.06] text-neutral-400 hover:border-white/20 hover:text-white"
                        )}
                      >
                        {d}s
                      </button>
                    ))}
                  </div>
                </div>
              </SpotlightCard>

              {/* Ideological Legend & Methodology Folio Card */}
              <div className="glass-panel p-5 space-y-3.5">
                <div className="flex items-center gap-2 text-xs font-mono font-bold uppercase tracking-widest text-neutral-200">
                  <BookOpen size={14} className="text-gold" />
                  <span>Critical Theory Archetype Key</span>
                </div>
                <div className="space-y-2.5 text-xs">
                  <div className="p-2.5 rounded-lg bg-yellow-500/5 border border-yellow-500/20 flex items-start gap-2.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-yellow-400 shrink-0 mt-1" />
                    <div>
                      <div className="font-mono font-bold text-yellow-400 text-[11px]">1. Traditional / Ecclesiastical</div>
                      <p className="text-neutral-400 text-[11px] leading-snug mt-0.5">
                        Herder, EVA, Patmos — Dogmatik, Seelsorge, Liturgie, Ökumene.
                      </p>
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-sky-500/5 border border-sky-400/20 flex items-start gap-2.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-sky-400 shrink-0 mt-1" />
                    <div>
                      <div className="font-mono font-bold text-sky-400 text-[11px]">2. Neoliberal / Self-Optimization</div>
                      <p className="text-neutral-400 text-[11px] leading-snug mt-0.5">
                        Gütersloher (Bertelsmann), Kösel — Achtsamkeit, Resilienz, Erfolg, Lebenshilfe.
                      </p>
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-rose-500/5 border border-rose-400/20 flex items-start gap-2.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-400 shrink-0 mt-1" />
                    <div>
                      <div className="font-mono font-bold text-rose-400 text-[11px]">3. Critical / Secular-Humanist</div>
                      <p className="text-neutral-400 text-[11px] leading-snug mt-0.5">
                        Suhrkamp, Alibri, Rowohlt — Religionskritik, Säkularismus, Machtkritik.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </motion.aside>

            {/* Right Column (8 Cols on LG): Multi-Tab Hermeneutics Workbench */}
            <motion.section variants={itemVariants} className="lg:col-span-8 space-y-5">
              
              {/* Workbench View Switcher Bar */}
              <div className="flex flex-wrap items-center justify-between gap-3 bg-midnight-900/90 backdrop-blur-xl p-2 rounded-2xl border border-white/[0.08]">
                <div className="flex flex-wrap gap-1.5">
                  <button
                    onClick={() => setActiveTab('clusters')}
                    className={clsx(
                      "cursor-pointer px-4 py-2.5 rounded-xl text-xs font-mono font-bold uppercase tracking-wider transition-all duration-200 flex items-center gap-2",
                      activeTab === 'clusters'
                        ? "bg-gold text-midnight-950 shadow-md"
                        : "text-neutral-400 hover:text-white hover:bg-white/[0.04]"
                    )}
                  >
                    <Layers size={14} />
                    <span>1. Discursive Clusters &amp; MARC21</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('matrix')}
                    className={clsx(
                      "cursor-pointer px-4 py-2.5 rounded-xl text-xs font-mono font-bold uppercase tracking-wider transition-all duration-200 flex items-center gap-2",
                      activeTab === 'matrix'
                        ? "bg-gold text-midnight-950 shadow-md"
                        : "text-neutral-400 hover:text-white hover:bg-white/[0.04]"
                    )}
                  >
                    <Building2 size={14} />
                    <span>2. Publisher × Archetype Matrix</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('diachronic')}
                    className={clsx(
                      "cursor-pointer px-4 py-2.5 rounded-xl text-xs font-mono font-bold uppercase tracking-wider transition-all duration-200 flex items-center gap-2",
                      activeTab === 'diachronic'
                        ? "bg-gold text-midnight-950 shadow-md"
                        : "text-neutral-400 hover:text-white hover:bg-white/[0.04]"
                    )}
                  >
                    <BarChart3 size={14} />
                    <span>3. Diachronic &amp; Coherence Atlas</span>
                  </button>
                </div>
              </div>

              {/* TAB 1: Discursive Clusters & MARC21 Paratextual Inspector */}
              {activeTab === 'clusters' && (
                <TopicModelViz
                  topics={topics}
                  isTraining={isTraining}
                  selectedYear={selectedYear}
                  selectedDecade={selectedDecade}
                  coherenceScore={coherenceScore}
                  cvCoherence={cvCoherence}
                  representativeDocs={representativeDocs}
                />
              )}

              {/* TAB 2: Institutional Publisher × Ideological Archetype Matrix */}
              {activeTab === 'matrix' && (
                <div className="glass-panel p-6 lg:p-8 space-y-8">
                  <div className="border-b border-white/[0.08] pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <span className="text-[10px] font-mono uppercase tracking-[0.25em] text-gold">
                        INSTITUTIONAL CROSS-TABULATION //
                      </span>
                      <h3 className="text-2xl sm:text-3xl font-heading font-bold italic text-white mt-1">
                        German Publishing Houses × Ideological Archetype Affinity
                      </h3>
                    </div>
                    <span className="text-xs font-mono text-neutral-400 bg-midnight-950 px-3 py-1.5 rounded-lg border border-white/10">
                      Posterior θ × φ Synthesis
                    </span>
                  </div>

                  {/* Stacked Bar Chart of Publisher Archetype Shares */}
                  <div className="h-80 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={publisherArchetypes}
                        margin={{ top: 10, right: 20, left: 0, bottom: 20 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                        <XAxis
                          dataKey="publisher"
                          tick={{ fill: '#E2E8F0', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <YAxis
                          unit="%"
                          tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <RechartsTooltip
                          contentStyle={{
                            backgroundColor: '#070709',
                            border: '1px solid rgba(255,255,255,0.15)',
                            borderRadius: '12px',
                            fontFamily: 'var(--font-mono)',
                            fontSize: '11px'
                          }}
                        />
                        <Legend wrapperStyle={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }} />
                        <Bar dataKey="Traditional" name="Traditional / Ecclesiastical (%)" stackId="a" fill="#EAB308" radius={[0, 0, 0, 0]} />
                        <Bar dataKey="Neoliberal" name="Neoliberal / Self-Optimization (%)" stackId="a" fill="#38BDF8" />
                        <Bar dataKey="Critical" name="Critical / Secular-Humanist (%)" stackId="a" fill="#FB7185" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Quantitative Cross-Tabulation Table */}
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse font-mono text-xs">
                      <thead>
                        <tr className="border-b border-white/10 text-[10px] uppercase tracking-wider text-neutral-400">
                          <th className="py-3 px-4">German Publishing House (Imprint)</th>
                          <th className="py-3 px-4 text-yellow-400">Traditional / Ecclesia</th>
                          <th className="py-3 px-4 text-sky-400">Neoliberal / Market</th>
                          <th className="py-3 px-4 text-rose-400">Critical / Secular</th>
                          <th className="py-3 px-4">Primary Discursive Orientation</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.06]">
                        {publisherArchetypes.map((row) => {
                          const maxVal = Math.max(row.Traditional, row.Neoliberal, row.Critical);
                          const dom =
                            maxVal === row.Traditional
                              ? 'Traditional / Ecclesiastical'
                              : maxVal === row.Neoliberal
                              ? 'Neoliberal / Self-Optimization'
                              : 'Critical / Secular-Humanist';
                          return (
                            <tr key={row.publisher} className="hover:bg-white/[0.02] transition-colors">
                              <td className="py-3 px-4 font-bold text-white">{row.publisher}</td>
                              <td className="py-3 px-4 text-yellow-400">{row.Traditional}%</td>
                              <td className="py-3 px-4 text-sky-400">{row.Neoliberal}%</td>
                              <td className="py-3 px-4 text-rose-400">{row.Critical}%</td>
                              <td className="py-3 px-4 text-neutral-300">{dom}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* TAB 3: Diachronic Evolution & Hyperparameter Coherence Atlas */}
              {activeTab === 'diachronic' && (
                <div className="space-y-6">
                  <SpotlightCard className="border-white/10 bg-midnight-900/85">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-4 border-b border-white/[0.07]">
                      <div>
                        <span className="text-[10px] font-mono uppercase tracking-[0.25em] text-gold">
                          TEMPORAL OBSERVATORY //
                        </span>
                        <h3 className="text-2xl font-heading font-bold italic text-white mt-0.5">
                          Diachronic Publication Volume &amp; Interactive Year Slicing
                        </h3>
                      </div>
                      <span className="text-[10px] font-mono uppercase tracking-widest bg-gold/15 text-gold px-3 py-1.5 rounded-lg border border-gold/30">
                        Click Any Year Node to Slice LDA
                      </span>
                    </div>
                    <TrendsGraph
                      data={trendsData}
                      onYearSelect={handleYearSelect}
                      selectedYear={selectedYear}
                    />
                  </SpotlightCard>

                  {/* Full Coherence Optimization Table */}
                  {coherenceGrid.length > 0 && (
                    <div className="glass-panel p-6 space-y-4">
                      <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                        <div>
                          <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-gold">
                            EMPIRICAL VALIDATION (RÖDER ET AL., 2015) //
                          </span>
                          <h4 className="text-xl font-heading font-bold italic text-white">
                            Hyperparameter Grid Search Matrix (K ∈ [4, 30])
                          </h4>
                        </div>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse font-mono text-xs">
                          <thead>
                            <tr className="border-b border-white/10 text-[10px] uppercase tracking-wider text-neutral-400">
                              <th className="py-2.5 px-3">Topics (K)</th>
                              <th className="py-2.5 px-3 text-gold">C_v Coherence (NPMI)</th>
                              <th className="py-2.5 px-3 text-emerald-400">U_Mass Coherence</th>
                              <th className="py-2.5 px-3">Log Perplexity Bound</th>
                              <th className="py-2.5 px-3">Action</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-white/[0.06]">
                            {coherenceGrid.map((pt) => (
                              <tr
                                key={pt.k}
                                className={clsx(
                                  "hover:bg-white/[0.03] transition-colors",
                                  numTopics === pt.k && "bg-gold/10"
                                )}
                              >
                                <td className="py-2.5 px-3 font-bold text-white">K = {pt.k}</td>
                                <td className="py-2.5 px-3 text-gold font-semibold">{pt.c_v.toFixed(4)}</td>
                                <td className="py-2.5 px-3 text-emerald-400">{pt.u_mass.toFixed(4)}</td>
                                <td className="py-2.5 px-3 text-neutral-400">{pt.log_perplexity.toFixed(4)}</td>
                                <td className="py-2.5 px-3">
                                  <button
                                    onClick={() => {
                                      handleRegimeSelect(pt.k);
                                      setActiveTab('clusters');
                                    }}
                                    className="cursor-pointer px-2.5 py-1 rounded bg-white/[0.06] hover:bg-gold hover:text-midnight-950 text-[10px] font-bold transition-colors"
                                  >
                                    Load K={pt.k}
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </motion.section>
          </div>
        </motion.main>

        {/* Majestic Author Attribution Colophon */}
        <motion.footer
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8, duration: 0.7 }}
          className="w-full text-center mt-16 pt-8 pb-4 relative z-10 border-t border-white/[0.07]"
        >
          <div className="mx-auto inline-flex items-center gap-3 py-2.5 px-6 rounded-full bg-midnight-900/90 backdrop-blur-xl border border-white/10 shadow-xl">
            <span className="w-2 h-2 rounded-full bg-gold" />
            <BlurText
              text="Dissertation Observatory by Paul Marandi · Ph.D. Scholar, CGS, SLL&CS, JNU"
              delay={30}
              className="text-neutral-300 font-mono uppercase text-[10px] sm:text-xs tracking-[0.22em] font-semibold"
            />
          </div>
        </motion.footer>
      </div>
    </div>
  );
}

export default App;
