"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { TrustBar, VisitorNav } from "../components/VisitorChrome";
import { getLandmarks } from "../lib/api";

export default function LandmarksPage() {
  const { data: landmarks = [] } = useQuery({
    queryKey: ["landmarks"],
    queryFn: () => getLandmarks(),
  });

  return (
    <main className="tourist-frame landmarks-page">
      <TrustBar mode="offline" />
      <VisitorNav />
      <section className="landmarks-header">
        <h1>三坊七巷 · 景点导览</h1>
        <p>共 {landmarks.length} 个景点</p>
      </section>
      <section className="landmarks-grid">
        {landmarks.map((lm) => (
          <Link href={`/?q=${encodeURIComponent(lm.name + "有什么看点")}`} key={lm.id} className="landmark-card">
            <div className="landmark-icon">
              {lm.tags?.includes("food") ? "🍜" :
               lm.tags?.includes("former-residence") ? "🏠" :
               lm.tags?.includes("architecture") ? "🏛" :
               lm.tags?.includes("performance") ? "🎭" :
               lm.tags?.includes("intangible-heritage") ? "🎨" :
               lm.tags?.includes("study") ? "📚" : "📍"}
            </div>
            <div className="landmark-info">
              <h3>{lm.name}</h3>
              <p className="landmark-summary">{lm.summary}</p>
              <div className="landmark-tags">
                {lm.avg_duration_min && (
                  <span className="landmark-tag">{lm.avg_duration_min} 分钟</span>
                )}
                {lm.tags?.slice(0, 3).map((tag) => (
                  <span className="landmark-tag" key={tag}>{tag}</span>
                ))}
              </div>
            </div>
          </Link>
        ))}
      </section>
    </main>
  );
}
