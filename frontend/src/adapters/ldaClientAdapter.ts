import type { LDAMode } from '../hooks/useLDA';

const API_BASE = '';

export interface PosteriorSliceParams {
  ldaMode: LDAMode;
  numTopics: number;
  year?: number | null;
  decade?: number | null;
  publishers?: string[];
  seedBoost?: number;
  baseEta?: number;
}

export interface Marc21SearchParams {
  q?: string;
  publisher?: string;
  year?: number | null;
  decade?: number | null;
  limit?: number;
}

export interface LDAClientPort {
  queryTopics(slice: PosteriorSliceParams): Promise<any>;
  updateCustomSeeds(payload: {
    seed_lexicons?: Record<string, string[]>;
    seed_boost?: number;
    base_eta?: number;
  }): Promise<any>;
  fetchTrends(): Promise<any>;
  fetchDataSummary(): Promise<any>;
  fetchCoherenceGrid(): Promise<any>;
  searchMarc21Catalog(params: Marc21SearchParams): Promise<any>;
  inspectGermanLemma(queryWord: string, ldaMode?: LDAMode): Promise<any>;
  updateTopicLabel(payload: {
    topic_id: number;
    lda_mode?: string;
    custom_label?: string;
    assigned_labels?: string[];
    regime_override?: string;
    apply_to_all_modes?: boolean;
  }): Promise<any>;
  resetTopicLabel(topicId?: number): Promise<any>;
}

export class HttpLDAClientAdapter implements LDAClientPort {
  async queryTopics(slice: PosteriorSliceParams): Promise<any> {
    const params = new URLSearchParams();
    params.append('lda_mode', slice.ldaMode);
    params.append('num_topics', slice.numTopics.toString());
    params.append('year', slice.year ? slice.year.toString() : '0');
    params.append('decade', slice.decade ? slice.decade.toString() : '0');
    params.append('publishers', (slice.publishers || []).join(','));
    params.append('seed_boost', (slice.seedBoost ?? 15.0).toString());
    params.append('base_eta', (slice.baseEta ?? 0.05).toString());

    const res = await fetch(`${API_BASE}/api/topics?${params.toString()}`);
    if (!res.ok) {
      throw new Error(`Failed to query posterior topics: ${res.status}`);
    }
    return res.json();
  }

  async updateCustomSeeds(payload: {
    seed_lexicons?: Record<string, string[]>;
    seed_boost?: number;
    base_eta?: number;
  }): Promise<any> {
    const res = await fetch(`${API_BASE}/api/update-seeds`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error(`Failed to update custom seeds: ${res.status}`);
    }
    return res.json();
  }

  async fetchTrends(): Promise<any> {
    const res = await fetch(`${API_BASE}/api/trends`);
    return res.json();
  }

  async fetchDataSummary(): Promise<any> {
    const res = await fetch(`${API_BASE}/api/data-summary`);
    return res.json();
  }

  async fetchCoherenceGrid(): Promise<any> {
    const res = await fetch(`${API_BASE}/api/coherence-grid`);
    return res.json();
  }

  async searchMarc21Catalog(params: Marc21SearchParams): Promise<any> {
    const q = new URLSearchParams();
    if (params.q) q.set('q', params.q);
    if (params.publisher) q.set('publisher', params.publisher);
    if (params.year) q.set('year', String(params.year));
    if (params.decade) q.set('decade', String(params.decade));
    q.set('limit', String(params.limit ?? 80));
    const res = await fetch(`${API_BASE}/api/marc21-search?${q.toString()}`);
    if (!res.ok) {
      throw new Error(`Failed to search MARC21 catalog: ${res.status}`);
    }
    return res.json();
  }

  async inspectGermanLemma(queryWord: string, ldaMode?: LDAMode): Promise<any> {
    const modeQuery = ldaMode ? `&lda_mode=${encodeURIComponent(ldaMode)}` : '';
    const res = await fetch(
      `${API_BASE}/api/lemma-inspector?q=${encodeURIComponent(queryWord.trim())}${modeQuery}`
    );
    if (!res.ok) {
      throw new Error(`Failed to inspect German lemma: ${res.status}`);
    }
    return res.json();
  }

  async updateTopicLabel(payload: {
    topic_id: number;
    lda_mode?: string;
    custom_label?: string;
    assigned_labels?: string[];
    regime_override?: string;
    apply_to_all_modes?: boolean;
  }): Promise<any> {
    const res = await fetch(`${API_BASE}/api/topic-labels`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error(`Failed to update topic label: ${res.status}`);
    }
    return res.json();
  }

  async resetTopicLabel(topicId?: number): Promise<any> {
    const res = await fetch(`${API_BASE}/api/reset-topic-labels`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(topicId !== undefined ? { topic_id: topicId } : {}),
    });
    if (!res.ok) {
      throw new Error(`Failed to reset topic label: ${res.status}`);
    }
    return res.json();
  }
}

export const ldaClientAdapter: LDAClientPort = new HttpLDAClientAdapter();
