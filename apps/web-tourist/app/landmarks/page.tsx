"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getLandmarks, type Landmark } from "../lib/api";

const FEATURED_ROUTE_IDS = [
  "nanhou-street",
  "linjuemin-bingxin",
  "xiaohuanglou",
  "shuixie-stage",
] as const;

const THEME_FILTERS = [
  {
    key: "all",
    label: "全部",
    hint: "完整景点库",
    signals: [],
  },
  {
    key: "classic",
    label: "首次必看",
    hint: "主街与坊巷格局",
    signals: ["axis", "three-lanes", "seven-alleys", "nearby", "坊巷格局"],
  },
  {
    key: "people",
    label: "名人故居",
    hint: "家国与文学线索",
    signals: ["history", "literature", "education", "shipbuilding", "近代史", "思想史", "近代化"],
  },
  {
    key: "craft",
    label: "非遗夜游",
    hint: "演艺手作与小吃",
    signals: ["food", "performance", "intangible-heritage", "craft", "night", "非遗", "互动"],
  },
  {
    key: "architecture",
    label: "古厝建筑",
    hint: "马鞍墙与天井",
    signals: ["architecture", "courtyard", "urban-pattern", "photo", "古厝", "马鞍墙"],
  },
] as const;

type ThemeKey = (typeof THEME_FILTERS)[number]["key"];

const TAG_LABELS: Record<string, string> = {
  architecture: "建筑",
  area: "片区",
  art: "艺术",
  atmosphere: "氛围",
  axis: "中轴",
  culture: "文化",
  courtyard: "天井",
  craft: "手作",
  education: "教育",
  entrance: "入口",
  experience: "体验",
  food: "小吃",
  garden: "花园",
  "golden-hour": "黄金时刻",
  heritage: "遗产",
  history: "历史",
  interactive: "互动",
  landmark: "地标",
  lane: "街巷",
  literature: "文学",
  literati: "士人",
  morning: "清晨",
  nearby: "邻近",
  night: "夜游",
  nature: "自然",
  "official-culture": "仕宦",
  performance: "演艺",
  photography: "摄影",
  photo: "摄影",
  "photo-spot": "拍照点",
  "quiet-route": "清静线",
  rare: "少见",
  residence: "故居",
  romance: "情侣",
  selfie: "自拍",
  shipbuilding: "船政",
  "street-art": "街头艺术",
  tea: "茶文化",
  "intangible-heritage": "非遗",
  "seven-alleys": "七巷",
  "three-lanes": "三坊",
  "urban-pattern": "格局",
};

const CARD_TONES = ["jade", "gold", "cinnabar", "ink"] as const;

function tagLabel(tag: string) {
  return TAG_LABELS[tag] ?? tag;
}

function getAskHref(landmark: Landmark) {
  return `/?q=${encodeURIComponent(`${landmark.name}有什么看点？适合停留多久？`)}&autoSend=true`;
}

function getSearchText(landmark: Landmark) {
  const tags = landmark.tags.map((tag) => `${tag} ${tagLabel(tag)}`).join(" ");
  return `${landmark.name} ${landmark.summary} ${tags}`.toLowerCase();
}

function matchesTheme(landmark: Landmark, theme: ThemeKey) {
  const filter = THEME_FILTERS.find((item) => item.key === theme);
  if (!filter || filter.key === "all") return true;
  const searchText = getSearchText(landmark);
  return filter.signals.some((signal) => searchText.includes(signal.toLowerCase()));
}

function formatDuration(minutes: number) {
  if (minutes < 60) return `${minutes} 分钟`;
  const hours = minutes / 60;
  if (hours >= 10) return `约 ${Math.round(hours)} 小时`;
  return Number.isInteger(hours) ? `${hours} 小时` : `${hours.toFixed(1)} 小时`;
}

