import { useState } from 'react';

// Hardcoded testing endpoint to connect the local UI to the live Vercel deployment
const API_BASE = '';

export const useLDA = () => {
  const [isTraining, setIsTraining] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [trendsData, setTrendsData] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);

  const fetchTrends = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/trends`);
      const data = await res.json();
      setTrendsData(data);
    } catch (e) {
      console.error("Failed to fetch trends", e);
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

  const runLDA = async (year?: number) => {
    setIsTraining(true);
    try {
      const endpoint = year ? `${API_BASE}/api/run-lda?year=${year}` : `${API_BASE}/api/run-lda`;
      const res = await fetch(endpoint, { method: 'POST' });
      const data = await res.json();
      return data;
    } catch (e) {
      console.error("Failed to run LDA", e);
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
      return true;
    } catch (e) {
      console.error("Failed to upload dataset", e);
      return false;
    } finally {
      setIsUploading(false);
    }
  };

  return { 
    isTraining, isUploading, trendsData, summary, 
    fetchTrends, fetchSummary, runLDA, uploadDataset, API_BASE 
  };
};
