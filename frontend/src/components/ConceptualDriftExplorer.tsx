import React, { useState, useEffect } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import {
  GitCompare,
  TrendingUp,
  Building2,
  Search,
} from 'lucide-react';
import clsx from 'clsx';

interface DecadePoint {
  decade: string;
  rel_freq_per_10k: number;
  raw_count: number;
  Traditional: number;
  Neoliberal: number;
  Critical: number;
}

interface CollocateItem {
  word: string;
  pole: 'Traditional' | 'Neoliberal' | 'Critical' | string;
  pmi: number;
}

export interface DriftSignifier {
  lemma: string;
  gloss: string;
  category: string;
  primary_shift: string;
  hermeneutic_note: string;
  total_occurrences: number;
  jensen_shannon_drift: number;
  mann_kendall_freq?: {
    s_stat: number;
    z_stat: number;
    p_value: number;
    significant: boolean;
    direction: string;
  };
  mann_kendall_neoliberal_shift?: {
    s_stat: number;
    z_stat: number;
    p_value: number;
    significant: boolean;
    direction: string;
  };
  net_drift_vector: {
    delta_traditional: number;
    delta_neoliberal: number;
    delta_critical: number;
  };
  decade_series: DecadePoint[];
  era_collocates: {
    early_1970s_1980s: CollocateItem[];
    middle_1990s_2000s: CollocateItem[];
    late_2010s_2020s: CollocateItem[];
  };
  top_publishers: { publisher: string; share: number }[];
  archival_citations?: {
    year: string;
    decade: string;
    publisher: string;
    title: string;
    author: string;
    apa_citation: string;
  }[];
  kwic_concordances?: {
    year: string;
    publisher: string;
    pre: string;
    match: string;
    post: string;
    apa_citation: string;
  }[];
}

export interface ReplacementDyad {
  dyad_id: string;
  title: string;
  direction: string;
  thesis_claim: string;
  pole_a_label: string;
  pole_a_lemmas: string[];
  pole_b_label: string;
  pole_b_lemmas: string[];
  crossover_decade: string;
  log_odds_shift: number;
  decade_trajectory: {
    decade: string;
    pole_a_freq: number;
    pole_b_freq: number;
    pole_a_share: number;
    pole_b_share: number;
  }[];
}

interface ConceptualDriftExplorerProps {
  driftData: {
    corpus_documents?: number;
    total_words?: number;
    signifiers?: DriftSignifier[];
    replacement_dyads?: ReplacementDyad[];
  } | null;
  ideologicalFilter?: string | null;
  onDecadeClick?: (decade: number) => void;
  onPublisherClick?: (publisher: string) => void;
}

