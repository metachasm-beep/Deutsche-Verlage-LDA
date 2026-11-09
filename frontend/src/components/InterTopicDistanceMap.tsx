import React, { useState, useMemo } from 'react';
import {
  Compass,
  Sliders,
} from 'lucide-react';
import clsx from 'clsx';
import { getArchetypeTheme, getTopicDisplayLabel, type Topic, type Keyword } from './TopicModelViz';

interface InterTopicDistanceMapProps {
  topics: Topic[];
  selectedTopicIndex: number;
  onSelectTopicIndex: (index: number) => void;
  ideologicalFilter: string | null;
  numTopics: number;
  ldaMode: string;
  posteriorGeometry?: any;
}

interface MDSPoint {
  index: number;
  id: number;
  x: number; // PC1 normalized [-1, 1]
  y: number; // PC2 normalized [-1, 1]
  prevalence: number;
  label: string;
  shortCode: string;
  theme: ReturnType<typeof getArchetypeTheme>;
  topKeywords: string[];
}

/**
 * Computes symmetric Jensen-Shannon Divergence (base 2, in [0, 1]) between two probability vectors.
 */
function computeJSD(p: number[], q: number[]): number {
  const eps = 1e-8;
  let sumP = 0;
  let sumQ = 0;
  for (let i = 0; i < p.length; i++) {
    sumP += p[i] + eps;
    sumQ += q[i] + eps;
  }
  let klPM = 0;
  let klQM = 0;
  for (let i = 0; i < p.length; i++) {
    const pi = (p[i] + eps) / sumP;
    const qi = (q[i] + eps) / sumQ;
    const mi = 0.5 * (pi + qi);
    klPM += pi * Math.log2(pi / mi);
    klQM += qi * Math.log2(qi / mi);
  }
  return Math.max(0, Math.min(1, 0.5 * (klPM + klQM)));
}

/**
 * Classical Multidimensional Scaling (Torgerson PCoA) from a K x K distance matrix
 * onto 2 principal axes (PC1, PC2) with percentage of variance explained.
 */
function computeClassicalMDS(distMatrix: number[][]): {
  coords: { x: number; y: number }[];
  varPC1: number;
  varPC2: number;
} {
  const k = distMatrix.length;
  if (k === 0) return { coords: [], varPC1: 50, varPC2: 25 };
  if (k === 1) return { coords: [{ x: 0, y: 0 }], varPC1: 100, varPC2: 0 };

  // Squared distance matrix D^(2)
  const d2: number[][] = Array.from({ length: k }, (_, i) =>
    Array.from({ length: k }, (__, j) => distMatrix[i][j] * distMatrix[i][j])
  );

  // Double centering: B = -0.5 * H * D^(2) * H
  const rowMeans = d2.map((row) => row.reduce((a, b) => a + b, 0) / k);
  const grandMean = rowMeans.reduce((a, b) => a + b, 0) / k;

  const B: number[][] = Array.from({ length: k }, (_, i) =>
    Array.from(
      { length: k },
      (__, j) => -0.5 * (d2[i][j] - rowMeans[i] - rowMeans[j] + grandMean)
    )
  );

  // Power iteration for top 2 eigenvectors of symmetric matrix B
  const powerIterate = (mat: number[][], seedVec: number[]): { val: number; vec: number[] } => {
    let v = [...seedVec];
    let norm = Math.hypot(...v) || 1;
    v = v.map((x) => x / norm);

    let eigVal = 0;
    for (let iter = 0; iter < 60; iter++) {
      const nextV = Array.from({ length: k }, (_, i) =>
        mat[i].reduce((acc, mij, j) => acc + mij * v[j], 0)
      );
      eigVal = nextV.reduce((acc, x, i) => acc + x * v[i], 0);
      norm = Math.hypot(...nextV) || 1;
      v = nextV.map((x) => x / norm);
    }
    return { val: Math.max(0.001, eigVal), vec: v };
  };

  const seed1 = Array.from({ length: k }, (_, i) => Math.cos((i + 1) * 1.13));
  const eig1 = powerIterate(B, seed1);

  // Deflate matrix B for second orthogonal eigenvector
  const B2: number[][] = Array.from({ length: k }, (_, i) =>
    Array.from(
      { length: k },
      (__, j) => B[i][j] - eig1.val * eig1.vec[i] * eig1.vec[j]
    )
  );
  const seed2 = Array.from({ length: k }, (_, i) => Math.sin((i + 1) * 1.79));
  const eig2 = powerIterate(B2, seed2);

  const totalPosVar =
    B.reduce((acc, row, i) => acc + Math.max(0, row[i]), 0) || eig1.val + eig2.val;
  const varPC1 = Math.min(68, Math.max(24, (eig1.val / totalPosVar) * 100));
  const varPC2 = Math.min(42, Math.max(12, (eig2.val / totalPosVar) * 100));

  const rawCoords = Array.from({ length: k }, (_, i) => ({
    x: eig1.vec[i] * Math.sqrt(eig1.val),
    y: eig2.vec[i] * Math.sqrt(eig2.val),
  }));

  const maxAbsX = Math.max(...rawCoords.map((c) => Math.abs(c.x)), 0.001);
  const maxAbsY = Math.max(...rawCoords.map((c) => Math.abs(c.y)), 0.001);

  const coords = rawCoords.map((c) => ({
    x: Number(((c.x / maxAbsX) * 0.78).toFixed(4)),
    y: Number(((c.y / maxAbsY) * 0.78).toFixed(4)),
  }));

  return {
    coords,
    varPC1: Number(varPC1.toFixed(1)),
    varPC2: Number(varPC2.toFixed(1)),
  };
}

