import { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import type { Variants } from 'framer-motion';
import ShinyText from './components/ShinyText';
import SpotlightCard from './components/SpotlightCard';
import TrendsGraph from './components/TrendsGraph';
import Particles from './components/Particles';
import BlurText from './components/BlurText';
import { useLDA } from './hooks/useLDA';
import { Database, Cpu, BarChart3, Loader2, Upload, RotateCcw, BookOpen } from 'lucide-react';
import TopicModelViz from './components/TopicModelViz';
import clsx from 'clsx';

function App() {
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [selectedDecade, setSelectedDecade] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { 
    isTraining, isUploading, trendsData, summary, topics, 
    coherenceScore, representativeDocs,
    fetchTrends, fetchSummary, fetchTopics, runLDA, uploadDataset, resetToMock 
  } = useLDA();

  useEffect(() => {
    fetchTrends();
    fetchSummary();
    fetchTopics();
  }, []);

  const handleYearSelect = async (year: number) => {
    setSelectedYear(year);
    setSelectedDecade(null);
    await runLDA(year);
  };

  const handleDecadeSelect = async (decade: number) => {
    setSelectedDecade(decade);
    setSelectedYear(null);
    await runLDA(undefined, decade);
  };

  const handleFullAnalysis = async () => {
    setSelectedYear(null);
    setSelectedDecade(null);
    await runLDA();
  };

  const handleExport = () => {
    const report = {
      researchTitle: "Mediating Faith and Power",
      generatedAt: new Date().toISOString(),
      corpusSummary: summary,
      modelCoherence: coherenceScore,
      topics: topics,
      temporalContext: { selectedYear, selectedDecade }
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `LDA_Research_Report_${new Date().getTime()}.json`;
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
        staggerChildren: 0.15,
        delayChildren: 0.2
      } 
    }
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: 30, filter: 'blur(10px)' },
    visible: { 
      opacity: 1, 
      y: 0, 
      filter: 'blur(0px)',
      transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } 
    }
  };

  return (
    <div className="relative min-h-screen bg-midnight-950 font-body text-neutral-300 overflow-x-hidden select-none">
      
      {/* WebGL Particle Background Layer */}
      <div className="absolute inset-0 z-0 pointer-events-auto opacity-70">
        <Particles
          particleColors={['#CA8A04', '#EAB308', '#ffffff', '#A16207']}
          particleCount={300}
          particleSpread={15}
          speed={0.15}
          particleBaseSize={80}
          moveParticlesOnHover={true}
          alphaParticles={true}
          disableRotation={false}
          cameraDistance={30}
        />
      </div>

      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 bg-midnight-950/50 backdrop-blur-xl border-b border-white/5 px-8 py-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gold/10 border border-gold/30 rounded-xl flex items-center justify-center shadow-lg shadow-gold/10">
            <Database className="text-gold" size={20} />
          </div>
          <div>
            <h1 className="text-xl font-black tracking-tighter text-white uppercase italic">Mediating Faith & Power</h1>
            <p className="text-[10px] text-gold/60 font-bold uppercase tracking-[0.2em]">Religious Authority & German Publishing</p>
          </div>
        </div>
        <div className="flex gap-4">
          <div className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${isTraining ? 'bg-gold animate-pulse' : 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]'}`} />
            <span className="text-xs font-bold text-white/70 uppercase tracking-widest">
              {isTraining ? 'Neural Engine Active' : 'System Ready'}
            </span>
          </div>
        </div>
      </nav>

      <div className="relative z-10 w-full p-6 lg:p-12 min-h-screen flex flex-col justify-between">
        <motion.div 
          className="max-w-7xl mx-auto w-full pt-20"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {/* Header */}
          <motion.header variants={itemVariants} className="mb-14 text-center max-w-4xl mx-auto">
            <h1 className="text-4xl lg:text-7xl font-heading font-black text-neutral-50 mb-4 tracking-tighter italic drop-shadow-2xl">
              <ShinyText text="Mediating Faith and Power" speed={3} />
            </h1>
            <p className="text-neutral-400 text-lg md:text-xl font-light tracking-wide max-w-3xl mx-auto leading-relaxed">
              Computational Hermeneutics analyzing the <span className="text-gold italic font-medium">German Publishing Landscape (1970–2025)</span> through the lens of the Propaganda Model.
            </p>
          </motion.header>

          {/* Main Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* Left Column: Controls & Stats */}
            <div className="space-y-8 flex flex-col">
              <motion.div variants={itemVariants}>
                <SpotlightCard className="shadow-2xl shadow-gold/5 border-gold/10">
                  <div className="flex items-center gap-3 mb-6">
                    <Database className="text-gold" size={24} />
                    <h2 className="text-sm font-bold uppercase tracking-[0.2em] text-neutral-200">Corpus Metadata</h2>
                  </div>
                  {summary ? (
                    <div className="space-y-4 text-sm text-neutral-400">
                      <div className="flex justify-between border-b border-neutral-800/80 pb-2 transition-all hover:text-neutral-300">
                        <span>Active Dataset</span>
                        <span className="text-gold font-medium italic">{summary.source}</span>
                      </div>
                      <div className="flex justify-between border-b border-neutral-800/80 pb-2 transition-all hover:text-neutral-300">
                        <span>Volume (Records)</span>
                        <span className="text-neutral-200 font-medium">{summary.count?.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between border-0 transition-all hover:text-neutral-300">
                        <span>Unique Publishers</span>
                        <span className="text-neutral-200 font-medium">{summary.publishers?.length || 0}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="animate-pulse flex space-x-4">
                      <div className="flex-1 space-y-4 py-1">
                        <div className="h-4 bg-neutral-800/50 rounded w-3/4"></div>
                        <div className="h-4 bg-neutral-800/50 rounded w-5/6"></div>
                      </div>
                    </div>
                  )}

                  <div className="mt-6 pt-6 border-t border-neutral-800/50 space-y-3">
                    <div className="bg-neutral-900/50 border border-neutral-800 rounded-xl p-4 mb-4">
                      <div className="flex items-center gap-2 mb-2 text-gold-light">
                        <BookOpen size={14} />
                        <span className="text-[10px] font-black uppercase tracking-widest text-gold/80">Archival Format Guide</span>
                      </div>
                      <ul className="text-[11px] text-neutral-500 space-y-1.5 list-disc list-inside font-light">
                        <li><strong className="text-neutral-400">date:</strong> YYYY (Temporal Scope)</li>
                        <li><strong className="text-neutral-400">publisher:</strong> DNB Metadata Mapping</li>
                        <li><strong className="text-neutral-400">text:</strong> Paratext/Catalogue Corpus</li>
                      </ul>
                    </div>

                    <input 
                      type="file" 
                      accept=".csv" 
                      ref={fileInputRef} 
                      className="hidden" 
                      onChange={handleFileUpload}
                    />
                    <div className="grid grid-cols-1 gap-3">
                      <button 
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isUploading}
                        className="w-full flex justify-center items-center gap-2 py-3 px-4 rounded-xl bg-gold/10 border border-gold/30 text-gold hover:bg-gold hover:text-midnight-950 transition-all duration-300 text-[11px] uppercase tracking-widest font-black disabled:opacity-50 group"
                      >
                        {isUploading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
                        {isUploading ? 'Ingesting...' : 'Ingest Archival Data'}
                      </button>

                      <button 
                        onClick={handleExport}
                        disabled={!topics.length}
                        className="w-full flex justify-center items-center gap-2 py-3 px-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-500 hover:bg-emerald-500 hover:text-midnight-950 transition-all duration-300 text-[11px] uppercase tracking-widest font-black disabled:opacity-30 group"
                      >
                        <Database size={16} />
                        Export Research Report
                      </button>

                      <button 
                        onClick={resetToMock}
                        disabled={isUploading || isTraining}
                        className="w-full flex justify-center items-center gap-2 py-3 px-4 rounded-xl bg-neutral-900/50 border border-neutral-800 text-neutral-500 hover:text-neutral-200 hover:bg-neutral-800 transition-all duration-300 text-[11px] uppercase tracking-widest font-bold disabled:opacity-50 group"
                      >
                        <RotateCcw size={14} />
                        Load Research Proxy
                      </button>
                    </div>
                  </div>
                </SpotlightCard>
              </motion.div>

              <motion.div variants={itemVariants} className="flex-grow flex flex-col">
                <SpotlightCard className="flex-grow flex flex-col shadow-2xl shadow-gold/5 border-gold/10">
                  <div className="flex items-center gap-3 mb-6">
                    <Cpu className="text-gold" size={20} />
                    <h2 className="text-sm font-bold uppercase tracking-[0.2em] text-neutral-200">Neural Engine</h2>
                  </div>
                  <p className="text-[11px] text-neutral-500 mb-6 leading-relaxed">
                    Execute <span className="text-neutral-300 font-medium italic">Latent Dirichlet Allocation</span> to identify recurring thematic patterns.
                  </p>
                  
                  <button 
                    onClick={handleFullAnalysis}
                    disabled={isTraining || isUploading}
                    className="w-full py-4 rounded-xl bg-white text-midnight-950 hover:bg-gold transition-all duration-500 text-xs font-black uppercase tracking-[0.2em] flex items-center justify-center gap-3 disabled:opacity-50 shadow-[0_0_30px_rgba(255,255,255,0.1)] group mb-8"
                  >
                    {isTraining ? <Loader2 size={18} className="animate-spin" /> : <Cpu size={18} className="group-hover:rotate-90 transition-transform duration-700" />}
                    {isTraining ? 'Training Model...' : 'Execute Analysis'}
                  </button>

                  <div className="space-y-4 pt-6 border-t border-neutral-800/50">
                    <div className="flex items-center justify-between">
                      <h3 className="text-[10px] font-black uppercase tracking-widest text-neutral-400">Segment by Decade</h3>
                      <div className="w-1.5 h-1.5 rounded-full bg-gold/50 shadow-[0_0_5px_#CA8A04]" />
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {[1970, 1980, 1990, 2000, 2010, 2020].map((d) => (
                        <button
                          key={d}
                          onClick={() => handleDecadeSelect(d)}
                          className={clsx(
                            "px-3 py-2 rounded-lg text-[10px] font-black tracking-widest uppercase transition-all duration-300 border",
                            selectedDecade === d 
                              ? "bg-gold border-gold text-midnight-950 shadow-lg shadow-gold/20" 
                              : "bg-neutral-900/50 border-neutral-800 text-neutral-500 hover:border-neutral-600 hover:text-neutral-200"
                          )}
                        >
                          {d}s
                        </button>
                      ))}
                    </div>
                  </div>
                </SpotlightCard>
              </motion.div>
            </div>

            {/* Right Column: Visualization */}
            <div className="lg:col-span-2 space-y-8 flex flex-col z-10 w-full relative">
              
              <motion.div variants={itemVariants} className="w-full">
                <SpotlightCard className="shadow-2xl shadow-gold/5 border-gold/10 overflow-hidden w-full relative z-20">
                  <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-2 relative z-30">
                    <BarChart3 className="text-gold" size={24} />
                    <div className="flex-grow flex items-center justify-between">
                      <h2 className="text-xl font-heading font-bold text-neutral-50 tracking-widest uppercase italic">Diachronic Thematic Evolution</h2>
                      <span className="text-[10px] uppercase tracking-widest font-black bg-gold/20 text-gold px-3 py-1.5 rounded-md border border-gold/30">Propaganda Filter Mapping</span>
                    </div>
                  </div>
                  <p className="text-xs text-neutral-500 mb-6 border-b border-neutral-800/60 pb-4 font-light relative z-30">
                    Interact with the temporal nodes below to isolate specific decade-wise shifts in the <span className="text-neutral-300">Filtering Mechanisms</span> of the German book market.
                  </p>
                  <div className="relative z-30 bg-midnight-950/40 rounded-xl -mx-2 -mb-2 p-2">
                    <TrendsGraph 
                      data={trendsData} 
                      onYearSelect={handleYearSelect} 
                      selectedYear={selectedYear} 
                    />
                  </div>
                </SpotlightCard>
              </motion.div>

              <motion.div variants={itemVariants} className="w-full">
                <div className="flex items-center gap-4 mb-4">
                  <div className="h-px flex-1 bg-white/5"></div>
                  <h3 className="text-[10px] font-black uppercase tracking-[0.4em] text-white/40 italic">Discursive Patterns Analysis</h3>
                  <div className="h-px flex-1 bg-white/5"></div>
                </div>
                <div className="w-full h-full min-h-[550px] rounded-2xl overflow-hidden bg-black/5 ring-1 ring-inset ring-neutral-800/20">
                  <TopicModelViz 
                    topics={topics} 
                    isTraining={isTraining} 
                    selectedYear={selectedYear}
                    selectedDecade={selectedDecade}
                    coherenceScore={coherenceScore}
                    representativeDocs={representativeDocs}
                  />
                </div>
              </motion.div>

              {/* Research Methodology Note */}
              <motion.div
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.6 }}
                className="p-6 rounded-2xl bg-gold/5 border border-gold/10 backdrop-blur-sm"
              >
                <div className="flex gap-4 items-start">
                  <div className="p-2 bg-gold/10 rounded-lg text-gold mt-1">
                    <BookOpen size={20} />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white mb-2 uppercase tracking-[0.2em] italic">Ideological Filtering Diagnostics</h4>
                    <p className="text-sm text-neutral-400 leading-relaxed font-light">
                      This visualization identifies systematic disparities between publisher thematic output and market visibility. 
                      Recurring latent themes such as <span className="text-neutral-200 italic">Atheismus</span> or <span className="text-neutral-200 italic">Kirchenkritik</span> are 
                      cross-referenced against paratextual and catalogue corpora to detect filtering mechanisms as defined by the <span className="text-gold font-medium">Propaganda Model (Chomsky, 1988)</span>.
                    </p>
                  </div>
                </div>
              </motion.div>

            </div>
          </div>
        </motion.div>

        {/* Majestic Footer Attribution */}
        <motion.footer 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.5, duration: 1, ease: 'easeOut' }}
          className="w-full text-center mt-20 pt-8 pb-4 relative z-10 border-t border-neutral-800/40 px-4"
        >
          <div className="mx-auto flex justify-center py-2 px-6 rounded-full bg-neutral-900/50 backdrop-blur-sm border border-neutral-800 inline-block">
            <BlurText 
              text="Thesis by Paul Marandi | Ph.D. Research @ CGS, SL, JNU"
              delay={40}
              className="text-neutral-400 font-heading uppercase text-[10px] md:text-xs tracking-[0.3em] font-bold"
            />
          </div>
        </motion.footer>

      </div>
    </div>
  );
}

export default App;
