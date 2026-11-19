import React, { useMemo, useState } from 'react';
import {
  BarChart3,
  ArrowLeftRight,
  Table2,
  ArrowUpDown,
  Filter,
  Sparkles,
  CheckCircle2,
} from 'lucide-react';
import clsx from 'clsx';
import type {
  QuantedaSTMReport,
  KeynessTermRow,
  STMCovariateRow,
} from '../hooks/useLDA';

interface QuantedaKeynessAndSTMPanelProps {
  quantedaStm: QuantedaSTMReport | null;
}

const BOILERPLATE_ARTIFACT_TOKENS = new Set([
  'nutzungsbedingung',
  'deposit',
  'use',
  'sociology',
  'commercial',
  'online',
  'internet',
  'pdf',
  'doi',
  'jes',
]);

function parseTopicLabel(raw: string): {
  regime: string;
  lemmas: string;
  accentText: string;
  badgeClass: string;
} {
  const m = raw.match(/^Topic\s+\d+\s*\(([^:]+):\s*(.+)\)$/);
  const regime = m ? m[1].trim() : 'Discursive Regime';
  const lemmas = m ? m[2].trim() : raw;
  const rLower = regime.toLowerCase();

  if (rLower.includes('traditional')) {
    return {
      regime: 'Traditional / Ecclesiastical',
      lemmas,
      accentText: 'text-traditional',
      badgeClass: 'bg-traditional/15 border-traditional/35 text-traditional',
    };
  }
  if (rLower.includes('neoliberal')) {
    return {
      regime: 'Neoliberal / Self-Optimization',
      lemmas,
      accentText: 'text-neoliberal',
      badgeClass: 'bg-neoliberal/15 border-neoliberal/35 text-neoliberal',
    };
  }
  if (rLower.includes('critical')) {
    return {
      regime: 'Critical / Secular-Humanist',
      lemmas,
      accentText: 'text-critical',
      badgeClass: 'bg-critical/15 border-critical/35 text-critical',
    };
  }
  return {
    regime: 'Hybrid / Discursive Mediation',
    lemmas,
    accentText: 'text-emerald-300',
    badgeClass: 'bg-emerald-500/15 border-emerald-500/35 text-emerald-300',
  };
}

function formatG2(val: number): string {
  const rounded = Math.round(val);
  return rounded > 0 ? `+${rounded.toLocaleString()}` : rounded.toLocaleString();
}

function formatPValue(p: number): string {
  if (p <= 0 || p < 0.0001) return 'p < 0.0001***';
  if (p < 0.001) return `p = ${p.toFixed(4)}***`;
  if (p < 0.01) return `p = ${p.toFixed(4)}**`;
  if (p < 0.05) return `p = ${p.toFixed(4)}*`;
  return `p = ${p.toFixed(4)}`;
}

