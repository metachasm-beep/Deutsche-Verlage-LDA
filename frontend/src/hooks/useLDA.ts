import { useState } from 'react';

const API_BASE = '';

export interface CoherencePoint {
  k: number;
  c_v: number;
  u_mass: number;
  log_perplexity: number;
}

export interface RegimePreset {
  k: number;
  label: string;
  description: string;
}

export interface PublisherArchetypeRow {
  publisher: string;
  Traditional: number;
  Neoliberal: number;
  Critical: number;
}

export type LDAMode = 'unseeded' | 'unsupervised' | 'seeded' | 'supervised';

export interface ModeComparisonRow {
  mode: LDAMode;
  label: string;
  short_label: string;
  prior_type: string;
  supervision: string;
  u_mass: number;
  vocab_size: number;
  regime_cv_accuracy: number;
  regime_macro_f1: number;
  publisher_accuracy: number;
  r2_explanatory_power: number;
}

export interface TopicRegressionWeight {
  topic_id: number;
  predicted_regime: string;
  w_traditional: number;
  w_neoliberal: number;
  w_critical: number;
  discriminative_power: number;
}

export interface SLDADiagnostics {
  regime_cv_accuracy?: number;
  regime_in_sample_accuracy?: number;
  regime_macro_f1?: number;
  publisher_accuracy?: number;
  r2_explanatory_power?: number;
  regime_class_metrics?: Record<string, { precision: number; recall: number; f1: number; support: number }>;
  topic_regression_weights?: TopicRegressionWeight[];
}

