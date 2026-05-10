"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { TrustBar, VisitorNav } from "../components/VisitorChrome";
import { getRoute, type RoutePlan, type RoutePreferences } from "../lib/api";

const INTEREST_OPTIONS = [
  { key: "history", label: "历史人文" },
  { key: "architecture", label: "古厝建筑" },
  { key: "food", label: "美食小吃" },
  { key: "photo", label: "拍照打卡" },
  { key: "culture", label: "非遗文化" },
  { key: "literature", label: "文学故事" },
  { key: "nature", label: "自然景观" },
  { key: "family", label: "亲子互动" },
  { key: "night", label: "夜游体验" },
];

const DURATION_OPTIONS = [
  { value: 60, label: "1 小时" },
  { value: 120, label: "2 小时" },
  { value: 180, label: "3 小时" },
  { value: 240, label: "4 小时" },
];

const PACE_OPTIONS = [
  { value: "relaxed", label: "轻松休闲", desc: "少走路多休息" },
  { value: "moderate", label: "适中节奏", desc: "正常步行" },
  { value: "active", label: "活力满满", desc: "多走多看" },
] as const;

const GROUP_OPTIONS = [
  { value: "solo", label: "独自游览" },
  { value: "couple", label: "情侣出游" },
  { value: "family", label: "亲子家庭" },
  { value: "friends", label: "朋友结伴" },
  { value: "elder", label: "长者出行" },
] as const;

const AGE_OPTIONS = [
  { value: "kids", label: "12 岁以下" },
  { value: "12-17", label: "12-17 岁" },
  { value: "18-35", label: "18-35 岁" },
  { value: "36-55", label: "36-55 岁" },
  { value: "55+", label: "55 岁以上" },
] as const;

export default function RoutePage() {
  const [prefs, setPrefs] = useState<RoutePreferences>({
    gender: "unspecified",
    age_range: "18-35",
    interests: ["history", "architecture"],
    pace: "moderate",
    group_type: "solo",
    duration_minutes: 120,
  });

  const toggleInterest = (key: string) => {
    setPrefs((prev) => ({
      ...prev,
      interests: prev.interests.includes(key)
        ? prev.interests.filter((i) => i !== key)
        : [...prev.interests, key],
    }));
  };

  const routeMutation = useMutation({
    mutationFn: (prefs: RoutePreferences) => getRoute(prefs),
  });

  const handleGenerate = () => {
    routeMutation.mutate(prefs);
  };

  const route = routeMutation.data;

  return (
    <main className="tourist-frame route-page">
      <TrustBar mode={route ? "online" : "offline"} />
      <VisitorNav />

      {/* Preference form */}
      <section className="route-prefs">
        <p className="caption">AI 路线规划</p>
        <h1 className="type-heading type-heading-1">
          告诉我你的偏好，AI 为你生成专属路线
        </h1>

        <div className="pref-grid">
          {/* Group type */}
          <fieldset className="pref-group">
            <legend>出行类型</legend>
            <div className="chip-row">
              {GROUP_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`pref-chip ${prefs.group_type === opt.value ? "active" : ""}`}
                  onClick={() => setPrefs((p) => ({ ...p, group_type: opt.value }))}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </fieldset>

          {/* Age range */}
          <fieldset className="pref-group">
            <legend>年龄段</legend>
            <div className="chip-row">
              {AGE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`pref-chip ${prefs.age_range === opt.value ? "active" : ""}`}
                  onClick={() => setPrefs((p) => ({ ...p, age_range: opt.value }))}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </fieldset>

          {/* Gender */}
          <fieldset className="pref-group">
            <legend>性别</legend>
            <div className="chip-row">
              {[
                { value: "unspecified", label: "不限" },
                { value: "male", label: "男" },
                { value: "female", label: "女" },
              ].map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`pref-chip ${prefs.gender === opt.value ? "active" : ""}`}
                  onClick={() => setPrefs((p) => ({ ...p, gender: opt.value }))}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </fieldset>

          {/* Duration */}
          <fieldset className="pref-group">
            <legend>计划时长</legend>
            <div className="chip-row">
              {DURATION_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`pref-chip ${prefs.duration_minutes === opt.value ? "active" : ""}`}
                  onClick={() => setPrefs((p) => ({ ...p, duration_minutes: opt.value }))}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </fieldset>

          {/* Pace */}
          <fieldset className="pref-group">
            <legend>游览节奏</legend>
            <div className="chip-row">
              {PACE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`pref-chip ${prefs.pace === opt.value ? "active" : ""}`}
                  title={opt.desc}
                  onClick={() => setPrefs((p) => ({ ...p, pace: opt.value }))}
                >
                  {opt.label}
                  <span className="chip-desc">{opt.desc}</span>
                </button>
              ))}
            </div>
          </fieldset>

          {/* Interests */}
          <fieldset className="pref-group pref-group-full">
            <legend>兴趣偏好（多选）</legend>
            <div className="chip-row">
              {INTEREST_OPTIONS.map((opt) => (
                <button
                  key={opt.key}
                  type="button"
                  className={`pref-chip ${prefs.interests.includes(opt.key) ? "active" : ""}`}
                  onClick={() => toggleInterest(opt.key)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </fieldset>
        </div>

        <button
          className="primary-button route-generate-btn"
          type="button"
          onClick={handleGenerate}
          disabled={routeMutation.isPending || prefs.interests.length === 0}
        >
          {routeMutation.isPending ? "AI 正在生成路线..." : "生成专属路线"}
        </button>
      </section>

      {/* Loading state */}
      {routeMutation.isPending && (
        <section className="route-loading">
          <span className="thinking-dots" aria-label="AI 正在为你规划路线">
            <span />
            <span />
            <span />
          </span>
          <p className="type-body">AI 正在分析你的偏好，生成个性化路线...</p>
        </section>
      )}

      {/* Route result */}
      {route && !routeMutation.isPending && (
        <section className="route-result">
          <div className="route-intro">
            <p className="caption">专属路线</p>
            <p className="type-body">{route.intro}</p>
            <p className="route-stats">
              步行约 {route.total_walk_minutes} 分钟
              {route.total_duration_min > 0 && ` · 游览约 ${route.total_duration_min} 分钟`}
            </p>
          </div>

          <section className="timeline">
            {route.stops.map((stop, index) => (
              <article className="route-card" key={stop.landmark_id}>
                <div className="route-step-badge">
                  {index === 0 ? "起" : String(index + 1)}
                </div>
                <div className="route-step-body">
                  <h2 className="type-heading type-heading-2">{stop.name}</h2>
                  {stop.highlight && (
                    <p className="route-highlight">{stop.highlight}</p>
                  )}
                  <p className="type-body">{stop.reason}</p>
                  <div className="route-meta">
                    <span>停留约 {stop.duration_min} 分钟</span>
                    {index > 0 && (
                      <span>步行 {stop.walk_minutes_from_previous} 分钟</span>
                    )}
                  </div>
                </div>
                {index < route.stops.length - 1 && (
                  <div className="route-step-connector">
                    <span className="walk-dot" />
                    <span className="walk-label">
                      步行 {route.stops[index + 1]?.walk_minutes_from_previous ?? 0} 分钟
                    </span>
                    <span className="walk-dot" />
                  </div>
                )}
              </article>
            ))}
          </section>
        </section>
      )}
    </main>
  );
}
