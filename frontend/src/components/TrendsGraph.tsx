import React, { useState } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { motion } from 'framer-motion';
import { Calendar, RotateCcw, Eye, Layers, TrendingUp } from 'lucide-react';
import clsx from 'clsx';

interface TrendsGraphProps {
  data: any[];
  publishers: string[];
  decadeBreakdown?: Record<string, Record<string, number>>;
  onYearClick?: (year: number) => void;
  selectedYear?: number | null;
  onDecadeClick?: (decade: number) => void;
  selectedDecade?: number | null;
  onResetTemporal?: () => void;
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
  '#60A5FA',
  '#FBBF24',
  '#C084FC',
  '#4ADE80',
];

const DECADE_COHORTS = [
  { label: '1970s', value: 1970 },
  { label: '1980s', value: 1980 },
  { label: '1990s', value: 1990 },
  { label: '2000s', value: 2000 },
  { label: '2010s', value: 2010 },
  { label: '2020s', value: 2020 },
];

export const TrendsGraph: React.FC<TrendsGraphProps> = ({
  data,
  publishers,
  decadeBreakdown = {},
  onYearClick,
  selectedYear,
  onDecadeClick,
  selectedDecade,
  onResetTemporal,
  compact = false,
}) => {
  const [hiddenPublishers, setHiddenPublishers] = useState<Record<string, boolean>>({});
  const [chartMode, setChartMode] = useState<'yearly_imprints' | 'decade_topics'>('yearly_imprints');

  const togglePublisher = (pub: string) => {
    setHiddenPublishers((prev) => ({
      ...prev,
      [pub]: !prev[pub],
    }));
  };

  const showAllPublishers = () => {
    setHiddenPublishers({});
  };

  // Transform decadeBreakdown = { "1970s": { "Topic 1": 12.3, ... }, ... } into Recharts array
  const decadeChartData = Object.entries(decadeBreakdown).map(([decLabel, topicMap]) => ({
    decade: decLabel,
    ...(topicMap || {}),
  }));

  const topicKeys =
    decadeChartData.length > 0
      ? Object.keys(decadeChartData[0]).filter((k) => k !== 'decade')
      : [];

  const CustomYearlyTooltip = ({ active, payload, label }: any) => {
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
            <span>Click point to slice LDA by Year</span>
            <span>→</span>
          </div>
        </div>
      );
    }
    return null;
  };

  const CustomDecadeTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const sorted = [...payload]
        .filter((p: any) => Number(p.value) > 0)
        .sort((a: any, b: any) => (b.value || 0) - (a.value || 0))
        .slice(0, 8);

      return (
        <div className="bg-obsidian-900/95 backdrop-blur-xl border border-white/15 p-3 rounded-lg shadow-archival min-w-[210px]">
          <div className="flex items-center justify-between pb-1.5 mb-2 border-b border-white/10">
            <span className="font-serif font-bold text-sm text-parchment-50">
              Decade Cohort: {label}
            </span>
            <span className="font-mono text-[10px] text-traditional">Topic Share %</span>
          </div>
          <div className="space-y-1">
            {sorted.map((entry: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between gap-3 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: entry.color || entry.fill }}
                  />
                  <span className="font-mono text-parchment-200">{entry.name}</span>
                </div>
                <span className="font-mono font-semibold tabular-nums text-parchment-50">
                  {Number(entry.value).toFixed(1)}%
                </span>
              </div>
            ))}
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
        {/* Header Bar with Mode Switcher (Yearly Imprints vs Decade Topic Shares) */}
        <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-2.5 border-b border-white/[0.07]">
          <div>
            <div className="flex items-center gap-1.5 mb-0.5">
              <span className="px-2 py-0.5 rounded bg-traditional/10 border border-traditional/30 font-mono text-[10px] uppercase tracking-widest text-traditional">
                Diachronic Monitor
              </span>
              {selectedYear && (
                <span className="px-2 py-0.5 rounded bg-neoliberal/15 border border-neoliberal/40 font-mono text-[10px] text-neoliberal">
                  Year: {selectedYear}
                </span>
              )}
              {selectedDecade && (
                <span className="px-2 py-0.5 rounded bg-critical/15 border border-critical/40 font-mono text-[10px] text-critical">
                  Decade: {selectedDecade}s
                </span>
              )}
            </div>
            <h3 className="font-serif text-lg sm:text-xl font-bold text-parchment-50">
              {chartMode === 'yearly_imprints'
                ? 'Annual Imprint Output & Temporal Slicer'
                : 'Decade Topic Share Trajectory (1970s–2020s)'}
            </h3>
          </div>

          <div className="flex items-center gap-1.5">
            {/* Sub-View Switcher */}
            <div className="flex items-center bg-obsidian-950 p-0.5 rounded-lg border border-white/10">
              <button
                onClick={() => setChartMode('yearly_imprints')}
                className={clsx(
                  'px-2 py-1 rounded-md font-mono text-[10px] transition-all cursor-pointer flex items-center gap-1',
                  chartMode === 'yearly_imprints'
                    ? 'bg-traditional text-obsidian-950 font-bold'
                    : 'text-parchment-300 hover:text-parchment-100'
                )}
              >
                <TrendingUp className="w-3 h-3" />
                <span>Yearly</span>
              </button>
              <button
                onClick={() => setChartMode('decade_topics')}
                className={clsx(
                  'px-2 py-1 rounded-md font-mono text-[10px] transition-all cursor-pointer flex items-center gap-1',
                  chartMode === 'decade_topics'
                    ? 'bg-traditional text-obsidian-950 font-bold'
                    : 'text-parchment-300 hover:text-parchment-100'
                )}
              >
                <Layers className="w-3 h-3" />
                <span>Decades</span>
              </button>
            </div>

            {(selectedYear || selectedDecade) && onResetTemporal && (
              <button
                onClick={onResetTemporal}
                className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono bg-traditional/15 hover:bg-traditional/25 text-traditional border border-traditional/40 transition-colors cursor-pointer"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Reset</span>
              </button>
            )}
          </div>
        </div>

        {/* Decade Cohort Quick-Slice Bar (1970s - 2020s) */}
        <div className="flex items-center justify-between gap-1.5 mb-2.5 pb-2 border-b border-white/[0.05] overflow-x-auto custom-scrollbar">
          <span className="font-mono text-[9px] uppercase tracking-widest text-parchment-300 shrink-0">
            Decade Slice:
          </span>
          <div className="flex items-center gap-1">
            {DECADE_COHORTS.map((dec) => {
              const isSelected = selectedDecade === dec.value;
              return (
                <button
                  key={dec.value}
                  onClick={() => onDecadeClick && onDecadeClick(dec.value)}
                  className={clsx(
                    'px-2 py-0.5 rounded font-mono text-[10px] border transition-all cursor-pointer',
                    isSelected
                      ? 'bg-traditional text-obsidian-950 border-traditional font-bold shadow-glow-gold'
                      : 'bg-obsidian-950/70 border-white/10 text-parchment-200 hover:border-traditional/40'
                  )}
                >
                  {dec.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Interactive Publisher Filter Pills (shown in Yearly Imprints mode) */}
        {chartMode === 'yearly_imprints' && (
          <div className="flex flex-wrap items-center gap-1.5 mb-2.5">
            {publishers.map((pub, idx) => {
              const color = PUBLISHER_COLORS[pub] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length];
              const isHidden = !!hiddenPublishers[pub];
              return (
                <button
                  key={pub}
                  onClick={() => togglePublisher(pub)}
                  className={clsx(
                    'inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-[10px] font-mono transition-all cursor-pointer',
                    isHidden
                      ? 'bg-obsidian-950/40 border-white/5 text-parchment-300/40 line-through'
                      : 'bg-obsidian-850/90 border-white/10 text-parchment-100 hover:border-white/25'
                  )}
                >
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: isHidden ? '#52525B' : color }}
                  />
                  <span className="truncate max-w-[110px]">{pub}</span>
                </button>
              );
            })}
            {Object.values(hiddenPublishers).some(Boolean) && (
              <button
                onClick={showAllPublishers}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-white/5 hover:bg-white/10 text-parchment-200 border border-white/10 cursor-pointer"
              >
                <Eye className="w-3 h-3" />
                All
              </button>
            )}
          </div>
        )}
      </div>

      {/* Main Chart Container */}
      <div className={clsx('w-full', compact ? 'h-[245px]' : 'h-[330px]')}>
        <ResponsiveContainer width="100%" height="100%">
          {chartMode === 'yearly_imprints' ? (
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
                content={<CustomYearlyTooltip />}
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
                const color =
                  PUBLISHER_COLORS[pub] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length];
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
                          const yVal = payload.payload.year ?? payload.payload.year_clean;
                          if (yVal) onYearClick(Number(yVal));
                        }
                      },
                    }}
                  />
                );
              })}
            </LineChart>
          ) : (
            <BarChart
              data={decadeChartData}
              margin={{ top: 8, right: 14, left: -14, bottom: 4 }}
              onClick={(e: any) => {
                if (e && e.activeLabel && onDecadeClick) {
                  const num = parseInt(String(e.activeLabel).replace(/\D/g, ''), 10);
                  if (!isNaN(num)) onDecadeClick(num);
                }
              }}
            >
              <CartesianGrid
                strokeDasharray="2 4"
                stroke="rgba(255,255,255,0.06)"
                vertical={false}
              />
              <XAxis
                dataKey="decade"
                stroke="#ECE8DF"
                fontSize={10}
                tickLine={false}
                axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                fontFamily="JetBrains Mono, monospace"
              />
              <YAxis
                stroke="#6E6D68"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${v}%`}
                fontFamily="JetBrains Mono, monospace"
              />
              <Tooltip content={<CustomDecadeTooltip />} />
              {topicKeys.map((tKey, idx) => (
                <Bar
                  key={tKey}
                  dataKey={tKey}
                  stackId="decadeStack"
                  fill={FALLBACK_COLORS[idx % FALLBACK_COLORS.length]}
                  fillOpacity={0.85}
                />
              ))}
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Footer Hint */}
      <div className="mt-2 pt-2 border-t border-white/[0.06] flex items-center justify-between text-[10px] font-mono text-parchment-300">
        <span>
          {chartMode === 'yearly_imprints'
            ? 'Click any year point or decade pill above to slice the posterior LDA model'
            : 'Stacked Topic Shares (1970s–2020s) computed from lda_model.decade_breakdown'}
        </span>
        <span className="text-traditional">Diachronic Engine Active</span>
      </div>
    </motion.div>
  );
};
