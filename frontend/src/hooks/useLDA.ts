import { useState } from 'react';
import { ldaClientAdapter } from '../adapters/ldaClientAdapter';

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
  const [corpusDocuments, setCorpusDocuments] = useState<number>(10612079);
  const [vocabSize, setVocabSize] = useState<number>(38416);
  const [coherenceScore, setCoherenceScore] = useState<number>(-2.4760);
  const [cvCoherence, setCvCoherence] = useState<number | null>(null);
  const [coherenceGrid, setCoherenceGrid] = useState<CoherencePoint[]>([]);
  const [recommendedRegimes, setRecommendedRegimes] = useState<RegimePreset[]>([]);
  const [publisherArchetypes, setPublisherArchetypes] = useState<PublisherArchetypeRow[]>([]);
  const [decadeBreakdown, setDecadeBreakdown] = useState<Record<string, Record<string, number>>>({});
  const [representativeDocs, setRepresentativeDocs] = useState<Record<number, any[]>>({});
  const [seedLexicons, setSeedLexicons] = useState<Record<string, string[]>>({});
  const [religiousBoostWords, setReligiousBoostWords] = useState<string[]>([]);
  const [conceptualDrift, setConceptualDrift] = useState<any>(null);
  const [robustnessTelemetry, setRobustnessTelemetry] = useState<any>(null);
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
      const data = await ldaClientAdapter.fetchTrends();
      setTrendsData(data);
    } catch (e) {
      console.error("Failed to fetch trends", e);
    }
  };

  const fetchCoherenceGrid = async () => {
    try {
      const data = await ldaClientAdapter.fetchCoherenceGrid();
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

      const data = await ldaClientAdapter.queryTopics({
        ldaMode: targetMode,
        numTopics: targetK,
        year: targetYear,
        decade: targetDecade,
        publishers: targetPubs,
        seedBoost: targetSeedBoost,
        baseEta: targetBaseEta,
      });
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
      if (data.robustness_telemetry) setRobustnessTelemetry(data.robustness_telemetry);
    } catch (e) {
      console.error("Failed to fetch topics", e);
    }
  };

  const fetchSummary = async () => {
    try {
      const data = await ldaClientAdapter.fetchDataSummary();
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
    const showSpinner = topics.length === 0;
    if (showSpinner) setIsTraining(true);
    try {
      const activeK = kOverride ?? numTopics;
      const activeMode = modeOverride ?? ldaMode;
      const activePubs = publishersOverride ?? activeFilters.publishers;
      const activeSeedBoost = seedBoostOverride ?? activeFilters.seed_boost ?? 15.0;
      const activeBaseEta = baseEtaOverride ?? activeFilters.base_eta ?? 0.05;
      if (kOverride) setNumTopics(kOverride);
      if (modeOverride) setLdaMode(modeOverride);

      // Stateless single-roundtrip lookup of pre-computed posterior slice (Zero live training)
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
      console.error("LDA slice query failed", e);
    } finally {
      if (showSpinner) setIsTraining(false);
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
      await ldaClientAdapter.updateCustomSeeds({
        seed_lexicons: newSeeds,
        seed_boost: seedBoost,
        base_eta: baseEta,
      });
      if (triggerRun) {
        const targetMode: LDAMode =
          ldaMode === 'seeded' || ldaMode === 'supervised' ? ldaMode : 'seeded';
        await fetchTopics(
          targetMode,
          numTopics,
          activeFilters.year,
          activeFilters.decade,
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

  const updateTopicLabel = async (
    topicId: number,
    customLabel: string,
    assignedLabels: string[] = [],
    regimeOverride: string = ''
  ) => {
    // Optimistically update local topics state immediately
    setTopics((prev: any[]) =>
      prev.map((t) => {
        if (t.id !== topicId) return t;
        const defaultLbl = t.default_label || `Topic ${topicId + 1}`;
        const resolvedCustom = customLabel.trim() || defaultLbl;
        const nextArch = { ...(t.archetype || {}) };
        if (regimeOverride.trim()) {
          nextArch.original_label = nextArch.original_label || nextArch.label;
          nextArch.label = regimeOverride.trim();
        } else if (nextArch.original_label) {
          nextArch.label = nextArch.original_label;
        }
        return {
          ...t,
          archetype: nextArch,
          custom_label: resolvedCustom,
          assigned_labels: assignedLabels,
          is_label_edited: Boolean(
            (customLabel.trim() && customLabel.trim() !== defaultLbl) ||
              assignedLabels.length > 0 ||
              regimeOverride.trim()
          ),
        };
      })
    );

    try {
      await ldaClientAdapter.updateTopicLabel({
        topic_id: topicId,
        lda_mode: ldaMode,
        custom_label: customLabel,
        assigned_labels: assignedLabels,
        regime_override: regimeOverride,
        apply_to_all_modes: true,
      });
    } catch (e) {
      console.error('Failed to persist custom topic label', e);
    }
  };

  const resetTopicLabel = async (topicId?: number) => {
    setTopics((prev: any[]) =>
      prev.map((t) => {
        if (topicId !== undefined && t.id !== topicId) return t;
        const defaultLbl = t.default_label || `Topic ${t.id + 1}`;
        const nextArch = { ...(t.archetype || {}) };
        if (nextArch.original_label) {
          nextArch.label = nextArch.original_label;
        }
        return {
          ...t,
          archetype: nextArch,
          custom_label: defaultLbl,
          assigned_labels: [],
          is_label_edited: false,
        };
      })
    );
    try {
      await ldaClientAdapter.resetTopicLabel(topicId);
    } catch (e) {
      console.error('Failed to reset topic label', e);
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
    robustnessTelemetry,
    activeFilters,
    fetchTrends,
    fetchSummary,
    fetchTopics,
    fetchCoherenceGrid,
    fetchConceptualDrift,
    runLDA,
    updateCustomSeeds,
    resetCustomSeeds,
    updateTopicLabel,
    resetTopicLabel,
    uploadDataset,
    resetToMock
  };
};