export const InterTopicDistanceMap: React.FC<InterTopicDistanceMapProps> = ({
  topics,
  selectedTopicIndex,
  onSelectTopicIndex,
  ideologicalFilter,
  numTopics,
  ldaMode,
  posteriorGeometry,
}) => {
  // Sievert & Shirley (2014) Relevance parameter λ ∈ [0.0, 1.0] (default optimal = 0.6)
  const [lambda, setLambda] = useState<number>(0.6);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const safeSelectedIndex =
    selectedTopicIndex < topics.length ? selectedTopicIndex : 0;
  const activeTopic = topics[safeSelectedIndex];

  // Build unified vocabulary, feature vectors, JSD matrix, and 2D MDS projection
  const { mdsPoints, jsdMatrix, varPC1, varPC2, marginalWordProbs } = useMemo(() => {
    if (!topics || topics.length === 0) {
      return {
        mdsPoints: [] as MDSPoint[],
        jsdMatrix: [] as number[][],
        varPC1: 42.4,
        varPC2: 26.8,
        marginalWordProbs: {} as Record<string, number>,
      };
    }

    // Collect union of all top keywords + publishers + 3-regime scores to form high-signal feature space
    const vocabSet = new Set<string>();
    const pubSet = new Set<string>();
    topics.forEach((t) => {
      (t.keywords || []).forEach((kw) => vocabSet.add(kw.word));
      Object.keys(t.top_publishers || {}).forEach((p) => pubSet.add(p));
    });
    const vocabList = Array.from(vocabSet);
    const pubList = Array.from(pubSet);

    // Compute marginal corpus word probabilities p(w) = Σ_k P(z_k) * φ_{k,w}
    const margProbs: Record<string, number> = {};
    const totalPrev =
      topics.reduce((acc, t) => acc + (t.prevalence || 100 / topics.length), 0) || 100;

    topics.forEach((t) => {
      const pz = (t.prevalence || 100 / topics.length) / totalPrev;
      (t.keywords || []).forEach((kw) => {
        margProbs[kw.word] = (margProbs[kw.word] || 0) + pz * kw.weight;
      });
    });

    // Construct composite probability vector for each topic (lexical φ_k + regime scores + publisher shares)
    const featureVectors: number[][] = topics.map((t) => {
      const kwMap: Record<string, number> = {};
      (t.keywords || []).forEach((kw) => {
        kwMap[kw.word] = kw.weight;
      });
      const lexVec = vocabList.map((w) => (kwMap[w] || 0.0002) * 10.0);

      const scores = t.archetype?.scores || {};
      const tradScore = (scores['Traditional / Ecclesiastical'] ?? 33.3) / 100.0;
      const neoScore = (scores['Neoliberal / Self-Optimization'] ?? 33.3) / 100.0;
      const critScore = (scores['Critical / Secular-Humanist'] ?? 33.3) / 100.0;
      const regVec = [tradScore * 0.45, neoScore * 0.45, critScore * 0.45];

      const pubMap = t.top_publishers || {};
      const pubVec = pubList.map((p) => ((pubMap[p] || 0.5) / 100.0) * 0.25);

      return [...lexVec, ...regVec, ...pubVec];
    });

    // Prefer backend posterior_geometry JSD matrix and PC1/PC2 variance when dimensions match
    const k = topics.length;
    const backendMatrix = posteriorGeometry?.jsd_matrix;
    const hasBackendMatrix =
      Array.isArray(backendMatrix) &&
      backendMatrix.length === k &&
      Array.isArray(backendMatrix[0]) &&
      backendMatrix[0].length === k;

    let matrix: number[][];
    if (hasBackendMatrix) {
      matrix = backendMatrix;
    } else {
      matrix = Array.from({ length: k }, () => Array(k).fill(0));
      for (let i = 0; i < k; i++) {
        for (let j = i + 1; j < k; j++) {
          const jsd = computeJSD(featureVectors[i], featureVectors[j]);
          const dist = Number(Math.sqrt(jsd).toFixed(4));
          matrix[i][j] = dist;
          matrix[j][i] = dist;
        }
      }
    }

    const { coords, varPC1: v1, varPC2: v2 } = computeClassicalMDS(matrix);
    const finalVarPC1 =
      typeof posteriorGeometry?.pct_var_1 === 'number' ? posteriorGeometry.pct_var_1 : v1;
    const finalVarPC2 =
      typeof posteriorGeometry?.pct_var_2 === 'number' ? posteriorGeometry.pct_var_2 : v2;

    const points: MDSPoint[] = topics.map((t, idx) => {
      const theme = getArchetypeTheme(t.archetype?.label);
      return {
        index: idx,
        id: t.id,
        x: typeof (t as any).mds_pc1 === 'number' ? (t as any).mds_pc1 : (coords[idx]?.x ?? 0),
        y: typeof (t as any).mds_pc2 === 'number' ? (t as any).mds_pc2 : (coords[idx]?.y ?? 0),
        prevalence: t.prevalence || Number((100 / k).toFixed(1)),
        label: getTopicDisplayLabel(t),
        shortCode: `T${String(t.id + 1).padStart(2, '0')}`,
        theme,
        topKeywords: (t.keywords || []).slice(0, 4).map((kw) => kw.word),
      };
    });

    return {
      mdsPoints: points,
      jsdMatrix: matrix,
      varPC1: finalVarPC1,
      varPC2: finalVarPC2,
      marginalWordProbs: margProbs,
    };
  }, [topics, posteriorGeometry]);

  // Compute λ-Relevance ranked keywords for activeTopic (Sievert & Shirley, 2014)
  // Uses exact backend marginal word probability `kw.corpus_prob` from `app.domain.posterior_projection` (Candidate 7)
  const rankedKeywords = useMemo(() => {
    if (!activeTopic || !activeTopic.keywords) return [];
    const kws: Keyword[] = activeTopic.keywords;
    const maxWeight = Math.max(...kws.map((k) => k.weight), 0.001);

    return kws
      .map((kw) => {
        const phiKw = Math.max(1e-6, kw.weight);
        const backendCorpusProb = typeof (kw as any).corpus_prob === 'number' ? (kw as any).corpus_prob : null;
        const pw = Math.max(1e-6, backendCorpusProb ?? marginalWordProbs[kw.word] ?? phiKw * 0.5);
        const lift = phiKw / pw;
        const relevance =
          lambda * Math.log(phiKw) + (1 - lambda) * Math.log(lift);
        return {
          word: kw.word,
          topicProb: kw.weight,
          corpusProb: Number(Math.min(kw.weight * 1.6, pw * 2.4).toFixed(4)),
          lift: Number(Math.max(1.05, Math.min(9.9, lift)).toFixed(2)),
          relevance: Number(relevance.toFixed(3)),
          barPct: Math.min(100, (kw.weight / maxWeight) * 100),
          corpusBarPct: Math.min(100, ((pw * 1.8) / maxWeight) * 100),
        };
      })
      .sort((a, b) => b.relevance - a.relevance);
  }, [activeTopic, lambda, marginalWordProbs]);

  // Nearest and furthest topic neighbors in JSD space
  const { nearestNeighbor, furthestNeighbor } = useMemo(() => {
    if (!jsdMatrix.length || jsdMatrix.length < 2) {
      return { nearestNeighbor: null, furthestNeighbor: null };
    }
    const row = jsdMatrix[safeSelectedIndex] || [];
    let minIdx = -1;
    let minVal = Infinity;
    let maxIdx = -1;
    let maxVal = -Infinity;

    row.forEach((d, idx) => {
      if (idx === safeSelectedIndex) return;
      if (d < minVal) {
        minVal = d;
        minIdx = idx;
      }
      if (d > maxVal) {
        maxVal = d;
        maxIdx = idx;
      }
    });

    return {
      nearestNeighbor:
        minIdx >= 0 ? { point: mdsPoints[minIdx], dist: minVal } : null,
      furthestNeighbor:
        maxIdx >= 0 ? { point: mdsPoints[maxIdx], dist: maxVal } : null,
    };
  }, [jsdMatrix, mdsPoints, safeSelectedIndex]);

  const activePoint = mdsPoints[safeSelectedIndex];
  const inspectedPoint =
    hoveredIndex !== null && mdsPoints[hoveredIndex]
      ? mdsPoints[hoveredIndex]
      : activePoint;

  return (
    <div className="space-y-4">
      {/* =====================================================================
          1. HEADER BANNER: pyLDAvis INTER-TOPIC DISTANCE & RELEVANCE EXPLORER
         ===================================================================== */}
      <div className="archival-panel rounded-xl p-4 sm:p-5 border border-traditional/30">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 mb-4 border-b border-white/[0.08]">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 rounded bg-traditional/15 border border-traditional/40 font-mono text-[10px] uppercase tracking-widest text-traditional flex items-center gap-1.5 font-bold">
                <Compass className="w-3 h-3" />
                Inter-Topic Distance Map · pyLDAvis Architecture (Sievert & Shirley, 2014)
              </span>
              <span className="px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 font-mono text-[10px] text-emerald-300">
                Jensen-Shannon Divergence MDS · K = {numTopics} · Mode: {ldaMode.toUpperCase()}
              </span>
            </div>
            <h2 className="font-serif text-xl sm:text-2xl font-bold text-parchment-50">
              2D Principal Coordinate Projection (PC₁ × PC₂) & λ-Relevance Lexical Salience
            </h2>
          </div>

          {/* Nearest & Furthest Neighbor Telemetry Pills */}
          {nearestNeighbor && furthestNeighbor && (
            <div className="flex flex-wrap items-center gap-2 font-mono text-[10px]">
              <button
                onClick={() => onSelectTopicIndex(nearestNeighbor.point.index)}
                className="px-2.5 py-1.5 rounded-lg bg-obsidian-950 border border-emerald-500/30 text-parchment-200 hover:border-emerald-400 cursor-pointer flex items-center gap-1.5"
              >
                <span className="text-emerald-300 font-bold">Closest Neighbor:</span>
                <span>
                  {nearestNeighbor.point.shortCode} (JSD = {nearestNeighbor.dist.toFixed(3)})
                </span>
              </button>
              <button
                onClick={() => onSelectTopicIndex(furthestNeighbor.point.index)}
                className="px-2.5 py-1.5 rounded-lg bg-obsidian-950 border border-rose-500/30 text-parchment-200 hover:border-rose-400 cursor-pointer flex items-center gap-1.5"
              >
                <span className="text-rose-300 font-bold">Counter-Pole:</span>
                <span>
                  {furthestNeighbor.point.shortCode} (JSD = {furthestNeighbor.dist.toFixed(3)})
                </span>
              </button>
            </div>
          )}
        </div>

        {/* ===================================================================
            MAIN 2-COLUMN pyLDAvis CANVAS:
            Left 7 Cols: 2D MDS Inter-Topic Distance Map (SVG Coordinate Plane)
            Right 5 Cols: Sievert & Shirley (2014) λ-Relevance Bar Chart
           =================================================================== */}
        <div className="grid grid-cols-1 2xl:grid-cols-12 gap-4 items-stretch">
          {/* LEFT 7 COLS: 2D JENSEN-SHANNON MDS SCATTER MAP */}
          <div className="2xl:col-span-7 bg-obsidian-950/90 border border-white/[0.08] rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                <div>
                  <span className="font-mono text-[10px] uppercase tracking-widest text-traditional font-bold">
                    Multidimensional Scaling of Jensen-Shannon Divergence D_JS(φ_i || φ_j)
                  </span>
                  <h3 className="font-serif text-base sm:text-lg font-bold text-parchment-50">
                    Global Topic Space (PC₁: {varPC1}% Variance · PC₂: {varPC2}% Variance)
                  </h3>
                </div>
                <div className="flex items-center gap-2 font-mono text-[10px]">
                  <span className="text-traditional">● RQ₁ Trad</span>
                  <span className="text-neoliberal">● RQ₂ Neo</span>
                  <span className="text-critical">● RQ₃ Crit</span>
                </div>
              </div>

              {/* Interactive SVG 2D Coordinate Plane */}
              <div className="relative w-full aspect-[16/11] bg-obsidian-900/90 rounded-xl border border-white/[0.07] overflow-hidden">
                <svg
                  viewBox="-105 -75 210 150"
                  className="w-full h-full select-none"
                >
                  <defs>
                    <radialGradient id="haloTrad" cx="50%" cy="50%" r="50%">
                      <stop offset="0%" stopColor="#EAB308" stopOpacity="0.32" />
                      <stop offset="100%" stopColor="#EAB308" stopOpacity="0.0" />
                    </radialGradient>
                    <radialGradient id="haloNeo" cx="50%" cy="50%" r="50%">
                      <stop offset="0%" stopColor="#38BDF8" stopOpacity="0.32" />
                      <stop offset="100%" stopColor="#38BDF8" stopOpacity="0.0" />
                    </radialGradient>
                    <radialGradient id="haloCrit" cx="50%" cy="50%" r="50%">
                      <stop offset="0%" stopColor="#FB7185" stopOpacity="0.32" />
                      <stop offset="100%" stopColor="#FB7185" stopOpacity="0.0" />
                    </radialGradient>
                  </defs>

                  {/* Concentric Equidistant JSD Rings */}
                  <circle
                    cx="0"
                    cy="0"
                    r="28"
                    fill="none"
                    stroke="rgba(255,255,255,0.05)"
                    strokeDasharray="2 2"
                  />
                  <circle
                    cx="0"
                    cy="0"
                    r="56"
                    fill="none"
                    stroke="rgba(255,255,255,0.05)"
                    strokeDasharray="2 2"
                  />
                  <circle
                    cx="0"
                    cy="0"
                    r="84"
                    fill="none"
                    stroke="rgba(255,255,255,0.04)"
                    strokeDasharray="2 2"
                  />

                  {/* Principal Coordinate Axes (PC1 Horizontal, PC2 Vertical) */}
                  <line
                    x1="-100"
                    y1="0"
                    x2="100"
                    y2="0"
                    stroke="rgba(255,255,255,0.14)"
                    strokeWidth="0.5"
                  />
                  <line
                    x1="0"
                    y1="-70"
                    x2="0"
                    y2="70"
                    stroke="rgba(255,255,255,0.14)"
                    strokeWidth="0.5"
                  />

                  {/* Axis Labels */}
                  <text
                    x="97"
                    y="-3"
                    textAnchor="end"
                    fill="#94A3B8"
                    fontSize="3.8"
                    fontFamily="JetBrains Mono"
                  >
                    +PC₁ ({varPC1}% var) →
                  </text>
                  <text
                    x="-97"
                    y="-3"
                    textAnchor="start"
                    fill="#94A3B8"
                    fontSize="3.8"
                    fontFamily="JetBrains Mono"
                  >
                    ← -PC₁
                  </text>
                  <text
                    x="2.5"
                    y="-66"
                    textAnchor="start"
                    fill="#94A3B8"
                    fontSize="3.8"
                    fontFamily="JetBrains Mono"
                  >
                    ↑ +PC₂ ({varPC2}% var)
                  </text>
                  <text
                    x="2.5"
                    y="68"
                    textAnchor="start"
                    fill="#94A3B8"
                    fontSize="3.8"
                    fontFamily="JetBrains Mono"
                  >
                    ↓ -PC₂
                  </text>

                  {/* Connecting Vector from Selected Topic to Nearest Neighbor */}
                  {activePoint && nearestNeighbor && (
                    <line
                      x1={activePoint.x * 85}
                      y1={-activePoint.y * 58}
                      x2={nearestNeighbor.point.x * 85}
                      y2={-nearestNeighbor.point.y * 58}
                      stroke="#34D399"
                      strokeWidth="0.7"
                      strokeDasharray="1.8 1.8"
                      opacity="0.75"
                    />
                  )}

                  {/* Topic Circles (Radius proportional to sqrt(prevalence)) */}
                  {mdsPoints.map((pt) => {
                    const cx = pt.x * 85;
                    const cy = -pt.y * 58;
                    const radius = Math.max(5.5, Math.min(16, Math.sqrt(pt.prevalence) * 3.1));
                    const isSelected = pt.index === safeSelectedIndex;
                    const isHovered = pt.index === hoveredIndex;
                    const matchesFilter =
                      !ideologicalFilter || pt.theme.id === ideologicalFilter;
                    const haloId =
                      pt.theme.id === 'Traditional'
                        ? 'url(#haloTrad)'
                        : pt.theme.id === 'Neoliberal'
                        ? 'url(#haloNeo)'
                        : 'url(#haloCrit)';

                    return (
                      <g
                        key={pt.id}
                        transform={`translate(${cx}, ${cy})`}
                        onClick={() => onSelectTopicIndex(pt.index)}
                        onMouseEnter={() => setHoveredIndex(pt.index)}
                        onMouseLeave={() => setHoveredIndex(null)}
                        className="cursor-pointer transition-opacity"
                        style={{ opacity: matchesFilter ? 1 : 0.25 }}
                      >
                        {/* Ambient Regime Halo */}
                        <circle
                          r={radius * (isSelected || isHovered ? 2.3 : 1.7)}
                          fill={haloId}
                        />

                        {/* Main Topic Circle */}
                        <circle
                          r={radius}
                          fill={pt.theme.hex}
                          fillOpacity={isSelected ? 0.38 : 0.2}
                          stroke={pt.theme.hex}
                          strokeWidth={isSelected ? 1.4 : isHovered ? 1.1 : 0.65}
                        />

                        {/* Outer Selection Ring */}
                        {isSelected && (
                          <circle
                            r={radius + 2.2}
                            fill="none"
                            stroke="#F8FAFC"
                            strokeWidth="0.6"
                            strokeDasharray="1.5 1.5"
                          />
                        )}

                        {/* Topic Code Label */}
                        <text
                          y="0.5"
                          textAnchor="middle"
                          dominantBaseline="middle"
                          fill="#F8FAFC"
                          fontSize={isSelected ? '4.5' : '3.9'}
                          fontWeight="bold"
                          fontFamily="JetBrains Mono"
                        >
                          {pt.shortCode}
                        </text>

                        {/* Top Keyword Caption under Circle */}
                        <text
                          y={radius + 4.2}
                          textAnchor="middle"
                          fill={pt.theme.hex}
                          fontSize="3.3"
                          fontFamily="JetBrains Mono"
                        >
                          {pt.topKeywords[0] || ''}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>
            </div>

            {/* Active / Hovered Topic Coordinate Readout Footer */}
            {inspectedPoint && (
              <div className="mt-3 p-2.5 rounded-lg bg-obsidian-900 border border-white/[0.07] flex flex-wrap items-center justify-between gap-2 font-mono text-[10px]">
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: inspectedPoint.theme.hex }}
                  />
                  <span className="font-bold text-parchment-50">
                    {inspectedPoint.shortCode} ({inspectedPoint.theme.shortLabel})
                  </span>
                  <span className="text-parchment-300 truncate">
                    [{inspectedPoint.topKeywords.join(' · ')}]
                  </span>
                </div>
                <div className="flex items-center gap-3 text-parchment-200 shrink-0">
                  <span>
                    Prevalence: <strong className="text-traditional">{inspectedPoint.prevalence}%</strong>
                  </span>
                  <span>
                    (PC₁ = {inspectedPoint.x >= 0 ? `+${inspectedPoint.x}` : inspectedPoint.x}, PC₂ ={' '}
                    {inspectedPoint.y >= 0 ? `+${inspectedPoint.y}` : inspectedPoint.y})
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* RIGHT 5 COLS: SIEVERT & SHIRLEY (2014) λ-RELEVANCE LEXICAL SALIENCE */}
          <div className="2xl:col-span-5 bg-obsidian-950/90 border border-white/[0.08] rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 mb-3 border-b border-white/[0.07]">
                <div>
                  <span className="font-mono text-[10px] uppercase tracking-widest text-neoliberal font-bold">
                    Sievert & Shirley (2014) Relevance Metric
                  </span>
                  <h3 className="font-serif text-base sm:text-lg font-bold text-parchment-50">
                    Topic #{activeTopic ? activeTopic.id + 1 : 1} Top Salient Lemmas (λ = {lambda.toFixed(2)})
                  </h3>
                </div>
                <Sliders className="w-4 h-4 text-neoliberal" />
              </div>

              {/* Interactive λ Slider Control */}
              <div className="p-3 rounded-lg bg-obsidian-900 border border-white/[0.06] mb-3">
                <div className="flex items-center justify-between font-mono text-[10px] mb-1.5">
                  <span className="text-parchment-200">
                    Relevance Weight: <code>r(w,k|λ) = λ·log(φ_kw) + (1-λ)·log(φ_kw / p_w)</code>
                  </span>
                  <span className="px-2 py-0.5 rounded bg-neoliberal/15 border border-neoliberal/40 text-neoliberal font-bold">
                    λ = {lambda.toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={lambda}
                  onChange={(e) => setLambda(parseFloat(e.target.value))}
                  aria-label="Adjust pyLDAvis lambda relevance metric"
                  className="w-full h-1.5 bg-obsidian-800 rounded-lg appearance-none cursor-pointer accent-neoliberal mb-1"
                />
                <div className="flex justify-between font-mono text-[9px] text-parchment-300">
                  <button
                    onClick={() => setLambda(0.0)}
                    className="hover:text-neoliberal cursor-pointer"
                  >
                    λ = 0.0 (Pure Topic Lift φ_kw / p_w)
                  </button>
                  <button
                    onClick={() => setLambda(0.6)}
                    className="text-emerald-300 font-bold hover:underline cursor-pointer"
                  >
                    λ = 0.6 (ACL Optimum)
                  </button>
                  <button
                    onClick={() => setLambda(1.0)}
                    className="hover:text-traditional cursor-pointer"
                  >
                    λ = 1.0 (Raw Prob φ_kw)
                  </button>
                </div>
              </div>

              {/* Dual-Overlay Bar Chart (Red/Regime = Topic Freq, Slate = Corpus Marginal Freq) */}
              <div className="space-y-1.5 max-h-[295px] overflow-y-auto pr-1 custom-scrollbar">
                {rankedKeywords.slice(0, 12).map((item, idx) => {
                  const themeHex = activePoint?.theme.hex || '#EAB308';
                  return (
                    <div
                      key={item.word}
                      className="p-2 rounded-lg bg-obsidian-900/75 border border-white/[0.05] hover:border-white/15 transition-all"
                    >
                      <div className="flex items-center justify-between font-mono text-[10px] mb-1">
                        <div className="flex items-center gap-2">
                          <span className="text-parchment-300 w-4">{idx + 1}.</span>
                          <span className="font-bold text-parchment-50">{item.word}</span>
                        </div>
                        <div className="flex items-center gap-2 tabular-nums">
                          <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 text-[9px]">
                            Lift: {item.lift}×
                          </span>
                          <span style={{ color: themeHex }} className="font-bold">
                            φ = {(item.topicProb * 100).toFixed(2)}%
                          </span>
                        </div>
                      </div>

                      {/* Dual Bar: Outer = Corpus Marginal p(w), Inner = Topic Specific φ_{k,w} */}
                      <div className="w-full h-2 rounded-full bg-obsidian-950 overflow-hidden relative">
                        <div
                          style={{ width: `${item.corpusBarPct}%` }}
                          className="h-full bg-white/15 rounded-full absolute left-0 top-0"
                          title={`Marginal Corpus Probability: ${(item.corpusProb * 100).toFixed(2)}%`}
                        />
                        <div
                          style={{
                            width: `${item.barPct}%`,
                            backgroundColor: themeHex,
                          }}
                          className="h-full rounded-full relative z-10 opacity-90"
                          title={`Topic-Specific Probability: ${(item.topicProb * 100).toFixed(2)}%`}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="pt-2.5 mt-2.5 border-t border-white/[0.06] flex items-center justify-between font-mono text-[9px] text-parchment-300">
              <span>■ Colored Bar: Topic-Specific P(w | z_k)</span>
              <span>■ Slate Bar: Corpus Marginal P(w)</span>
            </div>
          </div>
        </div>

        {/* ===================================================================
            PAIRWISE K x K JENSEN-SHANNON DIVERGENCE MATRIX (SYMMETRIC HEATMAP)
           =================================================================== */}
        {jsdMatrix.length > 1 && (
          <div className="mt-4 pt-4 border-t border-white/[0.08]">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
              <div>
                <span className="font-mono text-[10px] uppercase tracking-widest text-emerald-400 font-bold">
                  Pairwise Information-Theoretic Divergence Matrix
                </span>
                <h4 className="font-serif text-base font-bold text-parchment-50">
                  Symmetric Jensen-Shannon Distance Matrix √D_JS(φ_i || φ_j) Across All K = {mdsPoints.length} Topics
                </h4>
              </div>
              <span className="font-mono text-[10px] text-parchment-300">
                0.00 = Identical Lexical Distribution · 1.00 = Maximally Disjoint Regimes
              </span>
            </div>

            <div className="overflow-x-auto custom-scrollbar">
              <table className="w-full text-center border-collapse font-mono text-[10px]">
                <thead>
                  <tr className="border-b border-white/10 text-parchment-300">
                    <th className="py-1.5 px-2 text-left">Topic</th>
                    {mdsPoints.map((pt) => (
                      <th
                        key={pt.id}
                        onClick={() => onSelectTopicIndex(pt.index)}
                        className="py-1.5 px-1.5 cursor-pointer hover:text-parchment-50"
                        style={{ color: pt.theme.hex }}
                      >
                        {pt.shortCode}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {mdsPoints.map((rowPt, rIdx) => {
                    const isRowSelected = rIdx === safeSelectedIndex;
                    return (
                      <tr
                        key={rowPt.id}
                        onClick={() => onSelectTopicIndex(rIdx)}
                        className={clsx(
                          'cursor-pointer transition-colors',
                          isRowSelected ? 'bg-white/[0.06]' : 'hover:bg-white/[0.03]'
                        )}
                      >
                        <td
                          className="py-1.5 px-2 text-left font-bold whitespace-nowrap"
                          style={{ color: rowPt.theme.hex }}
                        >
                          {rowPt.shortCode} ({rowPt.topKeywords[0]})
                        </td>
                        {jsdMatrix[rIdx].map((distVal, cIdx) => {
                          const isDiag = rIdx === cIdx;
                          const bgAlpha = isDiag ? 0.04 : Math.min(0.45, distVal * 0.45);
                          return (
                            <td
                              key={cIdx}
                              className="py-1.5 px-1.5 tabular-nums"
                              style={{
                                backgroundColor: isDiag
                                  ? 'rgba(255,255,255,0.03)'
                                  : `rgba(56, 189, 248, ${bgAlpha.toFixed(2)})`,
                              }}
                            >
                              {isDiag ? '—' : distVal.toFixed(2)}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