function getCuratedStops(landmarks: Landmark[]) {
  const featured = landmarks.filter((landmark) => landmark.is_featured);
  if (featured.length > 0) return featured.slice(0, 4);
  const landmarkById = new Map(landmarks.map((landmark) => [landmark.id, landmark]));
  const stops = FEATURED_ROUTE_IDS.flatMap((id) => {
    const landmark = landmarkById.get(id);
    return landmark ? [landmark] : [];
  });
  return stops.length > 0 ? stops : landmarks.slice(0, 4);
}

export default function LandmarksPage() {
  const [query, setQuery] = useState("");
  const [selectedTheme, setSelectedTheme] = useState<ThemeKey>("all");
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const { data: landmarks = [], isLoading, isFetching } = useQuery({
    queryKey: ["landmarks"],
    queryFn: () => getLandmarks(),
    staleTime: 1000 * 60 * 20,
  });

  const filteredLandmarks = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const selectedTagLabel = selectedTag ? tagLabel(selectedTag) : null;
    return landmarks.filter((landmark) => {
      const themeMatched = matchesTheme(landmark, selectedTheme);
      const tagMatched =
        !selectedTag ||
        landmark.tags.some(
          (tag) => tag === selectedTag || tagLabel(tag) === selectedTagLabel,
        );
      if (!normalizedQuery) return themeMatched && tagMatched;
      return (
        themeMatched &&
        tagMatched &&
        getSearchText(landmark).includes(normalizedQuery)
      );
    });
  }, [landmarks, query, selectedTag, selectedTheme]);

  const featuredLandmark = landmarks[0];
  const curatedStops = useMemo(() => getCuratedStops(landmarks), [landmarks]);
  const totalDuration = landmarks.reduce(
    (sum, landmark) => sum + (landmark.avg_duration_min ?? 18),
    0,
  );
  const hotTags = useMemo(() => {
    const counts = new Map<string, number>();
    for (const landmark of landmarks) {
      for (const tag of landmark.tags) {
        counts.set(tag, (counts.get(tag) ?? 0) + 1);
      }
    }
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([tag]) => tag);
  }, [landmarks]);

  return (
    <main className="tourist-frame landmarks-page">
      <section className="landmarks-hero" aria-labelledby="landmarks-title">
        <div className="landmarks-hero-copy">
          <p className="caption">三坊七巷景点库</p>
          <h1 id="landmarks-title">把散点变成一条会讲故事的街巷</h1>
          <p>
            从主街集合点、名人故居到非遗夜游，先挑主题，再让 AI 帮你把看点串成顺路的讲解。
          </p>
          <div className="landmarks-hero-actions">
            <Link className="primary-button" href="/route">
              按时间规划路线
            </Link>
            <Link className="thin-button" href="/photo">
              现场拍照识景
            </Link>
          </div>
        </div>

        <aside className="landmarks-hero-panel" aria-label="导览概览">
          <div className="landmarks-scenic-card">
            <div className="landmarks-scenic-photo" aria-hidden="true" />
            <div className="landmarks-scenic-body">
              <p className="caption">推荐起点</p>
              <h2>{featuredLandmark?.name ?? "南后街"}</h2>
              <p>
                {featuredLandmark?.summary ??
                  "三坊七巷的中轴步行街，适合作为首次到访的集合点与路线起点。"}
              </p>
              {featuredLandmark && (
                <Link className="landmark-inline-link" href={getAskHref(featuredLandmark)}>
                  听这一站的讲解
                </Link>
              )}
            </div>
          </div>
          <div className="landmarks-quick-stats">
            <span>
              <strong>{landmarks.length}</strong>
              景点
            </span>
            <span>
              <strong>{totalDuration ? formatDuration(totalDuration) : "待定"}</strong>
              累计停留
            </span>
            <span>
              <strong>{hotTags.length}</strong>
              高频线索
            </span>
          </div>
        </aside>
      </section>

      <section className="landmarks-console" aria-label="景点筛选">
        <label className="landmarks-search">
          <span className="landmarks-search-icon" aria-hidden="true">
            ⌕
          </span>
          <input
            type="search"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setSelectedTag(null);
            }}
            placeholder="搜索景点、主题、非遗、马鞍墙"
            aria-label="搜索景点"
          />
          {query ? (
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setSelectedTag(null);
              }}
              aria-label="清空搜索"
            >
              ×
            </button>
          ) : null}
        </label>

        <div className="landmark-filter-tabs" role="list" aria-label="主题筛选">
          {THEME_FILTERS.map((filter) => (
            <button
              key={filter.key}
              type="button"
              className={`landmark-filter-tab ${selectedTheme === filter.key ? "active" : ""}`}
              onClick={() => setSelectedTheme(filter.key)}
              role="listitem"
            >
              <span>{filter.label}</span>
              <small>{filter.hint}</small>
            </button>
          ))}
        </div>

        {hotTags.length > 0 && (
          <div className="landmark-hot-tags" aria-label="高频标签">
            {hotTags.map((tag) => (
              <button
                key={tag}
                type="button"
                className={selectedTag === tag ? "active" : ""}
                onClick={() => {
                  setSelectedTag((current) => (current === tag ? null : tag));
                  setQuery("");
                }}
              >
                {tagLabel(tag)}
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="landmarks-curation" aria-labelledby="landmarks-route-title">
        <div className="landmarks-section-heading">
          <div>
            <p className="caption">精选动线</p>
            <h2 id="landmarks-route-title">第一次来，先走这四站</h2>
          </div>
          <Link className="landmark-inline-link" href="/route">
            生成完整路线
          </Link>
        </div>

        <div className="landmark-route-strip">
          {curatedStops.map((landmark, index) => (
            <Link className="route-stop-card" href={getAskHref(landmark)} key={landmark.id}>
              <span className="route-stop-index">{String(index + 1).padStart(2, "0")}</span>
              <h3>{landmark.name}</h3>
              <p>{landmark.summary}</p>
            </Link>
          ))}
        </div>
      </section>

      <section className="landmarks-results" aria-labelledby="landmarks-list-title">
        <div className="landmarks-section-heading">
          <div>
            <p className="caption">景点清单</p>
            <h2 id="landmarks-list-title">
              {isLoading ? "正在整理景点" : `${filteredLandmarks.length} 个可讲解景点`}
            </h2>
          </div>
          <span className="landmarks-result-note">
            {selectedTag
              ? tagLabel(selectedTag)
              : selectedTheme === "all"
                ? "全部主题"
                : THEME_FILTERS.find((item) => item.key === selectedTheme)?.label}
          </span>
        </div>

        <div className="landmarks-grid">
          {filteredLandmarks.map((landmark, index) => (
            <Link
              href={getAskHref(landmark)}
              key={landmark.id}
              className={`landmark-card tone-${CARD_TONES[index % CARD_TONES.length]}`}
            >
              <span className="landmark-card-index">{String(index + 1).padStart(2, "0")}</span>
              <div className="landmark-info">
                <h3>{landmark.name}</h3>
                <p className="landmark-summary">{landmark.summary}</p>
              </div>
              <div className="landmark-tags">
                <span className="landmark-tag">
                  停留 {landmark.avg_duration_min ?? 18} 分钟
                </span>
                {landmark.tags.slice(0, 3).map((tag) => (
                  <span className="landmark-tag" key={tag}>
                    {tagLabel(tag)}
                  </span>
                ))}
              </div>
              <span className="landmark-card-action">去问知行</span>
            </Link>
          ))}
        </div>

        {!isLoading && filteredLandmarks.length === 0 && (
          <div className="landmarks-empty">
            <h3>没找到匹配的景点</h3>
            <p>换个关键词，或回到全部主题继续逛。</p>
            <button
              className="thin-button"
              type="button"
              onClick={() => {
                setQuery("");
                setSelectedTag(null);
                setSelectedTheme("all");
              }}
            >
              重置筛选
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