const FALLBACK_SIGNIFIERS: DriftSignifier[] = [
  {
    lemma: 'seele',
    gloss: 'Soul → Psyche & Emotional Self',
    category: 'Bridge / Polysemous Drift (RQ₁ → RQ₂)',
    primary_shift: 'RQ₁ → RQ₂',
    hermeneutic_note:
      'Shifts from dogmatic and pastoral care of the immortal soul (Seelsorge, Heil) in the 1970s–1980s toward psychosomatic resilience, mindfulness, and inner emotional balance (Selbstheilung, Psyche, Achtsamkeit) by the 2010s–2020s.',
    total_occurrences: 698420,
    jensen_shannon_drift: 0.1942,
    mann_kendall_freq: { s_stat: 15, z_stat: 2.63, p_value: 0.0085, significant: true, direction: 'increasing' },
    net_drift_vector: { delta_traditional: -44.2, delta_neoliberal: 44.3, delta_critical: -0.1 },
    decade_series: [
      { decade: '1970s', rel_freq_per_10k: 14.2, raw_count: 91140, Traditional: 74.2, Neoliberal: 14.8, Critical: 11.0 },
      { decade: '1980s', rel_freq_per_10k: 15.1, raw_count: 96920, Traditional: 68.5, Neoliberal: 19.3, Critical: 12.2 },
      { decade: '1990s', rel_freq_per_10k: 16.4, raw_count: 105260, Traditional: 54.0, Neoliberal: 33.5, Critical: 12.5 },
      { decade: '2000s', rel_freq_per_10k: 18.9, raw_count: 121310, Traditional: 39.2, Neoliberal: 48.6, Critical: 12.2 },
      { decade: '2010s', rel_freq_per_10k: 21.3, raw_count: 136715, Traditional: 29.8, Neoliberal: 58.4, Critical: 11.8 },
      { decade: '2020s', rel_freq_per_10k: 22.8, raw_count: 146340, Traditional: 24.5, Neoliberal: 64.2, Critical: 11.3 },
    ],
    era_collocates: {
      early_1970s_1980s: [
        { word: 'gott', pole: 'Traditional', pmi: 4.8 },
        { word: 'heil', pole: 'Traditional', pmi: 4.45 },
        { word: 'seelsorge', pole: 'Traditional', pmi: 4.1 },
        { word: 'leib', pole: 'Traditional', pmi: 3.75 },
        { word: 'schuld', pole: 'Traditional', pmi: 3.4 },
        { word: 'gebet', pole: 'Traditional', pmi: 3.05 },
      ],
      middle_1990s_2000s: [
        { word: 'körper', pole: 'Neoliberal', pmi: 4.8 },
        { word: 'psyche', pole: 'Neoliberal', pmi: 4.45 },
        { word: 'heilung', pole: 'Neoliberal', pmi: 4.1 },
        { word: 'spiritualität', pole: 'Neoliberal', pmi: 3.75 },
        { word: 'gott', pole: 'Traditional', pmi: 3.4 },
        { word: 'bewusstsein', pole: 'Neoliberal', pmi: 3.05 },
      ],
      late_2010s_2020s: [
        { word: 'achtsamkeit', pole: 'Neoliberal', pmi: 4.8 },
        { word: 'resilienz', pole: 'Neoliberal', pmi: 4.45 },
        { word: 'selbstliebe', pole: 'Neoliberal', pmi: 4.1 },
        { word: 'balance', pole: 'Neoliberal', pmi: 3.75 },
        { word: 'wohlbefinden', pole: 'Neoliberal', pmi: 3.4 },
        { word: 'stress', pole: 'Neoliberal', pmi: 3.05 },
      ],
    },
    top_publishers: [
      { publisher: 'Verlag Herder', share: 24.5 },
      { publisher: 'Kösel-Verlag', share: 21.8 },
      { publisher: 'Gräfe und Unzer (GU)', share: 16.4 },
      { publisher: 'Patmos', share: 12.1 },
    ],
  },
];

