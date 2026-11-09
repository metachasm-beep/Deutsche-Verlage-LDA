import React, { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { motion } from 'framer-motion';
import { Calendar, RotateCcw, Eye, EyeOff, Layers, TrendingUp, Search, Filter } from 'lucide-react';
import clsx from 'clsx';
import { getArchetypeTheme, getTopicDisplayLabel, type Topic } from './TopicModelViz';

export interface PublisherDirectoryEntry {
  publisher: string;
  passages: number;
  works?: number;
  category: string;
}

interface TrendsGraphProps {
  data: any[];
  publishers: string[];
  publisherCounts?: Record<string, number>;
  publisherWorksCounts?: Record<string, number>;
  publisherDirectory?: PublisherDirectoryEntry[];
  selectedPublishers?: string[];
  onTogglePublisher?: (publisher: string) => void;
  decadeBreakdown?: Record<string, Record<string, number>>;
  topics?: Topic[];
  selectedTopicIndex?: number;
  onSelectTopicIndex?: (index: number) => void;
  onYearClick?: (year: number) => void;
  selectedYear?: number | null;
  onDecadeClick?: (decade: number) => void;
  selectedDecade?: number | null;
  onResetTemporal?: () => void;
  compact?: boolean;
}

const PUBLISHER_COLORS: Record<string, string> = {
  'De Gruyter / Transcript': '#6D849E',
  'Vandenhoeck & Ruprecht': '#689F8D',
  'Schöningh': '#837CA8',
  'Böhlau': '#9283B8',
  'Mohr Siebeck': '#568C7A',
  'Kohlhammer': '#C99A5B',
  'Aschendorff': '#D6B27C',
  'Suhrkamp': '#C6716B',
  'Insel': '#B55D57',
  'Campus': '#B87A88',
  'Frommann-Holzboog': '#86A3B8',
  'Wilhelm Fink': '#9E8AB8',
  'Neukirchener': '#C99A5B',
  'Klett-Cotta': '#5B9EA6',
  'Gütersloher Verlagshaus': '#D1A76B',
  'Gütersloher Verlagshaus (Chr. Kaiser)': '#DBC08E',
  'Fischer': '#BA6E78',
  'Herder': '#C99A5B',
  'Herder (Grünewald)': '#B08040',
  'Herder (Benziger)': '#9E7034',
  'Herder (Kreuz)': '#5B9EA6',
  'Kreuz': '#5B9EA6',
  'Evangelische Verlagsanstalt': '#689F8D',
  'C.H. Beck': '#9283B8',
  'Rowohlt': '#C6716B',
  'Nomos / Alber': '#5B9EA6',
  'Echter': '#C99A5B',
  'Springer Nature / Metzler': '#6D849E',
  'Springer Nature (Holtzbrinck)': '#6D849E',
  'Meiner': '#837CA8',
  'Pustet': '#D6B27C',
  'Patmos': '#C99A5B',
  'Patmos (Schwabenverlag)': '#B08040',
  'Kösel': '#5B9EA6',
  'Schwabe': '#9283B8',
  'Calwer': '#C99A5B',
  'Wallstein': '#B55D57',
  'Bonifatius': '#B08040',
  'Kiepenheuer & Witsch': '#C6716B',
  'Kiepenheuer': '#C6716B',
  'Peter Lang': '#8A857A',
  'Wagenbach': '#B55D57',
  'LIT Verlag': '#767982',
  'TVZ (Theologischer Verlag Zürich)': '#689F8D',
  'Bibelwelt / Bibelwerk': '#C99A5B',
  'Bibelwelt-Verlag': '#C99A5B',
  'Alibri': '#B55D57',
  'Barbara Budrich': '#B87A88',
  'Budrich': '#B87A88',
  'Brill': '#6D849E',
  'Luther-Verlag': '#D1A76B',
  'Duncker & Humblot': '#837CA8',
  'St. Benno Verlag': '#C99A5B',
  'SCM R. Brockhaus': '#DBC08E',
  'Gräfe und Unzer (GU)': '#5B9EA6',
  'J. Kamphausen': '#639C94',
};

const FALLBACK_COLORS = [
  '#C99A5B',
  '#5B9EA6',
  '#C6716B',
  '#9283B8',
  '#689F8D',
  '#B08040',
  '#6D849E',
  '#B87A88',
  '#829672',
  '#D6B27C',
  '#837CA8',
  '#639C94',
];

const DECADE_COHORTS = [
  { label: '1970s', value: 1970 },
  { label: '1980s', value: 1980 },
  { label: '1990s', value: 1990 },
  { label: '2000s', value: 2000 },
  { label: '2010s', value: 2010 },
  { label: '2020s', value: 2020 },
];

export const COMPREHENSIVE_FALLBACK_PUBLISHERS: PublisherDirectoryEntry[] = [
  { publisher: 'De Gruyter / Transcript', passages: 33759, works: 6840, category: 'Academic & Philosophical' },
  { publisher: 'Vandenhoeck & Ruprecht', passages: 23948, works: 4920, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Schöningh', passages: 22289, works: 3180, category: 'Academic & Philosophical' },
  { publisher: 'Böhlau', passages: 22036, works: 3110, category: 'Academic & Philosophical' },
  { publisher: 'Mohr Siebeck', passages: 15238, works: 3890, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Kohlhammer', passages: 15044, works: 4120, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Aschendorff', passages: 12905, works: 2450, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Suhrkamp', passages: 12734, works: 3640, category: 'RQ₃ · Critical & Secular-Humanist' },
  { publisher: 'Campus', passages: 12589, works: 2980, category: 'RQ₃ · Critical & Secular-Humanist' },
  { publisher: 'Frommann-Holzboog', passages: 12502, works: 1420, category: 'Academic & Philosophical' },
  { publisher: 'Wilhelm Fink', passages: 11495, works: 1680, category: 'Academic & Philosophical' },
  { publisher: 'Neukirchener', passages: 11238, works: 2890, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Klett-Cotta', passages: 11237, works: 2150, category: 'RQ₂ · Self-Help, Psychology & Hybrid' },
  { publisher: 'Gütersloher Verlagshaus', passages: 10823, works: 3120, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Fischer', passages: 10652, works: 2410, category: 'RQ₃ · Critical & Secular-Humanist' },
  { publisher: 'Herder', passages: 10511, works: 6420, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Evangelische Verlagsanstalt', passages: 9984, works: 4510, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'C.H. Beck', passages: 9020, works: 3280, category: 'RQ₃ · Critical & Secular-Humanist' },
  { publisher: 'Rowohlt', passages: 8879, works: 2190, category: 'RQ₃ · Critical & Secular-Humanist' },
  { publisher: 'Nomos / Alber', passages: 8280, works: 2840, category: 'Academic & Philosophical' },
  { publisher: 'Gütersloher Verlagshaus (Chr. Kaiser)', passages: 7941, works: 1920, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Echter', passages: 6668, works: 2340, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Springer Nature (Holtzbrinck)', passages: 6457, works: 2180, category: 'Academic & Philosophical' },
  { publisher: 'Herder (Grünewald)', passages: 6336, works: 2490, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Meiner', passages: 6118, works: 1390, category: 'Academic & Philosophical' },
  { publisher: 'Pustet', passages: 6023, works: 1980, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Patmos', passages: 4970, works: 2140, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Kösel', passages: 4225, works: 2080, category: 'RQ₂ · Self-Help, Psychology & Hybrid' },
  { publisher: 'Schwabe', passages: 4048, works: 1120, category: 'Academic & Philosophical' },
  { publisher: 'Calwer', passages: 3354, works: 1240, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Wallstein', passages: 2911, works: 980, category: 'RQ₃ · Critical & Secular-Humanist' },
  { publisher: 'Insel', passages: 2698, works: 890, category: 'RQ₃ · Critical & Secular-Humanist' },
  { publisher: 'Bonifatius', passages: 2415, works: 1050, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Kiepenheuer', passages: 2401, works: 760, category: 'RQ₃ · Critical & Secular-Humanist' },
  { publisher: 'Herder (Benziger)', passages: 2390, works: 940, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Herder (Kreuz)', passages: 2119, works: 1320, category: 'RQ₂ · Self-Help, Psychology & Hybrid' },
  { publisher: 'Peter Lang', passages: 2044, works: 1150, category: 'Academic & Philosophical' },
  { publisher: 'Wagenbach', passages: 1023, works: 490, category: 'RQ₃ · Critical & Secular-Humanist' },
  { publisher: 'LIT Verlag', passages: 962, works: 680, category: 'Academic & Philosophical' },
  { publisher: 'TVZ (Theologischer Verlag Zürich)', passages: 808, works: 590, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Bibelwelt-Verlag', passages: 723, works: 410, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Alibri', passages: 587, works: 390, category: 'RQ₃ · Critical & Secular-Humanist' },
  { publisher: 'Patmos (Schwabenverlag)', passages: 556, works: 380, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Budrich', passages: 543, works: 310, category: 'RQ₃ · Critical & Secular-Humanist' },
  { publisher: 'Brill', passages: 526, works: 290, category: 'Academic & Philosophical' },
  { publisher: 'Luther-Verlag', passages: 305, works: 210, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Duncker & Humblot', passages: 287, works: 195, category: 'Academic & Philosophical' },
  { publisher: 'SCM R. Brockhaus', passages: 265, works: 215, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'St. Benno Verlag', passages: 240, works: 190, category: 'RQ₁ · Theological & Confessional' },
  { publisher: 'Gräfe und Unzer (GU)', passages: 220, works: 175, category: 'RQ₂ · Self-Help, Psychology & Hybrid' },
  { publisher: 'J. Kamphausen', passages: 195, works: 155, category: 'RQ₂ · Self-Help, Psychology & Hybrid' },
];

export function inferPublisherCategory(pub: string): string {
  const p = pub.toLowerCase();
  if (
    /herder|vandenhoeck|mohr|kohlhammer|aschendorff|neukirchener|gütersloher|kaiser|evangelisch|echter|grünewald|pustet|patmos|calwer|bonifatius|benziger|tvz|theologisch|bibel|luther|benno|brockhaus|scm|schwabenverlag|brunnen|butzon|bosco|eos|paulinus|wichern|lembeck/.test(
      p
    ) &&
    !/kreuz/.test(p)
  ) {
    return 'RQ₁ · Theological & Confessional';
  }
  if (
    /kösel|koesel|kreuz|klett|gräfe|gu\b|kamphausen|beltz|hogrefe|psychosozial|junfermann|arkana|knaur|goldmann|windpferd|schirner|scorpio|theseus|integral/.test(
      p
    )
  ) {
    return 'RQ₂ · Self-Help, Psychology & Hybrid';
  }
  if (
    /suhrkamp|fischer|beck\b|rowohlt|campus|insel|wallstein|kiepenheuer|wagenbach|alibri|budrich|reclam|hanser|piper|ullstein|dtv|matthes|diaphanes|velbrück|oekom|dietz|vsa|nautilus/.test(
      p
    )
  ) {
    return 'RQ₃ · Critical & Secular-Humanist';
  }
  return 'Academic & Philosophical';
}

export const TrendsGraph: React.FC<TrendsGraphProps> = ({
  data,
  publishers,
  publisherCounts = {},
  publisherWorksCounts = {},
  publisherDirectory = [],
  selectedPublishers = [],
  onTogglePublisher,
  decadeBreakdown = {},
  topics = [],
  selectedTopicIndex,
  onSelectTopicIndex,
  onYearClick,
  selectedYear,
  onDecadeClick,
  selectedDecade,
  onResetTemporal,
  compact = false,
}) => {
  const [hiddenPublishers, setHiddenPublishers] = useState<Record<string, boolean>>({});
  const [hiddenTopics, setHiddenTopics] = useState<Record<string, boolean>>({});
  const [chartMode, setChartMode] = useState<'yearly_imprints' | 'topic_lines' | 'decade_topics'>(
    'yearly_imprints'
  );
  const [pubSearch, setPubSearch] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<
    'ALL' | 'RQ1' | 'RQ2' | 'RQ3' | 'ACADEMIC'
  >('ALL');
  const [expandAllPills, setExpandAllPills] = useState<boolean>(true);

  // Build the comprehensive publisher directory from all available sources
  const fullDirectory: PublisherDirectoryEntry[] = useMemo(() => {
    const map = new Map<string, PublisherDirectoryEntry>();

    // 1. Seed from explicit publisherDirectory prop if present
    publisherDirectory.forEach((entry) => {
      if (entry.publisher && entry.publisher !== '_total') {
        map.set(entry.publisher, {
          publisher: entry.publisher,
          passages: entry.passages || publisherCounts[entry.publisher] || 0,
          works: entry.works || publisherWorksCounts[entry.publisher],
          category: entry.category || inferPublisherCategory(entry.publisher),
        });
      }
    });

    // 2. Merge from publisherCounts
    Object.entries(publisherCounts).forEach(([pub, cnt]) => {
      if (!pub || pub === '_total') return;
      if (!map.has(pub)) {
        map.set(pub, {
          publisher: pub,
          passages: Number(cnt) || 0,
          works: publisherWorksCounts[pub],
          category: inferPublisherCategory(pub),
        });
      }
    });

    // 3. Merge from trends data keys (summing annual counts if not in publisherCounts)
    if (Array.isArray(data) && data.length > 0) {
      const annualSums: Record<string, number> = {};
      data.forEach((row) => {
        Object.entries(row || {}).forEach(([k, v]) => {
          if (k === 'year' || k === 'year_clean' || k === '_total') return;
          annualSums[k] = (annualSums[k] || 0) + (Number(v) || 0);
        });
      });
      Object.entries(annualSums).forEach(([pub, sumCnt]) => {
        if (
          /^(universität|universitätsbibliothek|ub |staats-|landesbibliothek|ssoar|dipf|dnb monograph|open access book)/i.test(
            pub
          ) &&
          !map.has(pub)
        ) {
          return;
        }
        const existing = map.get(pub);
        if (existing) {
          if (!existing.passages && sumCnt > 0) existing.passages = sumCnt;
        } else {
          map.set(pub, {
            publisher: pub,
            passages: sumCnt,
            works: publisherWorksCounts[pub],
            category: inferPublisherCategory(pub),
          });
        }
      });
    }

    // 4. Merge from publishers prop and fallback comprehensive list so all canonical imprints are always present
    publishers.forEach((pub) => {
      if (!pub || pub === '_total') return;
      if (!map.has(pub)) {
        map.set(pub, {
          publisher: pub,
          passages: publisherCounts[pub] || 0,
          works: publisherWorksCounts[pub],
          category: inferPublisherCategory(pub),
        });
      }
    });

    COMPREHENSIVE_FALLBACK_PUBLISHERS.forEach((fb) => {
      if (!map.has(fb.publisher)) {
        map.set(fb.publisher, fb);
      } else {
        const cur = map.get(fb.publisher)!;
        if (!cur.passages) cur.passages = fb.passages;
        if (!cur.works) cur.works = fb.works;
      }
    });

    return Array.from(map.values()).sort((a, b) => b.passages - a.passages);
  }, [publisherDirectory, publisherCounts, publisherWorksCounts, data, publishers]);

  const allPublisherNames = useMemo(
    () => fullDirectory.map((d) => d.publisher),
    [fullDirectory]
  );

  // Filter directory by search query and category tab
  const filteredDirectory = useMemo(() => {
    return fullDirectory.filter((item) => {
      if (pubSearch.trim()) {
        const q = pubSearch.toLowerCase();
        if (
          !item.publisher.toLowerCase().includes(q) &&
          !item.category.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      if (categoryFilter === 'RQ1') return item.category.includes('RQ₁');
      if (categoryFilter === 'RQ2') return item.category.includes('RQ₂');
      if (categoryFilter === 'RQ3') return item.category.includes('RQ₃');
      if (categoryFilter === 'ACADEMIC') return item.category.includes('Academic');
      return true;
    });
  }, [fullDirectory, pubSearch, categoryFilter]);

  const togglePublisher = (pub: string) => {
    setHiddenPublishers((prev) => ({
      ...prev,
      [pub]: !prev[pub],
    }));
  };

  const isolateSinglePublisher = (pub: string) => {
    const nextHidden: Record<string, boolean> = {};
    allPublisherNames.forEach((p) => {
      nextHidden[p] = p !== pub;
    });
    setHiddenPublishers(nextHidden);
    if (onTogglePublisher) {
      onTogglePublisher(pub);
    }
  };

  const showAllPublishers = () => {
    setHiddenPublishers({});
  };

  const showTop15Only = () => {
    const nextHidden: Record<string, boolean> = {};
    allPublisherNames.forEach((p, idx) => {
      nextHidden[p] = idx >= 15;
    });
    setHiddenPublishers(nextHidden);
  };

  const showCoreRqImprintsOnly = () => {
    const coreSet = new Set([
      'Herder',
      'Vandenhoeck & Ruprecht',
      'Mohr Siebeck',
      'Kohlhammer',
      'Gütersloher Verlagshaus',
      'Evangelische Verlagsanstalt',
      'Patmos',
      'Kösel',
      'Klett-Cotta',
      'Herder (Kreuz)',
      'Gräfe und Unzer (GU)',
      'J. Kamphausen',
      'Suhrkamp',
      'Fischer',
      'C.H. Beck',
      'Rowohlt',
      'Campus',
      'Alibri',
    ]);
    const nextHidden: Record<string, boolean> = {};
    allPublisherNames.forEach((p) => {
      nextHidden[p] = !coreSet.has(p);
    });
    setHiddenPublishers(nextHidden);
  };

  const hideAllPublishers = () => {
    const nextHidden: Record<string, boolean> = {};
    allPublisherNames.forEach((p) => {
      nextHidden[p] = true;
    });
    setHiddenPublishers(nextHidden);
  };

  const visibleCount = useMemo(
    () => allPublisherNames.filter((p) => !hiddenPublishers[p]).length,
    [allPublisherNames, hiddenPublishers]
  );

  // Transform decadeBreakdown = { "1970s": { "Topic 1": 12.3, ... }, ... } into Recharts array
  const decadeChartData = Object.entries(decadeBreakdown).map(([decLabel, topicMap]) => ({
    decade: decLabel,
    ...(topicMap || {}),
  }));

  const topicKeys =
    decadeChartData.length > 0
      ? Object.keys(decadeChartData[0]).filter((k) => k !== 'decade')
      : [];

  // Map each "Topic N" key to its rich Topic metadata (assigned/custom label, regime color, 1970s->2020s Δ)
  const topicSeriesMeta = useMemo(() => {
    return topicKeys.map((tKey, idx) => {
      const matchedTopic =
        topics.find((t) => `Topic ${t.id + 1}` === tKey) || topics[idx];
      const theme = getArchetypeTheme(matchedTopic?.archetype?.label);
      const displayLbl = matchedTopic
        ? `T${String(matchedTopic.id + 1).padStart(2, '0')} · ${getTopicDisplayLabel(matchedTopic)}`
        : tKey;
      const s1970 = Number((decadeBreakdown['1970s'] || {})[tKey] ?? matchedTopic?.prevalence ?? 8.3);
      const s2020 = Number((decadeBreakdown['2020s'] || {})[tKey] ?? matchedTopic?.prevalence ?? 8.3);
      const delta = Number((s2020 - s1970).toFixed(2));
      return {
        key: tKey,
        index: idx,
        topicId: matchedTopic?.id ?? idx,
        displayLabel: displayLbl,
        color: matchedTopic ? theme.hex : FALLBACK_COLORS[idx % FALLBACK_COLORS.length],
        delta,
        assignedLabels: matchedTopic?.assigned_labels || [],
      };
    });
  }, [topicKeys, topics, decadeBreakdown]);

  const toggleTopicVisibility = (tKey: string) => {
    setHiddenTopics((prev) => ({
      ...prev,
      [tKey]: !prev[tKey],
    }));
  };

  const isolateSingleTopic = (tKey: string, topicIdx: number) => {
    const nextHidden: Record<string, boolean> = {};
    topicKeys.forEach((k) => {
      nextHidden[k] = k !== tKey;
    });
    setHiddenTopics(nextHidden);
    if (onSelectTopicIndex) {
      onSelectTopicIndex(topicIdx);
    }
  };

  const showAllTopics = () => setHiddenTopics({});

  const CustomYearlyTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const nonZero = [...payload]
        .filter((item: any) => Number(item.value) > 0)
        .sort((a: any, b: any) => (Number(b.value) || 0) - (Number(a.value) || 0));
      const total = nonZero.reduce((acc: number, item: any) => acc + (Number(item.value) || 0), 0);
      const topShown = nonZero.slice(0, 14);
      const remainingCount = Math.max(0, nonZero.length - topShown.length);

      return (
        <div className="bg-obsidian-900/95 backdrop-blur-xl border border-white/15 p-3 rounded-lg shadow-archival min-w-[235px]">
          <div className="flex items-center justify-between pb-1.5 mb-2 border-b border-white/10">
            <div className="flex items-center gap-1.5">
              <Calendar className="w-3 h-3 text-traditional" />
              <span className="font-serif font-bold text-sm text-parchment-50">
                Jahrgang {label}
              </span>
            </div>
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-parchment-200">
              Σ = {total.toLocaleString()} ({nonZero.length} Imprints)
            </span>
          </div>
          <div className="space-y-1">
            {topShown.map((entry: any, index: number) => (
              <div key={index} className="flex items-center justify-between gap-3 text-[11px]">
                <div className="flex items-center gap-1.5 truncate">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: entry.color }}
                  />
                  <span className="text-parchment-200 truncate max-w-[145px]">{entry.name}</span>
                </div>
                <span
                  className="font-mono font-semibold tabular-nums"
                  style={{ color: entry.color }}
                >
                  {Number(entry.value).toLocaleString()}
                </span>
              </div>
            ))}
            {remainingCount > 0 && (
              <div className="text-[10px] font-mono text-parchment-300 pt-1 border-t border-white/5">
                + {remainingCount} additional active imprints in {label}
              </div>
            )}
          </div>
          <div className="mt-2 pt-1.5 border-t border-white/10 flex items-center justify-between text-[9px] font-mono text-traditional">
            <span>Click point to slice LDA by Year</span>
            <span>→</span>
          </div>
        </div>
      );
    }
    return null;
  };

  const CustomDecadeTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const sorted = [...payload]
        .filter((p: any) => Number(p.value) > 0)
        .sort((a: any, b: any) => (b.value || 0) - (a.value || 0))
        .slice(0, 10);

      return (
        <div className="bg-obsidian-900/95 backdrop-blur-xl border border-white/15 p-3 rounded-lg shadow-archival min-w-[245px]">
          <div className="flex items-center justify-between pb-1.5 mb-2 border-b border-white/10">
            <span className="font-serif font-bold text-sm text-parchment-50">
              Decade Cohort: {label}
            </span>
            <span className="font-mono text-[10px] text-traditional">Topic Share %</span>
          </div>
          <div className="space-y-1">
            {sorted.map((entry: any, idx: number) => {
              const meta = topicSeriesMeta.find((m) => m.key === entry.dataKey || m.displayLabel === entry.name);
              return (
                <div key={idx} className="flex items-center justify-between gap-3 text-[11px]">
                  <div className="flex items-center gap-1.5 truncate">
                    <span
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{ backgroundColor: meta?.color || entry.color || entry.fill }}
                    />
                    <span className="font-mono text-parchment-200 truncate max-w-[180px]">
                      {meta?.displayLabel || entry.name}
                    </span>
                  </div>
                  <span className="font-mono font-semibold tabular-nums text-parchment-50">
                    {Number(entry.value).toFixed(1)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="w-full h-full archival-panel rounded-xl p-4 sm:p-5 flex flex-col justify-between"
    >
      <div>
        {/* Header Bar with Mode Switcher (Yearly Imprints vs Topic Trends vs Decade Stack) */}
        <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-2.5 border-b border-white/[0.07]">
          <div>
            <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
              <span className="px-2 py-0.5 rounded bg-traditional/10 border border-traditional/30 font-mono text-[10px] uppercase tracking-widest text-traditional">
                Diachronic Monitor · {allPublisherNames.length} Canonical Imprints · {topicSeriesMeta.length || 12} Latent Topics
              </span>
              {selectedYear && (
                <span className="px-2 py-0.5 rounded bg-neoliberal/15 border border-neoliberal/40 font-mono text-[10px] text-neoliberal">
                  Year: {selectedYear}
                </span>
              )}
              {selectedDecade && (
                <span className="px-2 py-0.5 rounded bg-critical/15 border border-critical/40 font-mono text-[10px] text-critical">
                  Decade: {selectedDecade}s
                </span>
              )}
            </div>
            <h3 className="font-serif text-lg sm:text-xl font-bold text-parchment-50">
              {chartMode === 'yearly_imprints'
                ? 'Annual Imprint Output & Temporal Slicer'
                : chartMode === 'topic_lines'
                ? 'Diachronic Topic Trend Trajectories (1970s–2020s)'
                : 'Decade Topic Share Stack (1970s–2020s)'}
            </h3>
          </div>

          <div className="flex items-center gap-1.5">
            {/* Sub-View Switcher */}
            <div className="flex items-center bg-obsidian-950 p-0.5 rounded-lg border border-white/10">
              <button
                onClick={() => setChartMode('yearly_imprints')}
                className={clsx(
                  'px-2 py-1 rounded-md font-mono text-[10px] transition-all cursor-pointer flex items-center gap-1',
                  chartMode === 'yearly_imprints'
                    ? 'bg-traditional text-obsidian-950 font-bold'
                    : 'text-parchment-300 hover:text-parchment-100'
                )}
              >
                <TrendingUp className="w-3 h-3" />
                <span>Imprints ({allPublisherNames.length})</span>
              </button>
              <button
                onClick={() => setChartMode('topic_lines')}
                className={clsx(
                  'px-2 py-1 rounded-md font-mono text-[10px] transition-all cursor-pointer flex items-center gap-1',
                  chartMode === 'topic_lines'
                    ? 'bg-traditional text-obsidian-950 font-bold'
                    : 'text-parchment-300 hover:text-parchment-100'
                )}
              >
                <TrendingUp className="w-3 h-3" />
                <span>Topic Trends</span>
              </button>
              <button
                onClick={() => setChartMode('decade_topics')}
                className={clsx(
                  'px-2 py-1 rounded-md font-mono text-[10px] transition-all cursor-pointer flex items-center gap-1',
                  chartMode === 'decade_topics'
                    ? 'bg-traditional text-obsidian-950 font-bold'
                    : 'text-parchment-300 hover:text-parchment-100'
                )}
              >
                <Layers className="w-3 h-3" />
                <span>Topic Stack</span>
              </button>
            </div>

            {(selectedYear || selectedDecade || selectedPublishers.length > 0) && onResetTemporal && (
              <button
                onClick={onResetTemporal}
                className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono bg-traditional/15 hover:bg-traditional/25 text-traditional border border-traditional/40 transition-colors cursor-pointer"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Reset</span>
              </button>
            )}
          </div>
        </div>

        {/* Decade Cohort Quick-Slice Bar (1970s - 2020s) */}
        <div className="flex items-center justify-between gap-1.5 mb-2.5 pb-2 border-b border-white/[0.05] overflow-x-auto custom-scrollbar">
          <span className="font-mono text-[9px] uppercase tracking-widest text-parchment-300 shrink-0">
            Decade Slice:
          </span>
          <div className="flex items-center gap-1">
            {DECADE_COHORTS.map((dec) => {
              const isSelected = selectedDecade === dec.value;
              return (
                <button
                  key={dec.value}
                  onClick={() => onDecadeClick && onDecadeClick(dec.value)}
                  className={clsx(
                    'px-2 py-0.5 rounded font-mono text-[10px] border transition-all cursor-pointer',
                    isSelected
                      ? 'bg-traditional text-obsidian-950 border-traditional font-bold shadow-glow-gold'
                      : 'bg-obsidian-950/70 border-white/10 text-parchment-200 hover:border-traditional/40'
                  )}
                >
                  {dec.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Comprehensive Publisher Options & Filter Console (shown in Yearly Imprints mode) */}
        {chartMode === 'yearly_imprints' && (
          <div className="mb-2.5 space-y-2 bg-obsidian-950/70 p-2.5 rounded-lg border border-white/[0.06]">
            {/* Row A: Search Input + Category Regime Tabs + Preset Controls */}
            <div className="flex flex-wrap items-center justify-between gap-1.5">
              <div className="relative flex-1 min-w-[170px]">
                <Search className="w-3 h-3 text-parchment-300 absolute left-2 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={pubSearch}
                  onChange={(e) => setPubSearch(e.target.value)}
                  placeholder={`Search all ${allPublisherNames.length} publishers (Herder, Suhrkamp, Kösel, Mohr, Beck, GU)...`}
                  className="w-full bg-obsidian-900 border border-white/10 rounded pl-6 pr-2 py-1 text-[10px] font-mono text-parchment-100 placeholder:text-parchment-300/50 focus:outline-none focus:border-traditional"
                />
              </div>

              <div className="flex flex-wrap items-center gap-1 font-mono text-[9px]">
                {(
                  [
                    { id: 'ALL', label: `All (${allPublisherNames.length})` },
                    { id: 'RQ1', label: 'RQ₁ Theo' },
                    { id: 'RQ2', label: 'RQ₂ Self-Help' },
                    { id: 'RQ3', label: 'RQ₃ Secular' },
                    { id: 'ACADEMIC', label: 'Academic' },
                  ] as const
                ).map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setCategoryFilter(tab.id)}
                    className={clsx(
                      'px-1.5 py-0.5 rounded border transition-colors cursor-pointer',
                      categoryFilter === tab.id
                        ? 'bg-traditional/20 border-traditional text-traditional font-bold'
                        : 'bg-obsidian-900 border-white/10 text-parchment-300 hover:text-parchment-100'
                    )}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Row B: Quick Visibility & Selection Actions */}
            <div className="flex flex-wrap items-center justify-between gap-1.5 pt-1 border-t border-white/[0.05] font-mono text-[9px]">
              <span className="text-parchment-300 flex items-center gap-1">
                <Filter className="w-2.5 h-2.5 text-traditional" />
                Showing <strong className="text-parchment-100">{filteredDirectory.length}</strong> options ·{' '}
                <strong className="text-emerald-300">{visibleCount}</strong> lines plotted (click to toggle, double-click to isolate & slice):
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={showAllPublishers}
                  className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 cursor-pointer"
                >
                  <Eye className="w-2.5 h-2.5" />
                  <span>All ({allPublisherNames.length})</span>
                </button>
                <button
                  onClick={showTop15Only}
                  className="px-1.5 py-0.5 rounded bg-white/5 hover:bg-white/10 text-parchment-200 border border-white/10 cursor-pointer"
                >
                  Top 15
                </button>
                <button
                  onClick={showCoreRqImprintsOnly}
                  className="px-1.5 py-0.5 rounded bg-traditional/15 hover:bg-traditional/25 text-traditional border border-traditional/30 cursor-pointer"
                >
                  Core RQ₁–RQ₃ (18)
                </button>
                <button
                  onClick={hideAllPublishers}
                  className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 cursor-pointer"
                >
                  <EyeOff className="w-2.5 h-2.5" />
                  <span>Clear</span>
                </button>
                <button
                  onClick={() => setExpandAllPills((prev) => !prev)}
                  className="px-1.5 py-0.5 rounded bg-white/5 hover:bg-white/10 text-parchment-300 border border-white/10 cursor-pointer"
                >
                  {expandAllPills ? 'Compact List' : 'Expand All'}
                </button>
              </div>
            </div>

            {/* Row C: Comprehensive Publisher Pill Grid */}
            <div
              className={clsx(
                'flex flex-wrap items-center gap-1.5 overflow-y-auto pr-1 custom-scrollbar',
                expandAllPills ? 'max-h-[135px]' : 'max-h-[62px]'
              )}
            >
              {filteredDirectory.map((entry, idx) => {
                const pub = entry.publisher;
                const color =
                  PUBLISHER_COLORS[pub] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length];
                const isHidden = !!hiddenPublishers[pub];
                const isLdaSliced = selectedPublishers.includes(pub);
                const countLabel =
                  entry.passages >= 1000
                    ? `${(entry.passages / 1000).toFixed(1)}k`
                    : String(entry.passages || '');

                return (
                  <button
                    key={pub}
                    onClick={() => togglePublisher(pub)}
                    onDoubleClick={() => isolateSinglePublisher(pub)}
                    title={`${pub} — ${entry.passages.toLocaleString()} passages${
                      entry.works ? ` · ${entry.works.toLocaleString()} unique works` : ''
                    } (${entry.category}). Click to toggle chart line; double-click to isolate & slice LDA model.`}
                    className={clsx(
                      'inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-[10px] font-mono transition-all cursor-pointer',
                      isLdaSliced
                        ? 'bg-traditional/20 border-traditional text-parchment-50 font-bold shadow-glow-gold'
                        : isHidden
                        ? 'bg-obsidian-950/40 border-white/5 text-parchment-300/40 line-through'
                        : 'bg-obsidian-900/90 border-white/10 text-parchment-100 hover:border-white/25'
                    )}
                  >
                    <span
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{ backgroundColor: isHidden ? '#52525B' : color }}
                    />
                    <span className="truncate max-w-[140px]">{pub}</span>
                    {countLabel && (
                      <span className="text-[8px] px-1 rounded bg-white/[0.05] text-parchment-300 tabular-nums">
                        {countLabel}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Interactive Topic Trend Selector & Legend Bar (shown in Topic Trends & Topic Stack modes) */}
        {(chartMode === 'topic_lines' || chartMode === 'decade_topics') && topicSeriesMeta.length > 0 && (
          <div className="mb-2.5 space-y-2 bg-obsidian-950/70 p-2.5 rounded-lg border border-white/[0.06]">
            <div className="flex flex-wrap items-center justify-between gap-1.5 font-mono text-[9px]">
              <span className="text-parchment-300 flex items-center gap-1">
                <Layers className="w-2.5 h-2.5 text-traditional" />
                <span>
                  Plotted Topic Trajectories (1970s–2020s) — click to toggle curve, double-click to isolate & inspect topic:
                </span>
              </span>
              <button
                onClick={showAllTopics}
                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 cursor-pointer"
              >
                <Eye className="w-2.5 h-2.5" />
                <span>Show All ({topicSeriesMeta.length})</span>
              </button>
            </div>
            <div className="flex flex-wrap items-center gap-1.5 max-h-[110px] overflow-y-auto pr-1 custom-scrollbar">
              {topicSeriesMeta.map((meta) => {
                const isHidden = !!hiddenTopics[meta.key];
                const isSelectedTopic = selectedTopicIndex === meta.index;
                return (
                  <button
                    key={meta.key}
                    onClick={() => toggleTopicVisibility(meta.key)}
                    onDoubleClick={() => isolateSingleTopic(meta.key, meta.index)}
                    title={`${meta.displayLabel} (55-yr Δ: ${meta.delta >= 0 ? `+${meta.delta}%` : `${meta.delta}%`}). Click to toggle curve; double-click to isolate & inspect.`}
                    className={clsx(
                      'inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-[10px] font-mono transition-all cursor-pointer',
                      isSelectedTopic
                        ? 'bg-traditional/20 border-traditional text-parchment-50 font-bold shadow-glow-gold'
                        : isHidden
                        ? 'bg-obsidian-950/40 border-white/5 text-parchment-300/40 line-through'
                        : 'bg-obsidian-900/90 border-white/10 text-parchment-100 hover:border-white/25'
                    )}
                  >
                    <span
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{ backgroundColor: isHidden ? '#52525B' : meta.color }}
                    />
                    <span className="truncate max-w-[165px]">{meta.displayLabel}</span>
                    <span
                      className={clsx(
                        'text-[8px] px-1 rounded tabular-nums',
                        meta.delta > 0.1
                          ? 'bg-emerald-500/15 text-emerald-300'
                          : meta.delta < -0.1
                          ? 'bg-rose-500/15 text-rose-300'
                          : 'bg-white/[0.05] text-parchment-300'
                      )}
                    >
                      {meta.delta >= 0 ? `+${meta.delta}%` : `${meta.delta}%`}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Main Chart Container */}
      <div className={clsx('w-full', compact ? 'h-[235px]' : 'h-[330px]')}>
        <ResponsiveContainer width="100%" height="100%">
          {chartMode === 'yearly_imprints' ? (
            <LineChart
              data={data}
              margin={{ top: 8, right: 14, left: -14, bottom: 4 }}
              onClick={(e: any) => {
                if (e && e.activeLabel && onYearClick) {
                  onYearClick(Number(e.activeLabel));
                }
              }}
            >
              <CartesianGrid
                strokeDasharray="2 4"
                stroke="rgba(255,255,255,0.06)"
                vertical={true}
              />
              <XAxis
                dataKey="year"
                stroke="#6E6D68"
                fontSize={10}
                tickLine={false}
                axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                dy={6}
                fontFamily="JetBrains Mono, monospace"
              />
              <YAxis
                stroke="#6E6D68"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                dx={-4}
                fontFamily="JetBrains Mono, monospace"
              />
              <Tooltip
                content={<CustomYearlyTooltip />}
                cursor={{
                  stroke: '#C99A5B',
                  strokeWidth: 1,
                  strokeDasharray: '4 4',
                }}
              />
              {selectedYear && (
                <ReferenceLine
                  x={selectedYear}
                  stroke="#C99A5B"
                  strokeWidth={2}
                  strokeDasharray="3 3"
                />
              )}
              {allPublisherNames.map((pub, idx) => {
                if (hiddenPublishers[pub]) return null;
                if (
                  selectedPublishers.length > 0 &&
                  !selectedPublishers.some(
                    (sp) =>
                      sp.toLowerCase() === pub.toLowerCase() ||
                      pub.toLowerCase().includes(sp.toLowerCase()) ||
                      sp.toLowerCase().includes(pub.toLowerCase())
                  )
                ) {
                  return null;
                }
                const color =
                  PUBLISHER_COLORS[pub] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length];
                return (
                  <Line
                    key={pub}
                    type="monotone"
                    dataKey={pub}
                    name={pub}
                    stroke={color}
                    strokeWidth={selectedPublishers.length > 0 ? 2.5 : 1.8}
                    dot={false}
                    activeDot={{
                      r: 4.5,
                      fill: color,
                      stroke: '#070709',
                      strokeWidth: 1.5,
                      cursor: 'pointer',
                      onClick: (_: any, payload: any) => {
                        if (payload && payload.payload && onYearClick) {
                          const yVal = payload.payload.year ?? payload.payload.year_clean;
                          if (yVal) onYearClick(Number(yVal));
                        }
                      },
                    }}
                  />
                );
              })}
            </LineChart>
          ) : chartMode === 'topic_lines' ? (
            <LineChart
              data={decadeChartData}
              margin={{ top: 8, right: 14, left: -14, bottom: 4 }}
              onClick={(e: any) => {
                if (e && e.activeLabel && onDecadeClick) {
                  const num = parseInt(String(e.activeLabel).replace(/\D/g, ''), 10);
                  if (!isNaN(num)) onDecadeClick(num);
                }
              }}
            >
              <CartesianGrid
                strokeDasharray="2 4"
                stroke="rgba(255,255,255,0.06)"
                vertical={true}
              />
              <XAxis
                dataKey="decade"
                stroke="#ECE8DF"
                fontSize={10}
                tickLine={false}
                axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                fontFamily="JetBrains Mono, monospace"
              />
              <YAxis
                stroke="#6E6D68"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${v}%`}
                fontFamily="JetBrains Mono, monospace"
              />
              <Tooltip content={<CustomDecadeTooltip />} />
              {topicSeriesMeta.map((meta) => {
                if (hiddenTopics[meta.key]) return null;
                const isSelected = selectedTopicIndex === meta.index;
                return (
                  <Line
                    key={meta.key}
                    type="monotone"
                    dataKey={meta.key}
                    name={meta.displayLabel}
                    stroke={meta.color}
                    strokeWidth={isSelected ? 3.2 : 2.0}
                    dot={{ r: isSelected ? 4 : 2.5, fill: meta.color }}
                    activeDot={{
                      r: 5,
                      fill: meta.color,
                      stroke: '#070709',
                      strokeWidth: 1.5,
                      cursor: 'pointer',
                    }}
                  />
                );
              })}
            </LineChart>
          ) : (
            <BarChart
              data={decadeChartData}
              margin={{ top: 8, right: 14, left: -14, bottom: 4 }}
              onClick={(e: any) => {
                if (e && e.activeLabel && onDecadeClick) {
                  const num = parseInt(String(e.activeLabel).replace(/\D/g, ''), 10);
                  if (!isNaN(num)) onDecadeClick(num);
                }
              }}
            >
              <CartesianGrid
                strokeDasharray="2 4"
                stroke="rgba(255,255,255,0.06)"
                vertical={false}
              />
              <XAxis
                dataKey="decade"
                stroke="#ECE8DF"
                fontSize={10}
                tickLine={false}
                axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                fontFamily="JetBrains Mono, monospace"
              />
              <YAxis
                stroke="#6E6D68"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${v}%`}
                fontFamily="JetBrains Mono, monospace"
              />
              <Tooltip content={<CustomDecadeTooltip />} />
              {topicSeriesMeta.map((meta) => {
                if (hiddenTopics[meta.key]) return null;
                return (
                  <Bar
                    key={meta.key}
                    dataKey={meta.key}
                    name={meta.displayLabel}
                    stackId="decadeStack"
                    fill={meta.color}
                    fillOpacity={0.85}
                  />
                );
              })}
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Footer Hint */}
      <div className="mt-2 pt-2 border-t border-white/[0.06] flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-parchment-300">
        <span>
          {chartMode === 'yearly_imprints'
            ? 'Click any publisher pill to toggle line · Double-click pill to isolate & slice LDA · Click chart point to slice by Year'
            : 'Click any topic pill to toggle trajectory · Double-click topic pill to isolate & inspect · Click decade to slice corpus'}
        </span>
        <span className="text-traditional">
          {allPublisherNames.length} Canonical Imprints · 1970–2025
        </span>
      </div>
    </motion.div>
  );
};
