import { useState } from 'react';

// Hardcoded testing endpoint to connect the local UI to the live Vercel deployment
const API_BASE = '';

export const useLDA = () => {
  const [isTraining, setIsTraining] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [trendsData, setTrendsData] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [topics, setTopics] = useState<any[]>([]);
  const [coherenceScore, setCoherenceScore] = useState<number>(0);
  const [representativeDocs, setRepresentativeDocs] = useState<Record<number, string[]>>({});

  const fetchTrends = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/trends`);
      const data = await res.json();
      setTrendsData(data);
    } catch (e) {
      console.error("Failed to fetch trends", e);
    }
  };

  const fetchTopics = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/topics`);
      const data = await res.json();
      setTopics(data.topics || []);
      setCoherenceScore(data.coherence_score || 0);
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

  const runLDA = async (year?: number, decade?: number) => {
    setIsTraining(true);
    try {
      let url = `${API_BASE}/api/run-lda`;
      const params = new URLSearchParams();
      if (year) params.append('year', year.toString());
      if (decade) params.append('decade', decade.toString());
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
      await fetchTopics();
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
      await fetchTopics();
      // Auto-run LDA for better UX
      await runLDA();
      return true;
    } catch (e) {
      console.error("Failed to reset to mock data", e);
      return false;
    } finally {
      setIsUploading(false);
    }
  };

  return { 
    isTraining, isUploading, trendsData, summary, topics, 
    coherenceScore, representativeDocs,
    fetchTrends, fetchSummary, fetchTopics, runLDA, uploadDataset, resetToMock 
  };
};
