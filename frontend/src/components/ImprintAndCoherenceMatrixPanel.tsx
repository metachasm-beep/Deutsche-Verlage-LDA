import React from 'react';
import { TrendingUp } from 'lucide-react';
import clsx from 'clsx';
import type { CoherencePoint, PublisherArchetypeRow } from '../hooks/useLDA';

export interface ImprintAndCoherenceMatrixPanelProps {
  publisherArchetypes: PublisherArchetypeRow[];
  coherenceGrid: CoherencePoint[];
  numTopics: number;
  selectedPublishers: string[];
  ideologicalFilter: string | null;
  onTogglePublisher: (publisher: string, multiSelect?: boolean) => void;
  onSelectRegimeK: (k: number) => void;
  compactScroll?: boolean;
}

export const ImprintAndCoherenceMatrixPanel: React.FC<ImprintAndCoherenceMatrixPanelProps> = ({
  publisherArchetypes,
  coherenceGrid,
  numTopics,
  selectedPublishers,
  ideologicalFilter,
  onTogglePublisher,
  onSelectRegimeK,
  compactScroll = true,
}) => {
  const maxCv = coherenceGrid.length > 0 ? Math.max(...coherenceGrid.map((r) => r.c_v)) : 0;

  return (
    <div className="grid grid-cols-1 2xl:grid-cols-12 gap-4 items-stretch">
      {/* Left Cell: Publisher × Ideological Archetype Matrix */}
      <div className="2xl:col-span-7 archival-panel rounded-xl p-4 sm:p-5 flex flex-col justify-between">
        <div>
          <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-white/[0.07]">
            <div>
              <span className="font-mono text-[10px] uppercase tracking-widest text-traditional">
                Institutional Imprint Positioning
              </span>
              <h3 className="font-serif text-lg sm:text-xl font-bold text-parchment-50">
                Publisher × Ideological Archetype Matrix
              </h3>
            </div>
            <div className="flex items-center gap-2 font-mono text-[10px]">
              <span className="text-traditional">■ Trad</span>
              <span className="text-neoliberal">■ Neo</span>
              <span className="text-critical">■ Crit</span>
            </div>
          </div>

          <div
            className={clsx(
              'space-y-2.5',
              compactScroll && 'max-h-[320px] overflow-y-auto pr-1 custom-scrollbar'
            )}
          >
            {[...publisherArchetypes]
              .sort((a, b) => {
                if (!ideologicalFilter) return 0;
                const key = ideologicalFilter as 'Traditional' | 'Neoliberal' | 'Critical';
                return (b[key] ?? 0) - (a[key] ?? 0);
              })
              .map((item) => {
                const trad = item.Traditional ?? 0;
                const neo = item.Neoliberal ?? 0;
                const crit = item.Critical ?? 0;
                const isTrad = trad >= neo && trad >= crit;
                const isNeo = neo > trad && neo >= crit;
                const dominantLabel = isTrad
                  ? 'Traditional'
                  : isNeo
                  ? 'Neoliberal'
                  : 'Critical';
                const badgeClass = isTrad
                  ? 'bg-traditional/15 text-traditional border-traditional/30'
                  : isNeo
                  ? 'bg-neoliberal/15 text-neoliberal border-neoliberal/30'
                  : 'bg-critical/15 text-critical border-critical/30';

                const isPubActive = selectedPublishers.includes(item.publisher);
                const matchesRq = !ideologicalFilter || dominantLabel === ideologicalFilter;

                return (
                  <div
                    key={item.publisher}
                    onClick={() => onTogglePublisher(item.publisher, true)}
                    title="Click to isolate/toggle this Imprint in the active LDA sub-corpus"
                    className={clsx(
                      'p-2.5 rounded-lg border transition-all cursor-pointer',
                      isPubActive
                        ? 'bg-traditional/10 border-traditional shadow-glow-gold'
                        : matchesRq && ideologicalFilter
                        ? 'bg-obsidian-900 border-white/25'
                        : 'bg-obsidian-950/80 border-white/[0.06] hover:border-white/20',
                      !matchesRq && ideologicalFilter && 'opacity-50'
                    )}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="font-serif font-bold text-sm text-parchment-50 leading-snug break-words">
                          {isPubActive ? `✓ ${item.publisher}` : item.publisher}
                        </span>
                        <span
                          className={clsx(
                            'px-1.5 py-0.5 rounded border font-mono text-[9px] font-semibold shrink-0',
                            badgeClass
                          )}
                        >
                          {dominantLabel}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 font-mono text-[10px] tabular-nums shrink-0">
                        <span className="text-traditional">{trad}%</span>
                        <span className="text-neoliberal">{neo}%</span>
                        <span className="text-critical">{crit}%</span>
                      </div>
                    </div>
                    <div className="w-full h-2 rounded-full overflow-hidden flex bg-obsidian-900 p-0.5 gap-0.5">
                      <div
                        style={{ width: `${trad}%` }}
                        className="h-full bg-traditional rounded-l-full"
                      />
                      <div style={{ width: `${neo}%` }} className="h-full bg-neoliberal" />
                      <div
                        style={{ width: `${crit}%` }}
                        className="h-full bg-critical rounded-r-full"
                      />
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      </div>

      {/* Right Cell: Coherence Grid Validation Atlas */}
      <div className="2xl:col-span-5 archival-panel rounded-xl p-4 sm:p-5 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/[0.07]">
            <div>
              <span className="font-mono text-[10px] uppercase tracking-widest text-emerald-400">
                Röder et al. (2015) Validation
              </span>
              <h3 className="font-serif text-lg sm:text-xl font-bold text-parchment-50">
                Coherence Grid (C<sub>v</sub> vs. U<sub>Mass</sub>)
              </h3>
            </div>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>

          <div
            className={clsx(
              'overflow-x-auto',
              compactScroll && 'max-h-[320px] overflow-y-auto custom-scrollbar'
            )}
          >
            <table className="w-full text-left border-collapse font-mono text-[11px]">
              <thead>
                <tr className="border-b border-white/10 text-parchment-300 text-[9px] uppercase">
                  <th className="py-1.5 px-2">K</th>
                  <th className="py-1.5 px-2">Cv (NPMI)</th>
                  <th className="py-1.5 px-2">UMass</th>
                  <th className="py-1.5 px-2 text-right">Regime</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.05]">
                {coherenceGrid.map((row) => {
                  const isActive = row.k === numTopics;
                  const isPeak = row.c_v === maxCv;
                  return (
                    <tr
                      key={row.k}
                      onClick={() => onSelectRegimeK(row.k)}
                      className={clsx(
                        'cursor-pointer transition-colors',
                        isActive
                          ? 'bg-traditional/15 text-traditional font-bold'
                          : 'hover:bg-white/[0.04] text-parchment-200'
                      )}
                    >
                      <td className="py-1.5 px-2 tabular-nums">K={row.k}</td>
                      <td className="py-1.5 px-2 tabular-nums text-emerald-300">
                        {row.c_v.toFixed(4)}
                      </td>
                      <td className="py-1.5 px-2 tabular-nums text-neoliberal">
                        {row.u_mass.toFixed(3)}
                      </td>
                      <td className="py-1.5 px-2 text-right">
                        {isPeak ? (
                          <span className="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 text-[9px]">
                            Optimum
                          </span>
                        ) : row.k === 12 ? (
                          <span className="px-1.5 py-0.5 rounded bg-traditional/15 text-traditional text-[9px]">
                            Meso
                          </span>
                        ) : (
                          <span className="text-parchment-300 text-[9px]">
                            {row.k <= 8 ? 'Macro' : 'Micro'}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
