import { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import type { Variants } from 'framer-motion';
import ShinyText from './components/ShinyText';
import SpotlightCard from './components/SpotlightCard';
import TrendsGraph from './components/TrendsGraph';
import Particles from './components/Particles';
import BlurText from './components/BlurText';
import { useLDA } from './hooks/useLDA';
import { Database, Filter, Cpu, BarChart3, Loader2, Upload } from 'lucide-react';

function App() {
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [vizKey, setVizKey] = useState(0); 
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { isTraining, isUploading, trendsData, summary, fetchTrends, fetchSummary, runLDA, uploadDataset, API_BASE } = useLDA();

  useEffect(() => {
    fetchTrends();
    fetchSummary();
  }, []);

  const handleYearSelect = async (year: number) => {
    setSelectedYear(year);
    await runLDA(year);
    setVizKey(prev => prev + 1);
  };

  const handleFullAnalysis = async () => {
    setSelectedYear(null);
    await runLDA();
    setVizKey(prev => prev + 1);
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

      <div className="relative z-10 w-full p-6 lg:p-12 min-h-screen flex flex-col justify-between">
        <motion.div 
          className="max-w-7xl mx-auto w-full"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {/* Header */}
          <motion.header variants={itemVariants} className="mb-14 text-center max-w-4xl mx-auto pt-8">
            <h1 className="text-4xl lg:text-6xl font-heading font-semibold text-neutral-50 mb-4 flex items-center justify-center tracking-tight drop-shadow-2xl">
              <ShinyText text="The Computational Turn" speed={3} className="mr-3" />
              <span className="text-neutral-600 font-light mx-2 opacity-50">|</span> 
              <span className="font-light italic text-gold-light ml-2">Voices on Religion</span>
            </h1>
            <p className="text-neutral-400 text-lg md:text-xl font-light tracking-wide drop-shadow-md">
              High-fidelity Latent Dirichlet Allocation (LDA) dashboard mapping theological and secular-critical trends within the German publishing landscape.
            </p>
          </motion.header>

          {/* Main Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* Left Column: Controls & Stats */}
            <div className="space-y-8 flex flex-col">
              <motion.div variants={itemVariants}>
                <SpotlightCard className="shadow-2xl shadow-gold/5 border-gold/10">
                  <div className="flex items-center gap-3 mb-6">
                    <Database className="text-gold animate-pulse" size={24} />
                    <h2 className="text-xl font-heading text-neutral-50 tracking-wide">Corpus Overview</h2>
                  </div>
                  {summary ? (
                    <div className="space-y-4 text-sm text-neutral-400">
                      <div className="flex justify-between border-b border-neutral-800/80 pb-2 transition-all hover:text-neutral-300">
                        <span>Source Hub</span>
                        <span className="text-neutral-200">{summary.source}</span>
                      </div>
                      <div className="flex justify-between border-b border-neutral-800/80 pb-2 transition-all hover:text-neutral-300">
                        <span>Total Records</span>
                        <span className="text-neutral-200 font-medium">{summary.count} document(s)</span>
                      </div>
                      <div className="flex justify-between border-b border-neutral-800/80 pb-2 border-0 transition-all hover:text-neutral-300">
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

                  <div className="mt-6 pt-6 border-t border-neutral-800/50">
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
                      className="w-full flex justify-center items-center gap-2 py-3 px-4 rounded-xl bg-neutral-950/80 border border-gold/30 text-gold hover:bg-gold hover:text-midnight-950 hover:shadow-[0_0_15px_rgba(202,138,4,0.4)] transition-all duration-300 text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed group"
                    >
                      {isUploading ? <Loader2 size={18} className="animate-spin" /> : <Upload size={18} className="group-hover:-translate-y-1 transition-transform" />}
                      {isUploading ? 'Ingesting Dataset...' : 'Upload Custom Corpus'}
                    </button>
                  </div>
                </SpotlightCard>
              </motion.div>

              <motion.div variants={itemVariants} className="flex-grow flex flex-col">
                <SpotlightCard className="flex-grow flex flex-col shadow-2xl shadow-gold/5 border-gold/10">
                  <div className="flex items-center gap-3 mb-4">
                    <Cpu className="text-gold" size={24} />
                    <h2 className="text-xl font-heading text-neutral-50 tracking-wide">Neural Engine</h2>
                  </div>
                  
                  <p className="text-sm text-neutral-400 mb-6 flex-grow font-light leading-relaxed">
                    Execute full-spectrum LDA analysis to regenerate the topic distribution map. Or interact with the graph to isolate specific temporal slices.
                  </p>

                  <button 
                    onClick={handleFullAnalysis}
                    disabled={isTraining}
                    className="w-full py-4 px-4 bg-neutral-900 border border-neutral-700 hover:border-gold/50 text-neutral-200 hover:text-gold hover:bg-neutral-800 rounded-xl transition-all duration-300 flex items-center justify-center gap-2 font-medium shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed group"
                  >
                    {isTraining ? <Loader2 className="animate-spin text-gold" size={20} /> : <Filter size={20} className="text-gold group-hover:scale-110 transition-transform" />}
                    {isTraining ? 'Training Sub-Models...' : 'Execute Full Analysis'}
                  </button>

                  {selectedYear && !isTraining && (
                    <div className="mt-4 p-4 border border-gold/30 bg-gold/5 backdrop-blur-md text-gold-light rounded-xl text-sm flex justify-between items-center shadow-inner">
                      <span>Active Slice: <strong className="text-gold">{selectedYear}</strong></span>
                      <button onClick={handleFullAnalysis} className="text-xs hover:text-gold opacity-80 hover:opacity-100 transition-opacity uppercase tracking-widest font-bold">Clear Target</button>
                    </div>
                  )}
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
                      <h2 className="text-xl font-heading text-neutral-50 tracking-wide">Publisher Archetypes</h2>
                      <span className="text-[10px] uppercase tracking-widest font-bold bg-neutral-900/90 border border-neutral-700 text-gold-light px-3 py-1.5 rounded-md shadow-sm">Interactive</span>
                    </div>
                  </div>
                  <p className="text-sm text-neutral-500 mb-6 border-b border-neutral-800/60 pb-4 font-light relative z-30">
                    Click on a specific year node below to dynamically re-train the LDA topic model on that precise temporal band.
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

              <motion.div variants={itemVariants} className="flex-grow w-full">
                <SpotlightCard className="flex-grow min-h-[550px] !p-1 overflow-hidden relative group shadow-2xl border-neutral-800 w-full bg-white/5 backdrop-blur-sm z-20">
                  {isTraining && (
                      <div className="absolute inset-0 z-40 bg-midnight-950/90 backdrop-blur-xl flex items-center justify-center transition-all">
                        <div className="flex flex-col items-center">
                          <Loader2 className="animate-spin text-gold mb-6" size={56} />
                          <p className="text-neutral-200 font-heading text-xl animate-pulse tracking-wide">Synthesizing Topic Clusters...</p>
                        </div>
                      </div>
                  )}
                  <div className="w-full h-full min-h-[550px] rounded-2xl overflow-hidden bg-white/95 ring-1 ring-inset ring-black/10">
                    <iframe 
                        key={vizKey}
                        src={`${API_BASE}/api/topic-viz`} 
                        className="w-full h-full min-h-[550px] border-0 mix-blend-multiply opacity-95 group-hover:opacity-100 transition-opacity duration-500"
                        title="LDA pyLDAvis Output"
                    />
                  </div>
                </SpotlightCard>
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
              text="This webapp is made by Paul Marandi, Phd, CGS, SL, JNU."
              delay={40}
              animateBy="letters"
              direction="bottom"
              className="text-neutral-400 font-heading uppercase text-xs md:text-sm tracking-[0.2em] font-medium"
            />
          </div>
        </motion.footer>

      </div>
    </div>
  );
}

export default App;