export const useLDA = () => {
  const [isTraining, setIsTraining] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [trendsData, setTrendsData] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [topics, setTopics] = useState<any[]>([]);
  const [numTopics, setNumTopics] = useState<number>(12);
  const [ldaMode, setLdaMode] = useState<LDAMode>('unsupervised');
  const [ldaModeMeta, setLdaModeMeta] = useState<any>(null);
  const [modesComparison, setModesComparison] = useState<ModeComparisonRow[]>([]);
  const [sldaDiagnostics, setSldaDiagnostics] = useState<SLDADiagnostics | null>(null);
  const [corpusDocuments, setCorpusDocuments] = useState<number>(1863);
  const [vocabSize, setVocabSize] = useState<number>(10279);
  const [coherenceScore, setCoherenceScore] = useState<number>(-2.9771);
  const [cvCoherence, setCvCoherence] = useState<number | null>(null);
  const [coherenceGrid, setCoherenceGrid] = useState<CoherencePoint[]>([]);
  const [recommendedRegimes, setRecommendedRegimes] = useState<RegimePreset[]>([]);
  const [publisherArchetypes, setPublisherArchetypes] = useState<PublisherArchetypeRow[]>([]);
  const [decadeBreakdown, setDecadeBreakdown] = useState<Record<string, Record<string, number>>>({});
  const [representativeDocs, setRepresentativeDocs] = useState<Record<number, any[]>>({});
  const [seedLexicons, setSeedLexicons] = useState<Record<string, string[]>>({});
  const [religiousBoostWords, setReligiousBoostWords] = useState<string[]>([]);
  const [conceptualDrift, setConceptualDrift] = useState<any>(null);
  const [activeFilters, setActiveFilters] = useState<{
    year: number | null;
    decade: number | null;
    publishers: string[];
    seed_boost?: number;
    base_eta?: number;
  }>({ year: null, decade: null, publishers: [], seed_boost: 15.0, base_eta: 0.05 });

  const fetchConceptualDrift = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/conceptual-drift`);
      const data = await res.json();
      setConceptualDrift(data);
    } catch (e) {
      console.error("Failed to fetch conceptual drift", e);
    }
  };

  const fetchTrends = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/trends`);
      const data = await res.json();
      setTrendsData(data);
    } catch (e) {
      console.error("Failed to fetch trends", e);
    }
  };

  const fetchCoherenceGrid = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/coherence-grid`);
      const data = await res.json();
      setCoherenceGrid(data.grid || []);
      setRecommendedRegimes(data.recommended_regimes || []);
    } catch (e) {
      console.error("Failed to fetch coherence grid", e);
    }
  };

  const fetchTopics = async (
    modeOverride?: LDAMode,
    kOverride?: number,
    yearOverride?: number | null,
    decadeOverride?: number | null,
    pubsOverride?: string[],
    seedBoostOverride?: number,
    baseEtaOverride?: number
  ) => {
    try {
      const targetMode = modeOverride ?? ldaMode;
      const targetK = kOverride ?? numTopics;
      const targetYear = yearOverride !== undefined ? yearOverride : activeFilters.year;
      const targetDecade = decadeOverride !== undefined ? decadeOverride : activeFilters.decade;
      const targetPubs = pubsOverride !== undefined ? pubsOverride : activeFilters.publishers;
      const targetSeedBoost = seedBoostOverride ?? activeFilters.seed_boost ?? 15.0;
      const targetBaseEta = baseEtaOverride ?? activeFilters.base_eta ?? 0.05;

      const params = new URLSearchParams();
      params.append('lda_mode', targetMode);
      params.append('num_topics', targetK.toString());
      if (targetYear !== null && targetYear !== undefined) {
        params.append('year', targetYear.toString());
      } else {
        params.append('year', '0');
      }
      if (targetDecade !== null && targetDecade !== undefined) {
        params.append('decade', targetDecade.toString());
      } else {
        params.append('decade', '0');
      }
      params.append('publishers', (targetPubs || []).join(','));
      params.append('seed_boost', targetSeedBoost.toString());
      params.append('base_eta', targetBaseEta.toString());

      const res = await fetch(`${API_BASE}/api/topics?${params.toString()}`);
      const data = await res.json();
      setTopics(data.topics || []);
      if (data.lda_mode) setLdaMode(data.lda_mode as LDAMode);
      if (data.lda_mode_meta) setLdaModeMeta(data.lda_mode_meta);
      if (data.modes_comparison) setModesComparison(data.modes_comparison);
      if (data.slda_diagnostics) setSldaDiagnostics(data.slda_diagnostics);
      if (data.num_topics) setNumTopics(data.num_topics);
      if (data.corpus_documents) setCorpusDocuments(data.corpus_documents);
      if (data.vocab_size) setVocabSize(data.vocab_size);
      setCoherenceScore(data.coherence_score ?? 0);
      setCvCoherence(data.cv_coherence ?? null);
      setPublisherArchetypes(data.publisher_archetypes || []);
      setDecadeBreakdown(data.decade_breakdown || {});
      setRepresentativeDocs(data.representative_docs || {});
      if (data.seed_lexicons) setSeedLexicons(data.seed_lexicons);
      if (data.religious_boost_words) setReligiousBoostWords(data.religious_boost_words);
      if (data.active_filters) setActiveFilters(data.active_filters);
    } catch (e) {
      console.error("Failed to fetch topics", e);
    }
  };

  const fetchSummary = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/data-summary`);
      const data = await res.json();
      setSummary(data);
    } catch (e) {
      console.error("Failed to fetch summary", e);
    }
  };

  const runLDA = async (
    year?: number | null,
    decade?: number | null,
    kOverride?: number,
    modeOverride?: LDAMode,
    publishersOverride?: string[],
    seedBoostOverride?: number,
    baseEtaOverride?: number
  ) => {
    setIsTraining(true);
    try {
      const activeK = kOverride ?? numTopics;
      const activeMode = modeOverride ?? ldaMode;
      const activePubs = publishersOverride ?? activeFilters.publishers;
      const activeSeedBoost = seedBoostOverride ?? activeFilters.seed_boost ?? 15.0;
      const activeBaseEta = baseEtaOverride ?? activeFilters.base_eta ?? 0.05;
      if (kOverride) setNumTopics(kOverride);
      if (modeOverride) setLdaMode(modeOverride);

      let url = `${API_BASE}/api/run-lda`;
      const params = new URLSearchParams();
      if (year) params.append('year', year.toString());
      if (decade) params.append('decade', decade.toString());
      if (activeK) params.append('num_topics', activeK.toString());
      if (activeMode) params.append('lda_mode', activeMode);
      if (activePubs && activePubs.length > 0) {
        params.append('publishers', activePubs.join(','));
      }
      params.append('seed_boost', activeSeedBoost.toString());
      params.append('base_eta', activeBaseEta.toString());
      if (params.toString()) url += `?${params.toString()}`;

      await fetch(url, { method: 'POST' });
      await fetchTopics(
        activeMode,
        activeK,
        year ?? null,
        decade ?? null,
        activePubs,
        activeSeedBoost,
        activeBaseEta
      );
    } catch (e) {
      console.error("LDA training failed", e);
    } finally {
      setIsTraining(false);
    }
  };

  const uploadDataset = async (file: File) => {
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch(`${API_BASE}/api/upload-dataset`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      await fetchSummary();
      await fetchTrends();
      await runLDA(null, null, numTopics, ldaMode);
      return true;
    } catch (e) {
      console.error("Failed to upload dataset", e);
      return false;
    } finally {
      setIsUploading(false);
    }
  };

  const resetToMock = async () => {
    setIsUploading(true);
    try {
      await fetch(`${API_BASE}/api/reset-to-mock`, { method: 'POST' });
      await fetchSummary();
      await fetchTrends();
      await runLDA(null, null, numTopics, 'unsupervised');
      return true;
    } catch (e) {
      console.error("Failed to reset to default corpus", e);
      return false;
    } finally {
      setIsUploading(false);
    }
  };

  const updateCustomSeeds = async (
    newSeeds: Record<string, string[]>,
    seedBoost: number = 15.0,
    baseEta: number = 0.05,
    triggerRun: boolean = true
  ) => {
    setSeedLexicons(newSeeds);
    try {
      await fetch(`${API_BASE}/api/update-seeds`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          seed_lexicons: newSeeds,
          seed_boost: seedBoost,
          base_eta: baseEta,
        }),
      });
      if (triggerRun) {
        await runLDA(
          activeFilters.year,
          activeFilters.decade,
          numTopics,
          'seeded',
          activeFilters.publishers,
          seedBoost,
          baseEta
        );
      }
    } catch (e) {
      console.error('Failed to update custom seeds', e);
    }
  };

  const resetCustomSeeds = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/reset-seeds`, { method: 'POST' });
      const data = await res.json();
      if (data.seed_lexicons) setSeedLexicons(data.seed_lexicons);
      await runLDA(
        activeFilters.year,
        activeFilters.decade,
        numTopics,
        ldaMode,
        activeFilters.publishers,
        15.0,
        0.05
      );
    } catch (e) {
      console.error('Failed to reset custom seeds', e);
    }
  };

  return {
    isTraining,
    isUploading,
    trendsData,
    summary,
    topics,
    numTopics,
    setNumTopics,
    ldaMode,
    setLdaMode,
    ldaModeMeta,
    modesComparison,
    sldaDiagnostics,
    corpusDocuments,
    vocabSize,
    coherenceScore,
    cvCoherence,
    coherenceGrid,
    recommendedRegimes,
    publisherArchetypes,
    decadeBreakdown,
    representativeDocs,
    seedLexicons,
    setSeedLexicons,
    religiousBoostWords,
    conceptualDrift,
    activeFilters,
    fetchTrends,
    fetchSummary,
    fetchTopics,
    fetchCoherenceGrid,
    fetchConceptualDrift,
    runLDA,
    updateCustomSeeds,
    resetCustomSeeds,
    uploadDataset,
    resetToMock
  };
};
