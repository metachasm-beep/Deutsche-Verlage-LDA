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

export const useLDA = () => {
  const [isTraining, setIsTraining] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [trendsData, setTrendsData] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [topics, setTopics] = useState<any[]>([]);
  const [numTopics, setNumTopics] = useState<number>(12);
  const [coherenceScore, setCoherenceScore] = useState<number>(0);
  const [cvCoherence, setCvCoherence] = useState<number | null>(null);
  const [coherenceGrid, setCoherenceGrid] = useState<CoherencePoint[]>([]);
  const [recommendedRegimes, setRecommendedRegimes] = useState<RegimePreset[]>([]);
  const [representativeDocs, setRepresentativeDocs] = useState<Record<number, any[]>>({});

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

  const fetchTopics = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/topics`);
      const data = await res.json();
      setTopics(data.topics || []);
      if (data.num_topics) setNumTopics(data.num_topics);
      setCoherenceScore(data.coherence_score ?? 0);
      setCvCoherence(data.cv_coherence ?? null);
      setRepresentativeDocs(data.representative_docs || {});
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

  const runLDA = async (year?: number | null, decade?: number | null, kOverride?: number) => {
    setIsTraining(true);
    try {
      const activeK = kOverride ?? numTopics;
      if (kOverride) setNumTopics(kOverride);

      let url = `${API_BASE}/api/run-lda`;
      const params = new URLSearchParams();
      if (year) params.append('year', year.toString());
      if (decade) params.append('decade', decade.toString());
      if (activeK) params.append('num_topics', activeK.toString());
      if (params.toString()) url += `?${params.toString()}`;

      await fetch(url, { method: 'POST' });
      await fetchTopics();
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
      await runLDA(null, null, numTopics);
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
      await runLDA(null, null, numTopics);
      return true;
    } catch (e) {
      console.error("Failed to reset to default corpus", e);
      return false;
    } finally {
      setIsUploading(false);
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
    coherenceScore,
    cvCoherence,
    coherenceGrid,
    recommendedRegimes,
    representativeDocs,
    fetchTrends,
    fetchSummary,
    fetchTopics,
    fetchCoherenceGrid,
    runLDA,
    uploadDataset,
    resetToMock
  };
};