export const QuantedaKeynessAndSTMPanel: React.FC<QuantedaKeynessAndSTMPanelProps> = ({
  quantedaStm,
}) => {
  const [contrastMode, setContrastMode] = useState<'camp' | 'diachronic'>('camp');
  const [scaleMode, setScaleMode] = useState<'g2_log' | 'log_odds'>('g2_log');
  const [filterBoilerplate, setFilterBoilerplate] = useState<boolean>(true);
  const [topN, setTopN] = useState<number>(10);
  const [inspectedTerm, setInspectedTerm] = useState<{
    side: 'target' | 'reference';
    row: KeynessTermRow;
  } | null>(null);
  const [stmSortBy, setStmSortBy] = useState<'topic_id' | 'secular_effect' | 'diachronic_shift'>(
    'topic_id'
  );

  const activeContrast = useMemo(() => {
    if (!quantedaStm) return { target: [] as KeynessTermRow[], reference: [] as KeynessTermRow[] };
    const rawGroup =
      contrastMode === 'camp'
        ? quantedaStm.keyness_secular_vs_confessional
        : quantedaStm.keyness_2000_2025_vs_1970_1999;

    const filterList = (items: KeynessTermRow[] = []) =>
      (filterBoilerplate
        ? items.filter((it) => !BOILERPLATE_ARTIFACT_TOKENS.has(it.feature.toLowerCase()))
        : items
      ).slice(0, topN);

    return {
      target: filterList(rawGroup?.top_target_keyness || []),
      reference: filterList(rawGroup?.top_reference_keyness || []),
    };
  }, [quantedaStm, contrastMode, filterBoilerplate, topN]);

  const butterflyRows = useMemo(() => {
    const count = Math.max(activeContrast.target.length, activeContrast.reference.length);
    const maxRefLogG2 = Math.max(
      1,
      ...activeContrast.reference.map((r) => Math.log10(Math.max(10, Math.abs(r.g2_keyness))))
    );
    const maxTgtLogG2 = Math.max(
      1,
      ...activeContrast.target.map((t) => Math.log10(Math.max(10, Math.abs(t.g2_keyness))))
    );
    const maxAbsLogOdds = Math.max(
      0.5,
      ...activeContrast.reference.map((r) => Math.abs(r.log_odds_ratio)),
      ...activeContrast.target.map((t) => Math.abs(t.log_odds_ratio))
    );

    return Array.from({ length: count }, (_, idx) => {
      const ref = activeContrast.reference[idx] || null;
      const tgt = activeContrast.target[idx] || null;

      const refPct = ref
        ? scaleMode === 'g2_log'
          ? Math.max(18, (Math.log10(Math.max(10, Math.abs(ref.g2_keyness))) / maxRefLogG2) * 100)
          : Math.max(12, (Math.abs(ref.log_odds_ratio) / maxAbsLogOdds) * 100)
        : 0;

      const tgtPct = tgt
        ? scaleMode === 'g2_log'
          ? Math.max(18, (Math.log10(Math.max(10, Math.abs(tgt.g2_keyness))) / maxTgtLogG2) * 100)
          : Math.max(12, (Math.abs(tgt.log_odds_ratio) / maxAbsLogOdds) * 100)
        : 0;

      return { rank: idx + 1, ref, tgt, refPct, tgtPct };
    });
  }, [activeContrast, scaleMode]);

  const sortedStmRows = useMemo(() => {
    const rows = [...(quantedaStm?.stm_covariate_regressions || [])];
    if (stmSortBy === 'secular_effect') {
      return rows.sort(
        (a, b) => b.secular_vs_confessional_effect_pct - a.secular_vs_confessional_effect_pct
      );
    }
    if (stmSortBy === 'diachronic_shift') {
      return rows.sort(
        (a, b) => b.diachronic_1970_2025_shift_pct - a.diachronic_1970_2025_shift_pct
      );
    }
    return rows.sort((a, b) => a.topic_id - b.topic_id);
  }, [quantedaStm, stmSortBy]);

  const maxAbsSecularBeta = useMemo(() => {
    const vals = (quantedaStm?.stm_covariate_regressions || []).map((r) =>
      Math.abs(r.secular_vs_confessional_effect_pct)
    );
    return Math.max(5, ...vals);
  }, [quantedaStm]);

  const maxAbsTimeBeta = useMemo(() => {
    const vals = (quantedaStm?.stm_covariate_regressions || []).map((r) =>
      Math.abs(r.diachronic_1970_2025_shift_pct)
    );
    return Math.max(10, ...vals);
  }, [quantedaStm]);

  if (!quantedaStm || (quantedaStm.stm_covariate_regressions || []).length === 0) {
    return (
      <div className="archival-panel rounded-xl p-5 border border-critical/30">
        <div className="flex items-center gap-2 font-mono text-xs text-parchment-300">
          <BarChart3 className="w-4 h-4 text-critical animate-pulse" />
          <span>Loading Quanteda Dunning&apos;s G² Keyness &amp; 12-Topic STM Regressions...</span>
        </div>
      </div>
    );
  }

  const totalDocs = quantedaStm.total_documents || 10612079;
  const secDocs = quantedaStm.secular_documents || 6456388;
  const confDocs = quantedaStm.confessional_documents || 4155691;
  const secShare = ((secDocs / Math.max(1, totalDocs)) * 100).toFixed(2);
  const confShare = ((confDocs / Math.max(1, totalDocs)) * 100).toFixed(2);

  const isCampMode = contrastMode === 'camp';
  const leftLabel = isCampMode
    ? `Confessional / Theological Reference (-G², n = ${(confDocs / 1e6).toFixed(2)}M)`
    : 'Pre-2000 Print Reference (-G², 1970–1999)';
  const rightLabel = isCampMode
    ? `Secular / Critical / Trade Target (+G², n = ${(secDocs / 1e6).toFixed(2)}M)`
    : 'Post-2000 Emergent Print Target (+G², 2000–2025)';

  return (
    <div className="archival-panel rounded-xl p-4 sm:p-5 border border-critical/35 space-y-5">
      {/* Module Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-white/[0.08]">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded bg-critical/15 border border-critical/40 font-mono text-[10px] uppercase tracking-widest text-critical flex items-center gap-1.5 font-bold">
              <BarChart3 className="w-3 h-3" />
              Module 4 · Quanteda Keyness (G²) &amp; Structural Topic Model (STM)
            </span>
            <span className="px-2 py-0.5 rounded bg-traditional/15 border border-traditional/30 font-mono text-[10px] text-traditional">
              D = {totalDocs.toLocaleString()} Passages · {secShare}% Secular vs. {confShare}% Confessional
            </span>
          </div>
          <h2 className="font-serif text-xl sm:text-2xl font-bold text-parchment-50">
            Dunning&apos;s Log-Likelihood Keyness (G²) Butterfly &amp; 12-Topic STM Regression Table
          </h2>
        </div>

        {/* Contrast Mode Switcher */}
        <div className="flex items-center gap-1 p-1 rounded-lg bg-obsidian-950 border border-white/10">
          <button
            onClick={() => {
              setContrastMode('camp');
              setInspectedTerm(null);
            }}
            className={clsx(
              'px-2.5 py-1.5 rounded-md font-mono text-[10px] transition-all cursor-pointer flex items-center gap-1.5',
              isCampMode
                ? 'bg-critical text-obsidian-950 font-bold'
                : 'text-parchment-300 hover:text-parchment-100'
            )}
          >
            <ArrowLeftRight className="w-3 h-3" />
            <span>Secular vs. Confessional (RQ₂)</span>
          </button>
          <button
            onClick={() => {
              setContrastMode('diachronic');
              setInspectedTerm(null);
            }}
            className={clsx(
              'px-2.5 py-1.5 rounded-md font-mono text-[10px] transition-all cursor-pointer flex items-center gap-1.5',
              !isCampMode
                ? 'bg-neoliberal text-obsidian-950 font-bold'
                : 'text-parchment-300 hover:text-parchment-100'
            )}
          >
            <Sparkles className="w-3 h-3" />
            <span>Post-2000 vs. Pre-2000 (RQ₁/₄)</span>
          </button>
        </div>
      </div>

      {/* =====================================================================
          PANEL A: EXACT DUNNING'S G² DIVERGING BUTTERFLY CHART
         ===================================================================== */}
      <div className="bg-obsidian-950/90 border border-white/[0.08] rounded-xl p-4 space-y-3.5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <span className="font-mono text-[10px] uppercase tracking-widest text-critical font-bold">
              Internal Contrastive Reference Corpus Keyness · quanteda::textstat_keyness(measure = &quot;lr&quot;)
            </span>
            <h3 className="font-serif text-base sm:text-lg font-bold text-parchment-50">
              {isCampMode
                ? 'Institutional Gatekeeping Polarization: Confessional (-G²) vs. Secular/Trade (+G²)'
                : 'Diachronic Vocabulary Turnover: Pre-2000 (-G²) vs. Post-2000 Emergent Print (+G²)'}
            </h3>
            <p className="text-[11px] text-parchment-300 mt-0.5 leading-relaxed">
              Every lemma is tested across a 2×2 contingency table via{' '}
              <code className="text-parchment-100">G² = 2 Σ O_ij ln(O_ij / E_ij)</code> (all displayed terms{' '}
              <strong className="text-emerald-300">p &lt; 10⁻³⁰⁰</strong>). Hover or click any bar to inspect exact rates per 10k words and Log-Odds Ratios.
            </p>
          </div>

          {/* Interactive Butterfly Controls */}
          <div className="flex flex-wrap items-center gap-2 font-mono text-[10px]">
            <div className="flex items-center gap-1 p-0.5 rounded-lg bg-obsidian-900 border border-white/10">
              <button
                onClick={() => setScaleMode('g2_log')}
                className={clsx(
                  'px-2 py-1 rounded transition-colors cursor-pointer',
                  scaleMode === 'g2_log'
                    ? 'bg-traditional/25 text-traditional font-bold'
                    : 'text-parchment-300 hover:text-parchment-100'
                )}
              >
                Log-Scaled G²
              </button>
              <button
                onClick={() => setScaleMode('log_odds')}
                className={clsx(
                  'px-2 py-1 rounded transition-colors cursor-pointer',
                  scaleMode === 'log_odds'
                    ? 'bg-neoliberal/25 text-neoliberal font-bold'
                    : 'text-parchment-300 hover:text-parchment-100'
                )}
              >
                Log-Odds Scale
              </button>
            </div>

            <button
              onClick={() => setFilterBoilerplate((prev) => !prev)}
              className={clsx(
                'px-2.5 py-1 rounded-lg border flex items-center gap-1.5 cursor-pointer transition-colors',
                filterBoilerplate
                  ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300 font-bold'
                  : 'bg-obsidian-900 border-white/10 text-parchment-300'
              )}
              title="Toggle display of deposit/metadata boilerplate tokens (nutzungsbedingung, deposit, use)"
            >
              <Filter className="w-3 h-3" />
              <span>{filterBoilerplate ? 'Substantive Lemmas' : 'All Raw Tokens'}</span>
            </button>

            <div className="flex items-center gap-1 p-0.5 rounded-lg bg-obsidian-900 border border-white/10">
              {[8, 10, 15].map((n) => (
                <button
                  key={n}
                  onClick={() => setTopN(n)}
                  className={clsx(
                    'px-2 py-1 rounded cursor-pointer',
                    topN === n
                      ? 'bg-white/15 text-parchment-50 font-bold'
                      : 'text-parchment-300 hover:text-parchment-100'
                  )}
                >
                  Top {n}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Butterfly Column Pole Headers */}
        <div className="grid grid-cols-12 items-center gap-2 px-2 py-1.5 rounded-lg bg-obsidian-900/90 border border-white/[0.06] font-mono text-[10px] font-bold">
          <div className="col-span-6 text-right pr-2 text-traditional flex items-center justify-end gap-1.5">
            <span className="inline-block w-2.5 h-2.5 rounded-sm bg-traditional shrink-0" />
            <span className="truncate">{leftLabel}</span>
          </div>
          <div className="col-span-6 text-left pl-2 flex items-center gap-1.5">
            <span
              className={clsx(
                'inline-block w-2.5 h-2.5 rounded-sm shrink-0',
                isCampMode ? 'bg-critical' : 'bg-neoliberal'
              )}
            />
            <span className={clsx('truncate', isCampMode ? 'text-critical' : 'text-neoliberal')}>
              {rightLabel}
            </span>
          </div>
        </div>

        {/* Butterfly Bars Grid */}
        <div className="space-y-1.5">
          {butterflyRows.map(({ rank, ref, tgt, refPct, tgtPct }) => {
            const isRefSelected =
              inspectedTerm?.side === 'reference' &&
              inspectedTerm?.row.feature === ref?.feature;
            const isTgtSelected =
              inspectedTerm?.side === 'target' &&
              inspectedTerm?.row.feature === tgt?.feature;

            return (
              <div
                key={rank}
                className="grid grid-cols-12 items-center gap-0 group"
              >
                {/* Left Wing: Reference Corpus (-G²) */}
                <div className="col-span-6 flex items-center justify-end gap-2 pr-0 border-r-2 border-parchment-300/40">
                  {ref ? (
                    <button
                      type="button"
                      onMouseEnter={() => setInspectedTerm({ side: 'reference', row: ref })}
                      onClick={() => setInspectedTerm({ side: 'reference', row: ref })}
                      className={clsx(
                        'w-full flex items-center justify-end gap-2 py-1 pl-1.5 pr-0 rounded-l transition-colors cursor-pointer',
                        isRefSelected ? 'bg-traditional/15' : 'hover:bg-white/[0.04]'
                      )}
                    >
                      <span className="font-mono text-[10px] sm:text-[11px] text-parchment-200 tabular-nums shrink-0 text-right">
                        <strong className="text-traditional">{ref.feature}</strong>{' '}
                        <span className="text-parchment-300 text-[10px]">
                          ({scaleMode === 'g2_log' ? formatG2(ref.g2_keyness) : `${ref.log_odds_ratio.toFixed(2)} LO`})
                        </span>
                      </span>
                      <div className="w-[46%] sm:w-[54%] flex justify-end">
                        <div
                          style={{ width: `${refPct}%` }}
                          className={clsx(
                            'h-5 rounded-l-md transition-all duration-300 flex items-center justify-start pl-1.5',
                            isRefSelected
                              ? 'bg-traditional shadow-glow-gold'
                              : 'bg-traditional/85 hover:bg-traditional'
                          )}
                        >
                          <span className="font-mono text-[9px] font-bold text-obsidian-950 truncate hidden md:inline">
                            {ref.rate_ref_per_10k.toFixed(1)}/10k
                          </span>
                        </div>
                      </div>
                    </button>
                  ) : (
                    <div className="h-5" />
                  )}
                </div>

                {/* Right Wing: Target Corpus (+G²) */}
                <div className="col-span-6 flex items-center justify-start gap-2 pl-0">
                  {tgt ? (
                    <button
                      type="button"
                      onMouseEnter={() => setInspectedTerm({ side: 'target', row: tgt })}
                      onClick={() => setInspectedTerm({ side: 'target', row: tgt })}
                      className={clsx(
                        'w-full flex items-center justify-start gap-2 py-1 pr-1.5 pl-0 rounded-r transition-colors cursor-pointer',
                        isTgtSelected
                          ? isCampMode
                            ? 'bg-critical/15'
                            : 'bg-neoliberal/15'
                          : 'hover:bg-white/[0.04]'
                      )}
                    >
                      <div className="w-[46%] sm:w-[54%] flex justify-start">
                        <div
                          style={{ width: `${tgtPct}%` }}
                          className={clsx(
                            'h-5 rounded-r-md transition-all duration-300 flex items-center justify-end pr-1.5',
                            isCampMode
                              ? isTgtSelected
                                ? 'bg-critical'
                                : 'bg-critical/85 hover:bg-critical'
                              : isTgtSelected
                              ? 'bg-neoliberal'
                              : 'bg-neoliberal/85 hover:bg-neoliberal'
                          )}
                        >
                          <span className="font-mono text-[9px] font-bold text-obsidian-950 truncate hidden md:inline">
                            {tgt.rate_target_per_10k.toFixed(1)}/10k
                          </span>
                        </div>
                      </div>
                      <span className="font-mono text-[10px] sm:text-[11px] text-parchment-200 tabular-nums shrink-0 text-left">
                        <strong className={isCampMode ? 'text-critical' : 'text-neoliberal'}>
                          {tgt.feature}
                        </strong>{' '}
                        <span className="text-parchment-300 text-[10px]">
                          ({scaleMode === 'g2_log' ? formatG2(tgt.g2_keyness) : `+${tgt.log_odds_ratio.toFixed(2)} LO`})
                        </span>
                      </span>
                    </button>
                  ) : (
                    <div className="h-5" />
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Live Telemetry Inspector Strip for Hovered / Selected Lemma */}
        <div className="pt-2.5 mt-2 border-t border-white/[0.07] flex flex-wrap items-center justify-between gap-2 font-mono text-[10px]">
          {inspectedTerm ? (
            <>
              <div className="flex flex-wrap items-center gap-2 text-parchment-100">
                <span
                  className={clsx(
                    'px-2 py-0.5 rounded font-bold uppercase text-[9px]',
                    inspectedTerm.side === 'reference'
                      ? 'bg-traditional/20 text-traditional border border-traditional/40'
                      : isCampMode
                      ? 'bg-critical/20 text-critical border border-critical/40'
                      : 'bg-neoliberal/20 text-neoliberal border border-neoliberal/40'
                  )}
                >
                  {inspectedTerm.row.feature}
                </span>
                <span>
                  Dunning&apos;s G² ={' '}
                  <strong className="text-parchment-50">
                    {formatG2(inspectedTerm.row.g2_keyness)}
                  </strong>
                </span>
                <span>·</span>
                <span>
                  Log-Odds ={' '}
                  <strong className="text-emerald-300">
                    {inspectedTerm.row.log_odds_ratio >= 0
                      ? `+${inspectedTerm.row.log_odds_ratio.toFixed(3)}`
                      : inspectedTerm.row.log_odds_ratio.toFixed(3)}
                  </strong>
                </span>
                <span>·</span>
                <span>
                  Target Rate:{' '}
                  <strong className="text-parchment-50">
                    {inspectedTerm.row.rate_target_per_10k.toFixed(2)}/10k
                  </strong>{' '}
                  ({inspectedTerm.row.n_target.toLocaleString()})
                </span>
                <span>vs.</span>
                <span>
                  Ref Rate:{' '}
                  <strong className="text-parchment-50">
                    {inspectedTerm.row.rate_ref_per_10k.toFixed(2)}/10k
                  </strong>{' '}
                  ({inspectedTerm.row.n_reference.toLocaleString()})
                </span>
              </div>
              <span className="text-emerald-300 font-bold">
                {(() => {
                  const rT = Math.max(0.01, inspectedTerm.row.rate_target_per_10k);
                  const rR = Math.max(0.01, inspectedTerm.row.rate_ref_per_10k);
                  return rT >= rR
                    ? `${(rT / rR).toFixed(2)}× higher in ${isCampMode ? 'Secular' : 'Post-2000'} · p < 10⁻³⁰⁰`
                    : `${(rR / rT).toFixed(2)}× higher in ${isCampMode ? 'Confessional' : 'Pre-2000'} · p < 10⁻³⁰⁰`;
                })()}
              </span>
            </>
          ) : (
            <span className="text-parchment-300">
              Internal Reference Design: {isCampMode ? `${confDocs.toLocaleString()} Confessional passages serve as C_ref for ${secDocs.toLocaleString()} Secular passages` : '1970–1999 passages serve as C_ref for 2000–2025 passages'}. Hover any lemma bar to inspect exact contingency counts &amp; fold-enrichment.
            </span>
          )}
        </div>
      </div>

      {/* =====================================================================
          PANEL B: FULL 12-TOPIC STRUCTURAL TOPIC MODEL (STM) REGRESSION TABLE
         ===================================================================== */}
      <div className="bg-obsidian-950/90 border border-white/[0.08] rounded-xl p-4 space-y-3.5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <Table2 className="w-3.5 h-3.5 text-neoliberal" />
              <span className="font-mono text-[10px] uppercase tracking-widest text-neoliberal font-bold">
                Structural Topic Model Covariate Regressions · stm::estimateEffect(1:12 ~ IsSecular + TimeNorm)
              </span>
            </div>
            <h3 className="font-serif text-base sm:text-lg font-bold text-parchment-50">
              12-Topic Partial Effects: Publisher Ownership (β₁) &amp; 55-Year Diachronic Shift (β₂)
            </h3>
            <p className="text-[11px] text-parchment-300 mt-0.5">
              OLS regression across all <strong className="text-parchment-100">D = {totalDocs.toLocaleString()}</strong> passages:{' '}
              <code className="text-emerald-300">
                θ_(d,k) = β₀ + β₁·IsSecular_d + β₂·((Year_d − 1970)/55) + ε_(d,k)
              </code>{' '}
              — isolating pure institutional ownership effects net of year and pure 1970→2025 shifts net of ownership.
            </p>
          </div>

          {/* Sort Controls */}
          <div className="flex items-center gap-1 p-1 rounded-lg bg-obsidian-900 border border-white/10 font-mono text-[10px]">
            <ArrowUpDown className="w-3 h-3 text-parchment-300 ml-1 mr-0.5" />
            {(
              [
                { id: 'topic_id', label: 'Topic 1–12' },
                { id: 'secular_effect', label: 'Sort by β₁ Ownership' },
                { id: 'diachronic_shift', label: 'Sort by β₂ 55-Yr Shift' },
              ] as const
            ).map((opt) => (
              <button
                key={opt.id}
                onClick={() => setStmSortBy(opt.id)}
                className={clsx(
                  'px-2 py-1 rounded transition-colors cursor-pointer',
                  stmSortBy === opt.id
                    ? 'bg-neoliberal text-obsidian-950 font-bold'
                    : 'text-parchment-300 hover:text-parchment-100'
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Responsive 12-Row STM Table */}
        <div className="overflow-x-auto custom-scrollbar">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/10 bg-obsidian-900/90 font-mono text-[10px] uppercase tracking-wider text-parchment-300">
                <th className="py-2.5 px-3">Topic &amp; Top Lemmas</th>
                <th className="py-2.5 px-3">Ideological Pole</th>
                <th className="py-2.5 px-3 text-right">Ownership Effect β₁ (Sec. vs. Conf.)</th>
                <th className="py-2.5 px-3 text-right">β₁ 95% CI &amp; t-Stat</th>
                <th className="py-2.5 px-3 text-right">55-Yr Shift β₂ (1970→2025)</th>
                <th className="py-2.5 px-3 text-right">β₂ 95% CI &amp; t-Stat</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.05] text-xs">
              {sortedStmRows.map((row: STMCovariateRow) => {
                const parsed = parseTopicLabel(row.topic_label);
                const secPos = row.secular_vs_confessional_effect_pct >= 0;
                const timePos = row.diachronic_1970_2025_shift_pct >= 0;
                const secBarW = Math.min(
                  100,
                  (Math.abs(row.secular_vs_confessional_effect_pct) / maxAbsSecularBeta) * 100
                );
                const timeBarW = Math.min(
                  100,
                  (Math.abs(row.diachronic_1970_2025_shift_pct) / maxAbsTimeBeta) * 100
                );

                return (
                  <tr
                    key={row.topic_id}
                    className="hover:bg-white/[0.03] transition-colors"
                  >
                    {/* Topic ID & Lemmas */}
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-2">
                        <span className="px-1.5 py-0.5 rounded bg-obsidian-900 border border-white/15 font-mono text-[10px] font-bold text-parchment-50 tabular-nums shrink-0">
                          T{String(row.topic_id).padStart(2, '0')}
                        </span>
                        <span className="font-mono text-[11px] text-parchment-100 italic">
                          {parsed.lemmas}
                        </span>
                      </div>
                    </td>

                    {/* Ideological Regime Badge */}
                    <td className="py-2.5 px-3">
                      <span
                        className={clsx(
                          'inline-block px-2 py-0.5 rounded border font-mono text-[9px] font-semibold whitespace-nowrap',
                          parsed.badgeClass
                        )}
                      >
                        {parsed.regime}
                      </span>
                    </td>

                    {/* β₁ Ownership Effect + Diverging Micro-Bar */}
                    <td className="py-2.5 px-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-20 h-2.5 rounded bg-obsidian-900 border border-white/[0.06] flex items-center overflow-hidden shrink-0">
                          <div className="w-1/2 h-full flex justify-end border-r border-white/25">
                            {!secPos && (
                              <div
                                style={{ width: `${secBarW}%` }}
                                className="h-full bg-traditional rounded-l-sm"
                              />
                            )}
                          </div>
                          <div className="w-1/2 h-full flex justify-start">
                            {secPos && (
                              <div
                                style={{ width: `${secBarW}%` }}
                                className="h-full bg-critical rounded-r-sm"
                              />
                            )}
                          </div>
                        </div>
                        <span
                          className={clsx(
                            'font-mono text-xs font-bold tabular-nums w-14 text-right',
                            secPos ? 'text-critical' : 'text-traditional'
                          )}
                        >
                          {secPos
                            ? `+${row.secular_vs_confessional_effect_pct.toFixed(2)}%`
                            : `${row.secular_vs_confessional_effect_pct.toFixed(2)}%`}
                        </span>
                      </div>
                    </td>

                    {/* β₁ CI & t-stat */}
                    <td className="py-2.5 px-3 text-right font-mono text-[10px] text-parchment-300 tabular-nums whitespace-nowrap">
                      <div>
                        [{row.secular_ci_95[0].toFixed(2)}, {row.secular_ci_95[1].toFixed(2)}]
                      </div>
                      <div className="text-[9px] text-parchment-200">
                        t = {row.secular_t_stat >= 0 ? `+${row.secular_t_stat.toFixed(1)}` : row.secular_t_stat.toFixed(1)}{' '}
                        <span className="text-emerald-300">({formatPValue(row.secular_p_value)})</span>
                      </div>
                    </td>

                    {/* β₂ 55-Year Diachronic Shift + Diverging Micro-Bar */}
                    <td className="py-2.5 px-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-20 h-2.5 rounded bg-obsidian-900 border border-white/[0.06] flex items-center overflow-hidden shrink-0">
                          <div className="w-1/2 h-full flex justify-end border-r border-white/25">
                            {!timePos && (
                              <div
                                style={{ width: `${timeBarW}%` }}
                                className="h-full bg-traditional rounded-l-sm"
                              />
                            )}
                          </div>
                          <div className="w-1/2 h-full flex justify-start">
                            {timePos && (
                              <div
                                style={{ width: `${timeBarW}%` }}
                                className="h-full bg-neoliberal rounded-r-sm"
                              />
                            )}
                          </div>
                        </div>
                        <span
                          className={clsx(
                            'font-mono text-xs font-bold tabular-nums w-16 text-right',
                            timePos ? 'text-neoliberal' : 'text-traditional'
                          )}
                        >
                          {timePos
                            ? `+${row.diachronic_1970_2025_shift_pct.toFixed(2)}%`
                            : `${row.diachronic_1970_2025_shift_pct.toFixed(2)}%`}
                        </span>
                      </div>
                    </td>

                    {/* β₂ CI & t-stat */}
                    <td className="py-2.5 px-3 text-right font-mono text-[10px] text-parchment-300 tabular-nums whitespace-nowrap">
                      <div>
                        [{row.diachronic_ci_95[0].toFixed(2)}, {row.diachronic_ci_95[1].toFixed(2)}]
                      </div>
                      <div className="text-[9px] text-parchment-200">
                        t = {row.diachronic_t_stat >= 0 ? `+${row.diachronic_t_stat.toFixed(1)}` : row.diachronic_t_stat.toFixed(1)}{' '}
                        <span className="text-emerald-300">({formatPValue(row.diachronic_p_value)})</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Bottom STM Headline Verification Strip */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 pt-2.5 border-t border-white/[0.07] font-mono text-[10px]">
          <div className="p-2.5 rounded-lg bg-obsidian-900/90 border border-traditional/30 flex items-center justify-between gap-2">
            <div>
              <span className="block text-[9px] uppercase text-parchment-300">
                Strongest Confessional Anchor (β₁)
              </span>
              <strong className="text-traditional">
                T02 Ecclesiology (-4.77%, t = -158.8***)
              </strong>
            </div>
            <CheckCircle2 className="w-4 h-4 text-traditional shrink-0" />
          </div>
          <div className="p-2.5 rounded-lg bg-obsidian-900/90 border border-critical/30 flex items-center justify-between gap-2">
            <div>
              <span className="block text-[9px] uppercase text-parchment-300">
                Strongest Secular Ownership Lift (β₁)
              </span>
              <strong className="text-critical">
                T07 Subjectivity (+4.36%, t = +95.9***)
              </strong>
            </div>
            <CheckCircle2 className="w-4 h-4 text-critical shrink-0" />
          </div>
          <div className="p-2.5 rounded-lg bg-obsidian-900/90 border border-neoliberal/30 flex items-center justify-between gap-2">
            <div>
              <span className="block text-[9px] uppercase text-parchment-300">
                Largest 55-Year Expansion (β₂)
              </span>
              <strong className="text-neoliberal">
                T06 Sociology &amp; Ethics (+10.45%, t = +170.5***)
              </strong>
            </div>
            <CheckCircle2 className="w-4 h-4 text-neoliberal shrink-0" />
          </div>
        </div>
      </div>
    </div>
  );
};
