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
import { Layers, Info, Activity } from 'lucide-react';
import clsx from 'clsx';

interface Keyword {
  word: string;
  weight: number;
}

interface Topic {
  id: number;
  prevalence: number;
  keywords: Keyword[];
}

interface TopicModelVizProps {
  topics: Topic[];
  isTraining: boolean;
}

const TopicModelViz: React.FC<TopicModelVizProps> = ({ topics, isTraining }) => {
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null);

  const selectedTopic = topics.find(t => t.id === selectedTopicId) || topics[0];

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

  return (
    <div className="flex flex-col lg:flex-row h-full min-h-[550px] w-full bg-midnight-950/30 backdrop-blur-md rounded-2xl overflow-hidden border border-neutral-800/50 shadow-2xl shadow-black/40">
      
      {/* Sidebar: Topic Selection */}
      <div className="w-full lg:w-72 border-r border-neutral-800/50 bg-neutral-900/60 p-5 overflow-y-auto max-h-[250px] lg:max-h-none custom-scrollbar">
        <div className="flex items-center gap-3 mb-6 px-1">
          <div className="w-2 h-6 bg-gold rounded-full" />
          <h3 className="text-xs font-heading font-black text-neutral-300 uppercase tracking-[0.2em]">Clusters</h3>
        </div>
        
        <div className="space-y-3">
          {topics.map((topic) => (
            <motion.button
              key={topic.id}
              whileHover={{ x: 6, backgroundColor: 'rgba(202, 138, 4, 0.08)' }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setSelectedTopicId(topic.id)}
              className={clsx(
                "w-full text-left p-4 rounded-xl transition-all duration-500 border flex flex-col gap-2 group relative overflow-hidden",
                (selectedTopicId === topic.id || (selectedTopicId === null && topic.id === topics[0].id))
                  ? "bg-gold/10 border-gold/40 shadow-[0_4px_15px_rgba(202,138,4,0.15)] ring-1 ring-gold/20"
                  : "bg-neutral-950/40 border-neutral-800/50 hover:border-neutral-600/50"
              )}
            >
              {(selectedTopicId === topic.id || (selectedTopicId === null && topic.id === topics[0].id)) && (
                <motion.div 
                   layoutId="active-indicator"
                   className="absolute left-0 top-0 bottom-0 w-1 bg-gold shadow-[0_0_10px_#CA8A04]"
                />
              )}
              
              <div className="flex justify-between items-center relative z-10">
                <span className={clsx(
                  "text-[10px] font-black font-heading uppercase tracking-[0.15em]",
                  (selectedTopicId === topic.id || (selectedTopicId === null && topic.id === topics[0].id))
                    ? "text-gold"
                    : "text-neutral-500"
                )}>
                  Pattern {topic.id + 1}
                </span>
                <span className="text-[10px] font-bold text-neutral-100 bg-neutral-800/80 backdrop-blur-sm px-2 py-0.5 rounded-full border border-neutral-700/50">
                  {topic.prevalence}%
                </span>
              </div>
              <div className="text-[11px] text-neutral-400 truncate font-medium group-hover:text-neutral-200 transition-colors">
                {topic.keywords.slice(0, 3).map(k => k.word).join(' · ')}
              </div>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Main Content: Keyword Distribution */}
      <div className="flex-grow p-8 flex flex-col bg-gradient-to-br from-midnight-950/40 to-neutral-950/40 relative">
        <AnimatePresence mode="wait">
          <motion.div
            key={selectedTopic?.id || 'none'}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="flex-grow flex flex-col h-full"
          >
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10 pb-8 border-b border-neutral-800/40">
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                   <h2 className="text-4xl font-heading font-light text-neutral-50 tracking-tight">
                    Topic Cluster <span className="text-gold font-bold">#{selectedTopic ? selectedTopic.id + 1 : '?'}</span>
                  </h2>
                </div>
                <p className="text-sm text-neutral-400 font-light tracking-wide max-w-lg leading-relaxed">
                  Latent semantic distribution across the corpus. Higher weights indicate term importance within this specific cognitive cluster.
                </p>
              </div>

              <div className="flex items-center gap-6 bg-black/30 backdrop-blur-xl p-4 rounded-2xl border border-neutral-800/80 shadow-2xl">
                <div className="flex flex-col items-center px-2">
                  <span className="text-[10px] text-neutral-500 uppercase font-black tracking-widest mb-1">Prevalence</span>
                  <span className="text-xl text-neutral-100 font-black tabular-nums">{selectedTopic?.prevalence}%</span>
                </div>
                <div className="w-[1px] h-10 bg-neutral-800/80" />
                <div className="flex flex-col items-center px-2">
                  <span className="text-[10px] text-neutral-500 uppercase font-black tracking-widest mb-1">Vocabulary</span>
                  <span className="text-xl text-neutral-100 font-black tabular-nums">{selectedTopic?.keywords.length}</span>
                </div>
              </div>
            </div>

            <div className="flex-grow w-full min-h-[300px] relative px-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={selectedTopic?.keywords || []}
                  margin={{ top: 0, right: 40, left: 20, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#1e293b" />
                  <XAxis 
                    type="number" 
                    hide 
                    domain={[0, 'dataMax']} 
                  />
                  <YAxis 
                    dataKey="word" 
                    type="category" 
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#CBD5E1', fontSize: 13, fontWeight: 500, fontFamily: 'var(--font-heading)' }}
                    width={100}
                  />
                  <Tooltip 
                    cursor={{ fill: 'rgba(255, 255, 255, 0.03)' }}
                    contentStyle={{ 
                      backgroundColor: 'rgba(15, 23, 42, 0.95)', 
                      borderRadius: '16px', 
                      border: '1px solid rgba(202, 138, 4, 0.3)',
                      boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
                      backdropFilter: 'blur(12px)',
                      padding: '12px'
                    }}
                    labelStyle={{ color: '#F8FAFC', fontWeight: 'bold', fontSize: '14px', marginBottom: '8px' }}
                    itemStyle={{ color: '#F59E0B', fontSize: '12px' }}
                    formatter={(value: any) => [`${(Number(value) * 100).toFixed(2)}% Contribution`, 'Semantic Weight']}
                  />
                  <Bar 
                    dataKey="weight" 
                    radius={[0, 6, 6, 0]}
                    barSize={24}
                    animationDuration={1500}
                    animationEasing="ease-out"
                  >
                    {
                      selectedTopic?.keywords.map((_, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={index === 0 ? '#F59E0B' : '#D97706'} 
                          fillOpacity={1 - (index * 0.05)}
                        />
                      ))
                    }
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-8 p-5 rounded-2xl bg-neutral-900/60 border border-neutral-800/80 flex gap-4 items-start shadow-xl">
               <div className="p-2 bg-gold/10 rounded-lg text-gold mt-1">
                 <Info size={18} />
               </div>
               <div className="space-y-1">
                 <h4 className="text-xs font-bold text-neutral-300 uppercase tracking-widest">Interpretive Matrix</h4>
                 <p className="text-[12px] text-neutral-400 leading-relaxed font-light">
                   Dominant keyword <strong className="text-gold font-bold uppercase tracking-tight">"{selectedTopic?.keywords[0].word}"</strong> ({(selectedTopic?.keywords[0].weight * 100).toFixed(1)}% weight) suggests this topic cluster captures theological or institutional terminology most frequently found in <span className="text-neutral-200">{selectedTopic?.prevalence > 30 ? 'broad' : 'specialized'}</span> discourse sectors.
                 </p>
               </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};

export default TopicModelViz;
