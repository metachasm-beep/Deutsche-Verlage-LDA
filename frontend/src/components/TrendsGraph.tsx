import React, { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { motion } from 'framer-motion';
import { Calendar, RotateCcw, Eye } from 'lucide-react';
import clsx from 'clsx';

interface TrendsGraphProps {
  data: any[];
  publishers: string[];
  onYearClick?: (year: number) => void;
  selectedYear?: number | null;
  onResetYear?: () => void;
  compact?: boolean;
}

const PUBLISHER_COLORS: Record<string, string> = {
  'Verlag Herder': '#EAB308',
  'St. Benno Verlag': '#F59E0B',
  'SCM R. Brockhaus': '#FDE047',
  'Kösel-Verlag': '#38BDF8',
  'Gräfe und Unzer (GU)': '#06B6D4',
  'J. Kamphausen': '#2DD4BF',
  'Suhrkamp / Insel': '#FB7185',
  'C.H. Beck': '#A78BFA',
};

const FALLBACK_COLORS = [
  '#EAB308',
  '#38BDF8',
  '#FB7185',
  '#A78BFA',
  '#34D399',
  '#F59E0B',
  '#2DD4BF',
  '#F472B6',
];

export const TrendsGraph: React.FC<TrendsGraphProps> = ({
  data,
  publishers,
  onYearClick,
  selectedYear,
  onResetYear,
  compact = false,
}) => {
  const [hiddenPublishers, setHiddenPublishers] = useState<Record<string, boolean>>({});

  const togglePublisher = (pub: string) => {
    setHiddenPublishers((prev) => ({
      ...prev,
      [pub]: !prev[pub],
    }));
  };

  const showAllPublishers = () => {
    setHiddenPublishers({});
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const sorted = [...payload].sort((a: any, b: any) => (b.value || 0) - (a.value || 0));
      const total = sorted.reduce((acc: number, item: any) => acc + (Number(item.value) || 0), 0);

      return (
        <div className="bg-obsidian-900/95 backdrop-blur-xl border border-white/15 p-3 rounded-lg shadow-archival min-w-[220px]">
          <div className="flex items-center justify-between pb-1.5 mb-2 border-b border-white/10">
            <div className="flex items-center gap-1.5">
              <Calendar className="w-3 h-3 text-traditional" />
              <span className="font-serif font-bold text-sm text-parchment-50">
                Jahrgang {label}
              </span>
            </div>
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-parchment-200">
              Σ = {total}
            </span>
          </div>
          <div className="space-y-1">
            {sorted.map((entry: any, index: number) => (
              <div key={index} className="flex items-center justify-between gap-3 text-[11px]">
                <div className="flex items-center gap-1.5 truncate">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: entry.color }}
                  />
                  <span className="text-parchment-200 truncate max-w-[130px]">{entry.name}</span>
                </div>
                <span
                  className="font-mono font-semibold tabular-nums"
                  style={{ color: entry.color }}
                >
                  {entry.value}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-2 pt-1.5 border-t border-white/10 flex items-center justify-between text-[9px] font-mono text-traditional">
            <span>Click point to slice LDA</span>
            <span>→</span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="w-full h-full archival-panel rounded-xl p-4 sm:p-5 flex flex-col justify-between"
    >
      <div>
        {/* Header Bar */}
        <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-white/[0.07]">
          <div>
            <div className="flex items-center gap-1.5 mb-0.5">
              <span className="px-2 py-0.5 rounded bg-traditional/10 border border-traditional/30 font-mono text-[10px] uppercase tracking-widest text-traditional">
                Diachronic Slicer (2005–2026)
              </span>
              {selectedYear && (
                <span className="px-2 py-0.5 rounded bg-neoliberal/15 border border-neoliberal/40 font-mono text-[10px] text-neoliberal">
                  Active: {selectedYear}
                </span>
              )}
            </div>
            <h3 className="font-serif text-lg sm:text-xl font-bold text-parchment-50">
              Imprint Output & Temporal Slicing
            </h3>
          </div>

          <div className="flex items-center gap-1.5">
            {Object.values(hiddenPublishers).some(Boolean) && (
              <button
                onClick={showAllPublishers}
                className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono bg-white/5 hover:bg-white/10 text-parchment-200 border border-white/10 transition-colors cursor-pointer"
              >
                <Eye className="w-3 h-3" />
                All
              </button>
            )}
            {selectedYear && onResetYear && (
              <button
                onClick={onResetYear}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[10px] font-mono bg-traditional/15 hover:bg-traditional/25 text-traditional border border-traditional/40 transition-colors cursor-pointer"
              >
                <RotateCcw className="w-3 h-3" />
                Reset ({selectedYear})
              </button>
            )}
          </div>
        </div>

        {/* Interactive Publisher Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 mb-3">
          {publishers.map((pub, idx) => {
            const color = PUBLISHER_COLORS[pub] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length];
            const isHidden = !!hiddenPublishers[pub];
            return (
              <button
                key={pub}
                onClick={() => togglePublisher(pub)}
                className={clsx(
                  'inline-flex items-center gap-1.5 px-2 py-1 rounded border text-[10px] font-mono transition-all cursor-pointer',
                  isHidden
                    ? 'bg-obsidian-950/40 border-white/5 text-parchment-300/40 line-through'
                    : 'bg-obsidian-850/90 border-white/10 text-parchment-100 hover:border-white/25'
                )}
              >
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: isHidden ? '#52525B' : color }}
                />
                <span className="truncate max-w-[115px]">{pub}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Chart Container */}
      <div className={clsx('w-full', compact ? 'h-[265px]' : 'h-[340px]')}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 8, right: 14, left: -14, bottom: 4 }}
            onClick={(e: any) => {
              if (e && e.activeLabel && onYearClick) {
                onYearClick(Number(e.activeLabel));
              }
            }}
          >
            <CartesianGrid
              strokeDasharray="2 4"
              stroke="rgba(255,255,255,0.06)"
              vertical={true}
            />
            <XAxis
              dataKey="year"
              stroke="#6E6D68"
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
              dy={6}
              fontFamily="JetBrains Mono, monospace"
            />
            <YAxis
              stroke="#6E6D68"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              dx={-4}
              fontFamily="JetBrains Mono, monospace"
            />
            <Tooltip
              content={<CustomTooltip />}
              cursor={{
                stroke: '#EAB308',
                strokeWidth: 1,
                strokeDasharray: '4 4',
              }}
            />
            {selectedYear && (
              <ReferenceLine
                x={selectedYear}
                stroke="#EAB308"
                strokeWidth={2}
                strokeDasharray="3 3"
              />
            )}
            {publishers.map((pub, idx) => {
              if (hiddenPublishers[pub]) return null;
              const color = PUBLISHER_COLORS[pub] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length];
              return (
                <Line
                  key={pub}
                  type="monotone"
                  dataKey={pub}
                  name={pub}
                  stroke={color}
                  strokeWidth={2}
                  dot={{
                    r: 2.5,
                    fill: '#070709',
                    stroke: color,
                    strokeWidth: 1.5,
                  }}
                  activeDot={{
                    r: 5,
                    fill: color,
                    stroke: '#070709',
                    strokeWidth: 2,
                    cursor: 'pointer',
                    onClick: (_: any, payload: any) => {
                      if (payload && payload.payload && onYearClick) {
                        onYearClick(Number(payload.payload.year));
                      }
                    },
                  }}
                />
              );
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Footer Hint */}
      <div className="mt-2 pt-2 border-t border-white/[0.06] flex items-center justify-between text-[10px] font-mono text-parchment-300">
        <span>Click any year node to slice the posterior topic model</span>
        <span className="text-traditional">DNB SRU 2005–2026</span>
      </div>
    </motion.div>
  );
};
