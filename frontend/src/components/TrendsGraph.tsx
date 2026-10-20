import React, { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine
} from 'recharts';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface TrendsGraphProps {
  data: any[];
  onYearSelect: (year: number) => void;
  selectedYear?: number | null;
}

// High-contrast ideological palette mapped to German publishers
const PUBLISHER_PALETTE: Record<string, string> = {
  'Herder': '#EAB308',                     // Liturgical Gold (Traditional)
  'Evangelische Verlagsanstalt': '#F59E0B', // Warm Amber (Traditional)
  'Patmos': '#FDE047',                     // Ecclesiastical Yellow (Traditional)
  'Gütersloher Verlagshaus': '#38BDF8',    // Market Cyan (Neoliberal/Mainstream)
  'Kösel': '#22D3EE',                      // Therapeutic Teal (Neoliberal/Self-Help)
  'Suhrkamp': '#FB7185',                   // Critical Rose (Secular/Critical)
  'Alibri': '#F43F5E',                     // Secular Crimson (Critical)
  'Rowohlt': '#A78BFA'                     // Literary Violet (Critical/Mainstream)
};

const FALLBACK_COLORS = ['#EAB308', '#38BDF8', '#FB7185', '#34D399', '#A78BFA', '#F97316', '#22D3EE', '#F43F5E'];

const TrendsGraph: React.FC<TrendsGraphProps> = ({ data, onYearSelect, selectedYear }) => {
  const [hiddenPublishers, setHiddenPublishers] = useState<Record<string, boolean>>({});

  if (!data || data.length === 0) {
    return (
      <div className="h-72 flex items-center justify-center text-neutral-500 font-mono text-xs uppercase tracking-widest">
        Initializing Diachronic Telemetry...
      </div>
    );
  }

  const publishers = Object.keys(data[0]).filter(k => k !== 'year_clean');

  const togglePublisher = (pub: string) => {
    setHiddenPublishers(prev => ({ ...prev, [pub]: !prev[pub] }));
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full space-y-4"
    >
      {/* Interactive Publisher Filter Pills */}
      <div className="flex flex-wrap items-center gap-2 px-2">
        <span className="text-[10px] font-mono uppercase tracking-widest text-neutral-500 mr-1">
          Imprints:
        </span>
        {publishers.map((pub, idx) => {
          const color = PUBLISHER_PALETTE[pub] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length];
          const isHidden = !!hiddenPublishers[pub];
          return (
            <button
              key={pub}
              onClick={() => togglePublisher(pub)}
              className={clsx(
                "cursor-pointer px-2.5 py-1 rounded-md text-[10px] font-mono tracking-tight transition-all duration-200 border flex items-center gap-1.5",
                isHidden
                  ? "bg-neutral-950/40 border-neutral-800/50 text-neutral-600 opacity-50"
                  : "bg-neutral-900/80 border-white/10 text-neutral-200 hover:border-white/25"
              )}
            >
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: isHidden ? '#525252' : color }}
              />
              <span>{pub}</span>
            </button>
          );
        })}
      </div>

      {/* Main Temporal Line Chart */}
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            onClick={(e: any) => {
              if (e && e.activeLabel) {
                const yr = parseInt(e.activeLabel.toString(), 10);
                if (!isNaN(yr)) onYearSelect(yr);
              }
            }}
            margin={{ top: 10, right: 24, left: -10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis
              dataKey="year_clean"
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'var(--font-mono)' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'var(--font-mono)' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(13, 14, 18, 0.96)',
                border: '1px solid rgba(212, 175, 55, 0.35)',
                borderRadius: '12px',
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
                backdropFilter: 'blur(12px)'
              }}
              labelStyle={{ color: '#F8FAFC', fontWeight: 700, marginBottom: '4px' }}
            />
            {selectedYear && (
              <ReferenceLine
                x={selectedYear.toString()}
                stroke="#D4AF37"
                strokeDasharray="4 4"
                strokeWidth={2}
              />
            )}
            {publishers.map((pub, idx) => {
              if (hiddenPublishers[pub]) return null;
              const color = PUBLISHER_PALETTE[pub] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length];
              return (
                <Line
                  key={pub}
                  type="monotone"
                  dataKey={pub}
                  stroke={color}
                  strokeWidth={2.25}
                  dot={{ r: 3.5, fill: color, strokeWidth: 0 }}
                  activeDot={{ r: 6, stroke: '#070709', strokeWidth: 2, fill: color }}
                  animationDuration={900}
                />
              );
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
};

export default TrendsGraph;