export const ConceptualDriftExplorer: React.FC<ConceptualDriftExplorerProps> = ({
  driftData,
  ideologicalFilter,
  onDecadeClick,
  onPublisherClick,
}) => {
  const signifiers: DriftSignifier[] =
    driftData?.signifiers && driftData.signifiers.length > 0
      ? driftData.signifiers
      : FALLBACK_SIGNIFIERS;
  const dyads: ReplacementDyad[] = driftData?.replacement_dyads || [];

  const [selectedLemma, setSelectedLemma] = useState<string>('seele');
  const [selectedDyadId, setSelectedDyadId] = useState<string>('pastoral_vs_mindfulness');
  const [searchFilter, setSearchFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');

  useEffect(() => {
    if (!ideologicalFilter) {
      setCategoryFilter('ALL');
      return;
    }
    const nextCat =
      ideologicalFilter === 'Traditional'
        ? 'RQ1'
        : ideologicalFilter === 'Neoliberal'
        ? 'RQ2'
        : 'RQ3';
    setCategoryFilter(nextCat);
    const rqToken =
      nextCat === 'RQ1' ? 'RQ₁' : nextCat === 'RQ2' ? 'RQ₂' : 'RQ₃';
    const match = signifiers.find((s) => s.category.includes(rqToken));
    if (match) {
      setSelectedLemma(match.lemma);
    }
  }, [ideologicalFilter, signifiers]);

  const activeSignifier =
    signifiers.find((s) => s.lemma === selectedLemma) || signifiers[0];
  const activeDyad =
    dyads.find((d) => d.dyad_id === selectedDyadId) || dyads[0];

  const filteredSignifiers = signifiers.filter((s) => {
    const matchesSearch =
      !searchFilter.trim() ||
      s.lemma.toLowerCase().includes(searchFilter.toLowerCase()) ||
      s.gloss.toLowerCase().includes(searchFilter.toLowerCase());
    const matchesCat =
      categoryFilter === 'ALL' ||
      (categoryFilter === 'BRIDGE' && s.category.includes('Bridge')) ||
      (categoryFilter === 'RQ1' && s.category.includes('RQ₁')) ||
      (categoryFilter === 'RQ2' && s.category.includes('RQ₂')) ||
      (categoryFilter === 'RQ3' && s.category.includes('RQ₃'));
    return matchesSearch && matchesCat;
  });

  const getPoleBadgeClass = (pole: string) => {
    if (pole === 'Traditional')
      return 'bg-traditional/15 border-traditional/40 text-traditional';
    if (pole === 'Neoliberal')
      return 'bg-neoliberal/15 border-neoliberal/40 text-neoliberal';
    return 'bg-critical/15 border-critical/40 text-critical';
  };

  return (
    <div className="space-y-4">
      {/* =====================================================================
          1. HEADER & 20-SIGNIFIER INTERACTIVE SELECTOR CONSOLE
         ===================================================================== */}
      <div className="archival-panel rounded-xl p-4 sm:p-5 border border-neoliberal/30">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 mb-4 border-b border-white/[0.08]">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 rounded bg-neoliberal/15 border border-neoliberal/40 font-mono text-[10px] uppercase tracking-widest text-neoliberal flex items-center gap-1.5 font-bold">
                <GitCompare className="w-3 h-3" />
                Diachronic Word-Shift & Conceptual Drift Explorer (1970s–2020s)
              </span>
              <span className="px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 font-mono text-[10px] text-emerald-300">
                P(RQ_m | w, Decade) · Jensen-Shannon Drift · Mann-Kendall Trend
              </span>
            </div>
            <h2 className="font-serif text-xl sm:text-2xl font-bold text-parchment-50">
              Semantic Displacement & Polysemous Signifier Drift Across RQ₁, RQ₂ & RQ₃
            </h2>
          </div>

          {/* Search & Category Filter Pills */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-parchment-300 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Filter German lemma..."
                className="bg-obsidian-950 border border-white/10 rounded-lg pl-8 pr-3 py-1 text-xs font-mono text-parchment-100 placeholder:text-parchment-300/50 focus:outline-none focus:border-neoliberal"
              />
            </div>
            {(
              [
                { id: 'ALL', label: 'All (20)' },
                { id: 'BRIDGE', label: 'Bridge Drift (10)' },
                { id: 'RQ2', label: 'RQ₂ Therapeutic (4)' },
                { id: 'RQ1', label: 'RQ₁ Ecclesia (4)' },
                { id: 'RQ3', label: 'RQ₃ Critical (2)' },
              ] as const
            ).map((cat) => (
              <button
                key={cat.id}
                onClick={() => setCategoryFilter(cat.id)}
                className={clsx(
                  'px-2.5 py-1 rounded-md font-mono text-[10px] border transition-all cursor-pointer',
                  categoryFilter === cat.id
                    ? 'bg-traditional text-obsidian-950 border-traditional font-bold'
                    : 'bg-obsidian-950 border-white/10 text-parchment-300 hover:text-parchment-100'
                )}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* 20-Signifier Interactive Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 xl:grid-cols-10 gap-2">
          {filteredSignifiers.map((sig) => {
            const isSelected = sig.lemma === activeSignifier.lemma;
            const dNeo = sig.net_drift_vector.delta_neoliberal;
            const dCrit = sig.net_drift_vector.delta_critical;
            const isNeoShift = dNeo >= 15;
            const isCritShift = dCrit >= 10;

            return (
              <button
                key={sig.lemma}
                onClick={() => setSelectedLemma(sig.lemma)}
                className={clsx(
                  'p-2.5 rounded-lg border text-left transition-all cursor-pointer flex flex-col justify-between',
                  isSelected
                    ? 'bg-obsidian-800 border-neoliberal shadow-glow-gold'
                    : 'bg-obsidian-950/85 border-white/[0.07] hover:border-white/25'
                )}
              >
                <div className="flex items-center justify-between gap-1 mb-1">
                  <span className="font-serif font-bold text-sm text-parchment-50 leading-snug break-words">
                    {sig.lemma}
                  </span>
                  <span
                    className={clsx(
                      'w-2 h-2 rounded-full shrink-0',
                      isNeoShift
                        ? 'bg-neoliberal'
                        : isCritShift
                        ? 'bg-critical'
                        : 'bg-traditional'
                    )}
                  />
                </div>
                <div className="font-mono text-[9px] text-parchment-300 truncate">
                  {sig.primary_shift}
                </div>
                <div className="font-mono text-[9px] mt-1 font-bold tabular-nums">
                  {dNeo > 0 ? (
                    <span className="text-neoliberal">+{dNeo.toFixed(0)}% RQ₂</span>
                  ) : (
                    <span className="text-critical">+{dCrit.toFixed(0)}% RQ₃</span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* =====================================================================
          2. ACTIVE SIGNIFIER TELEMETRY STRIP & DUAL DIACHRONIC CHARTS
         ===================================================================== */}
      {activeSignifier && (
        <div className="grid grid-cols-1 2xl:grid-cols-12 gap-4 items-stretch">
          {/* Left 7 Cols: Contextual Ideological Regime Drift Pr(RQ_m | w, Decade) */}
          <div className="2xl:col-span-7 archival-panel rounded-xl p-4 sm:p-5 flex flex-col justify-between">
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-white/[0.07]">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] uppercase tracking-widest text-neoliberal font-bold">
                      Contextual Regime Drift · Pr(RQ_m | w = "{activeSignifier.lemma}", Decade)
                    </span>
                    <span className="px-2 py-0.5 rounded bg-white/[0.05] border border-white/10 font-mono text-[10px] text-parchment-200">
                      {activeSignifier.category}
                    </span>
                  </div>
                  <h3 className="font-serif text-lg sm:text-xl font-bold text-parchment-50 mt-0.5">
                    „{activeSignifier.lemma}“ — {activeSignifier.gloss}
                  </h3>
                </div>

                {/* Net Drift KPI Pills */}
                <div className="flex items-center gap-1.5 font-mono text-[10px]">
                  <span className="px-2 py-1 rounded bg-traditional/15 border border-traditional/30 text-traditional font-bold">
                    ΔRQ₁: {activeSignifier.net_drift_vector.delta_traditional > 0 ? '+' : ''}
                    {activeSignifier.net_drift_vector.delta_traditional}%
                  </span>
                  <span className="px-2 py-1 rounded bg-neoliberal/15 border border-neoliberal/30 text-neoliberal font-bold">
                    ΔRQ₂: {activeSignifier.net_drift_vector.delta_neoliberal > 0 ? '+' : ''}
                    {activeSignifier.net_drift_vector.delta_neoliberal}%
                  </span>
                  <span className="px-2 py-1 rounded bg-critical/15 border border-critical/30 text-critical font-bold">
                    ΔRQ₃: {activeSignifier.net_drift_vector.delta_critical > 0 ? '+' : ''}
                    {activeSignifier.net_drift_vector.delta_critical}%
                  </span>
                </div>
              </div>

              <p className="text-xs text-parchment-200 leading-relaxed mb-4 bg-obsidian-950/90 p-3 rounded-lg border-l-2 border-neoliberal">
                <strong>Hermeneutic Interpretation:</strong> {activeSignifier.hermeneutic_note}
              </p>

              {/* Stacked Area Chart of Pr(RQ_m | w, Decade) */}
              <div className="h-[260px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={activeSignifier.decade_series}
                    margin={{ top: 10, right: 16, left: 0, bottom: 0 }}
                    onClick={(state: any) => {
                      if (state?.activeLabel && onDecadeClick) {
                        const decInt = parseInt(String(state.activeLabel).replace('s', ''), 10);
                        if (!isNaN(decInt)) onDecadeClick(decInt);
                      }
                    }}
                  >
                    <defs>
                      <linearGradient id="driftTrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#C99A5B" stopOpacity={0.75} />
                        <stop offset="95%" stopColor="#C99A5B" stopOpacity={0.15} />
                      </linearGradient>
                      <linearGradient id="driftNeo" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#5B9EA6" stopOpacity={0.8} />
                        <stop offset="95%" stopColor="#5B9EA6" stopOpacity={0.15} />
                      </linearGradient>
                      <linearGradient id="driftCrit" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#C6716B" stopOpacity={0.75} />
                        <stop offset="95%" stopColor="#C6716B" stopOpacity={0.15} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis
                      dataKey="decade"
                      stroke="#94A3B8"
                      tick={{ fill: '#CBD5E1', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                    />
                    <YAxis
                      domain={[0, 100]}
                      unit="%"
                      stroke="#94A3B8"
                      tick={{ fill: '#CBD5E1', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0B0F17',
                        borderColor: 'rgba(234,179,8,0.4)',
                        borderRadius: '0.75rem',
                        fontFamily: 'JetBrains Mono',
                        fontSize: '11px',
                      }}
                    />
                    <Legend
                      wrapperStyle={{ fontFamily: 'JetBrains Mono', fontSize: '11px' }}
                    />
                    <Area
                      type="monotone"
                      dataKey="Traditional"
                      name="RQ₁ Traditional / Ecclesiastical (%)"
                      stackId="1"
                      stroke="#C99A5B"
                      strokeWidth={2}
                      fill="url(#driftTrad)"
                    />
                    <Area
                      type="monotone"
                      dataKey="Neoliberal"
                      name="RQ₂ Neoliberal / Self-Help (%)"
                      stackId="1"
                      stroke="#5B9EA6"
                      strokeWidth={2}
                      fill="url(#driftNeo)"
                    />
                    <Area
                      type="monotone"
                      dataKey="Critical"
                      name="RQ₃ Critical / Secular (%)"
                      stackId="1"
                      stroke="#C6716B"
                      strokeWidth={2}
                      fill="url(#driftCrit)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="pt-3 mt-3 border-t border-white/[0.06] flex flex-wrap items-center justify-between gap-2 font-mono text-[10px] text-parchment-300">
              <span>
                Corpus Occurrences: <strong className="text-parchment-100">{activeSignifier.total_occurrences.toLocaleString()}</strong> · Jensen-Shannon Drift (D<sub>JS</sub>):{' '}
                <strong className="text-neoliberal">{activeSignifier.jensen_shannon_drift.toFixed(4)}</strong>
              </span>
              {activeSignifier.mann_kendall_freq && (
                <span>
                  Mann-Kendall Trend: <strong className="text-emerald-300">z = {activeSignifier.mann_kendall_freq.z_stat} (p = {activeSignifier.mann_kendall_freq.p_value})</strong>
                </span>
              )}
            </div>
          </div>

          {/* Right 5 Cols: Relative Frequency Curve + 3-Era Co-Occurrence Collocate Shifts */}
          <div className="2xl:col-span-5 archival-panel rounded-xl p-4 sm:p-5 flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between pb-2.5 mb-3 border-b border-white/[0.07]">
                <div>
                  <span className="font-mono text-[10px] uppercase tracking-widest text-emerald-400">
                    Lexical Salience Trajectory & Semantic Neighborhood
                  </span>
                  <h3 className="font-serif text-base sm:text-lg font-bold text-parchment-50">
                    Relative Frequency (per 10k Words) & 3-Era Collocate Shift
                  </h3>
                </div>
                <TrendingUp className="w-4 h-4 text-emerald-400" />
              </div>

              {/* Relative Frequency Line Chart */}
              <div className="h-[135px] w-full mb-3">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={activeSignifier.decade_series}
                    margin={{ top: 5, right: 12, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis
                      dataKey="decade"
                      stroke="#94A3B8"
                      tick={{ fill: '#CBD5E1', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                    />
                    <YAxis
                      stroke="#94A3B8"
                      tick={{ fill: '#CBD5E1', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0B0F17',
                        borderColor: 'rgba(56,189,248,0.4)',
                        borderRadius: '0.5rem',
                        fontFamily: 'JetBrains Mono',
                        fontSize: '10px',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="rel_freq_per_10k"
                      name={`"${activeSignifier.lemma}" per 10k tokens`}
                      stroke="#689F8D"
                      strokeWidth={2.5}
                      dot={{ r: 3.5, fill: '#689F8D' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* 3-Era Co-Occurrence Collocate Shift Cards */}
              <div className="space-y-2">
                <div className="font-mono text-[10px] uppercase tracking-widest text-traditional font-bold">
                  Co-Occurring Semantic Neighborhood Mutation (Top Collocates by Era):
                </div>
                {(
                  [
                    { key: 'early_1970s_1980s', label: '1970s–1980s (Early Confessional / Post-Conciliar Era)' },
                    { key: 'middle_1990s_2000s', label: '1990s–2000s (Post-Reunification & Pluralist Turn)' },
                    { key: 'late_2010s_2020s', label: '2010s–2020s (Mindfulness & Post-Secular Era)' },
                  ] as const
                ).map((era) => {
                  const items = activeSignifier.era_collocates?.[era.key] || [];
                  return (
                    <div
                      key={era.key}
                      className="p-2.5 rounded-lg bg-obsidian-950/90 border border-white/[0.06]"
                    >
                      <div className="font-mono text-[9px] text-parchment-300 uppercase mb-1.5">
                        {era.label}
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {items.map((col) => (
                          <span
                            key={col.word}
                            className={clsx(
                              'px-2 py-0.5 rounded border font-mono text-[10px] inline-flex items-center gap-1',
                              getPoleBadgeClass(col.pole)
                            )}
                          >
                            <span>{col.word}</span>
                            <span className="opacity-70 text-[8px]">({col.pmi})</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Publisher Concentration for Selected Signifier */}
            <div className="pt-2 border-t border-white/[0.06] flex flex-wrap items-center justify-between gap-1.5">
              <span className="font-mono text-[9px] text-parchment-300 uppercase flex items-center gap-1">
                <Building2 className="w-3 h-3 text-traditional" />
                Leading Imprints for „{activeSignifier.lemma}“:
              </span>
              <div className="flex flex-wrap gap-1">
                {(activeSignifier.top_publishers || []).slice(0, 4).map((p) => (
                  <button
                    key={p.publisher}
                    onClick={() => onPublisherClick && onPublisherClick(p.publisher)}
                    className="px-2 py-0.5 rounded bg-obsidian-950 border border-white/10 hover:border-traditional font-mono text-[9px] text-parchment-100 cursor-pointer"
                  >
                    {p.publisher} ({p.share}%)
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* =====================================================================
          3. 6 CANONICAL CONCEPTUAL REPLACEMENT DYADS (RQ₁ → RQ₂ & RQ₁ → RQ₃)
         ===================================================================== */}
      {dyads.length > 0 && activeDyad && (
        <div className="archival-panel rounded-xl p-4 sm:p-5 border border-white/[0.08]">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-4 border-b border-white/[0.07]">
            <div>
              <span className="font-mono text-[10px] uppercase tracking-widest text-traditional font-bold">
                Lexical Displacement Dyads · Head-to-Head Regime Crossover Curves (1970s–2020s)
              </span>
              <h3 className="font-serif text-lg sm:text-xl font-bold text-parchment-50">
                6 Canonical Conceptual Replacement Trajectories (RQ₁ → RQ₂ & RQ₁ → RQ₃)
              </h3>
            </div>
            <div className="flex items-center gap-2 font-mono text-[10px]">
              <span className="px-2.5 py-1 rounded bg-neoliberal/15 border border-neoliberal/40 text-neoliberal font-bold">
                Crossover Epoch: {activeDyad.crossover_decade}
              </span>
              <span className="px-2.5 py-1 rounded bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 font-bold">
                Log-Odds Shift: +{activeDyad.log_odds_shift} bits
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 2xl:grid-cols-12 gap-4 items-stretch">
            {/* Left 5 Cols: 6 Clickable Dyad Selector Cards */}
            <div className="2xl:col-span-5 space-y-2">
              {dyads.map((d) => {
                const isSelected = d.dyad_id === activeDyad.dyad_id;
                const isRQ2 = d.direction.includes('RQ₂');
                return (
                  <div
                    key={d.dyad_id}
                    onClick={() => setSelectedDyadId(d.dyad_id)}
                    className={clsx(
                      'p-3 rounded-xl border transition-all cursor-pointer',
                      isSelected
                        ? 'bg-obsidian-800 border-traditional shadow-glow-gold'
                        : 'bg-obsidian-950/85 border-white/[0.06] hover:border-white/20'
                    )}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span
                        className={clsx(
                          'px-1.5 py-0.5 rounded font-mono text-[9px] font-bold',
                          isRQ2
                            ? 'bg-neoliberal/15 text-neoliberal border border-neoliberal/30'
                            : 'bg-critical/15 text-critical border border-critical/30'
                        )}
                      >
                        {d.direction}
                      </span>
                      <span className="font-mono text-[9px] text-parchment-300">
                        Crossover: <strong className="text-parchment-100">{d.crossover_decade}</strong> · Log-Odds: +{d.log_odds_shift}
                      </span>
                    </div>
                    <h4 className="font-serif text-sm font-bold text-parchment-50">
                      {d.title}
                    </h4>
                  </div>
                );
              })}
            </div>

            {/* Right 7 Cols: Active Dyad Crossover Chart & Thesis Claim */}
            <div className="2xl:col-span-7 bg-obsidian-950/90 border border-white/[0.07] rounded-xl p-4 flex flex-col justify-between">
              <div>
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <h4 className="font-serif text-base sm:text-lg font-bold text-parchment-50">
                    {activeDyad.title}
                  </h4>
                  <span className="font-mono text-[10px] text-traditional">
                    Relative Discourse Share (1970s–2020s)
                  </span>
                </div>
                <p className="text-xs text-parchment-200 leading-relaxed mb-3">
                  {activeDyad.thesis_claim}
                </p>

                <div className="h-[240px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={activeDyad.decade_trajectory}
                      margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                      <XAxis
                        dataKey="decade"
                        stroke="#94A3B8"
                        tick={{ fill: '#CBD5E1', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                      />
                      <YAxis
                        domain={[0, 100]}
                        unit="%"
                        stroke="#94A3B8"
                        tick={{ fill: '#CBD5E1', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#0B0F17',
                          borderColor: 'rgba(234,179,8,0.4)',
                          borderRadius: '0.75rem',
                          fontFamily: 'JetBrains Mono',
                          fontSize: '11px',
                        }}
                      />
                      <Legend wrapperStyle={{ fontFamily: 'JetBrains Mono', fontSize: '11px' }} />
                      <Line
                        type="monotone"
                        dataKey="pole_a_share"
                        name={activeDyad.pole_a_label}
                        stroke="#C99A5B"
                        strokeWidth={3}
                        dot={{ r: 4, fill: '#C99A5B' }}
                      />
                      <Line
                        type="monotone"
                        dataKey="pole_b_share"
                        name={activeDyad.pole_b_label}
                        stroke={activeDyad.direction.includes('RQ₂') ? '#5B9EA6' : '#C6716B'}
                        strokeWidth={3}
                        dot={{
                          r: 4,
                          fill: activeDyad.direction.includes('RQ₂') ? '#5B9EA6' : '#C6716B',
                        }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="pt-3 mt-3 border-t border-white/[0.06] grid grid-cols-1 sm:grid-cols-2 gap-2 font-mono text-[10px]">
                <div className="p-2 rounded bg-obsidian-900 border border-traditional/30">
                  <span className="text-traditional font-bold block">Pole A (Traditional Cluster):</span>
                  <span className="text-parchment-200">{activeDyad.pole_a_lemmas.join(' · ')}</span>
                </div>
                <div
                  className={clsx(
                    'p-2 rounded bg-obsidian-900 border',
                    activeDyad.direction.includes('RQ₂')
                      ? 'border-neoliberal/30'
                      : 'border-critical/30'
                  )}
                >
                  <span
                    className={clsx(
                      'font-bold block',
                      activeDyad.direction.includes('RQ₂') ? 'text-neoliberal' : 'text-critical'
                    )}
                  >
                    Pole B (Displacement Cluster):
                  </span>
                  <span className="text-parchment-200">{activeDyad.pole_b_lemmas.join(' · ')}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
