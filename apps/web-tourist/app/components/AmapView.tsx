"use client";

import { useEffect, useRef, useState } from "react";

// Prefer the env-driven key so a prod build can swap in its own quota, but
// fall back to the repo demo key for local dev.
const AMAP_KEY =
  process.env.NEXT_PUBLIC_AMAP_KEY || "485e3836235de177b54deaa033a9801e";
const CENTER: [number, number] = [119.2966, 26.0842]; // 三坊七巷中心

// Minimal shape of the AMap globals we actually touch. Keeps TS honest
// without pulling in the full (and large) @amap/amap-jsapi-types package.
type AMapMarkerOptions = {
  position: [number, number];
  title?: string;
  label?: { content: string; direction: string; offset: unknown };
  content?: string;
  offset?: unknown;
};

type AMapInstance = {
  add: (markerOrList: unknown) => void;
  remove: (markers: unknown[]) => void;
  setCenter: (position: [number, number]) => void;
  destroy: () => void;
  plugin: (name: string, cb: () => void) => void;
};

type AMapGlobal = {
  Map: new (
    el: HTMLElement,
    opts: { zoom: number; center: [number, number]; mapStyle: string; viewMode: string },
  ) => AMapInstance;
  Marker: new (opts: AMapMarkerOptions) => unknown;
  Pixel: new (x: number, y: number) => unknown;
  Geolocation: new (opts: Record<string, unknown>) => {
    getCurrentPosition: (
      cb: (status: string, result: { position: { lat: number; lng: number } }) => void,
    ) => void;
  };
};

declare global {
  interface Window {
    AMap?: AMapGlobal;
  }
}

type Landmark = {
  id: string;
  name: string;
  geo_point?: { lat: number; lng: number } | null;
  tags?: string[];
};

/** Curated set of key landmarks shown on the homepage map. */
const FEATURED_IDS = new Set([
  "nanhou-street",
  "nanhou-street-north-archway",
  "yijin-lane",
  "wenru-lane",
  "linjuemin-bingxin",
  "yanfu-former-residence",
  "shenbaozhen-former-residence",
  "xiaohuanglou",
  "shuixie-stage",
  "huang-alley",
  "heart-tree",
  "fuzhou-intangible-heritage",
]);

function getDistance(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number,
): number {
  const R = 6371000;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

let amapLoaderPromise: Promise<AMapGlobal | null> | null = null;

function loadAmap(): Promise<AMapGlobal | null> {
  if (typeof window === "undefined") return Promise.resolve(null);
  if (window.AMap) return Promise.resolve(window.AMap);
  if (amapLoaderPromise) return amapLoaderPromise;
  amapLoaderPromise = new Promise((resolve) => {
    const script = document.createElement("script");
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${AMAP_KEY}`;
    script.async = true;
    script.onload = () => resolve(window.AMap ?? null);
    script.onerror = () => {
      amapLoaderPromise = null;
      resolve(null);
    };
    document.head.appendChild(script);
  });
  return amapLoaderPromise;
}

export function AmapView({ landmarks }: { landmarks: Landmark[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<AMapInstance | null>(null);
  const markersRef = useRef<unknown[]>([]);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;
    let cancelled = false;

    loadAmap().then((AMap) => {
      if (cancelled || !AMap || !containerRef.current) return;
      const map = new AMap.Map(containerRef.current, {
        zoom: 17,
        center: CENTER,
        mapStyle: "amap://styles/dark",
        viewMode: "2D",
      });

      map.plugin("AMap.Geolocation", () => {
        const geolocation = new AMap.Geolocation({
          enableHighAccuracy: true,
          timeout: 10000,
          zoomToAccuracy: false,
          showCircle: false,
          showMarker: false,
          showButton: false,
        });
        geolocation.getCurrentPosition((status, result) => {
          if (status !== "complete") return;
          const pos = result.position;
          const dist = getDistance(pos.lat, pos.lng, CENTER[1], CENTER[0]);
          // 3km 以内才显示位置并移视角
          if (dist < 3000) {
            const marker = new AMap.Marker({
              position: [pos.lng, pos.lat],
              content: `<div style="width:14px;height:14px;background:#88a37d;border:2px solid #e8c896;border-radius:50%;box-shadow:0 0 12px rgba(136,163,125,0.6);"></div>`,
              offset: new AMap.Pixel(-7, -7),
            });
            map.add(marker);
            map.setCenter([pos.lng, pos.lat]);
          }
        });
      });

      mapRef.current = map;
      setMapReady(true);
    });

    return () => {
      cancelled = true;
      if (mapRef.current) {
        mapRef.current.destroy();
        mapRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!mapReady || landmarks.length === 0) return;
    const map = mapRef.current;
    const AMap = typeof window !== "undefined" ? window.AMap : undefined;
    if (!map || !AMap) return;

    if (markersRef.current.length > 0) {
      map.remove(markersRef.current);
    }
    markersRef.current = [];

    const markers = landmarks
      .filter((lm) => lm.geo_point && FEATURED_IDS.has(lm.id))
      .map(
        (lm) =>
          new AMap.Marker({
            position: [lm.geo_point!.lng, lm.geo_point!.lat],
            title: lm.name,
            content: `<div style="display:flex;flex-direction:column;align-items:center;transform:translate(-50%,-100%);">
              <div style="width:8px;height:8px;background:#e8c896;border:2px solid #b3914a;border-radius:50%;box-shadow:0 0 8px rgba(232,200,150,0.5);"></div>
              <span style="margin-top:3px;padding:2px 6px;font-size:11px;color:#ece9e2;background:rgba(19,23,25,0.85);border-radius:3px;white-space:nowrap;text-shadow:0 1px 2px rgba(0,0,0,0.6);">${lm.name}</span>
            </div>`,
            offset: new AMap.Pixel(0, 0),
          }),
      );
    map.add(markers);
    markersRef.current = markers;
  }, [mapReady, landmarks]);

  return (
    <div
      ref={containerRef}
      className="amap-container"
      style={{ width: "100%", height: "100%" }}
    />
  );
}
