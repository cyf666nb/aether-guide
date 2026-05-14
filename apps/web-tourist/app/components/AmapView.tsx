"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

// Prefer the env-driven key so a prod build can swap in its own quota, but
// fall back to the repo demo key for local dev.
const AMAP_KEY =
  process.env.NEXT_PUBLIC_AMAP_KEY || "485e3836235de177b54deaa033a9801e";

const CENTER: [number, number] = [119.2964, 26.0835]; // 南后街中段 (三坊七巷中心)

// Minimal shape of the AMap globals we actually touch. Keeps TS honest
// without pulling in the full (and large) @amap/amap-jsapi-types package.
type AMapMarkerOptions = {
  position: [number, number];
  title?: string;
  label?: { content: string; direction: string; offset: unknown };
  content?: string;
  offset?: unknown;
};

type AMapPolylineOptions = {
  path: [number, number][];
  strokeColor: string;
  strokeOpacity: number;
  strokeWeight: number;
  lineJoin?: "round" | "miter" | "bevel";
  lineCap?: "round" | "butt" | "square";
  showDir?: boolean;
  zIndex?: number;
};

type AMapInstance = {
  add: (markerOrList: unknown) => void;
  remove: (markers: unknown[]) => void;
  setCenter: (position: [number, number]) => void;
  setZoomAndCenter: (zoom: number, position: [number, number]) => void;
  destroy: () => void;
  plugin: (names: string | string[], cb: () => void) => void;
};

type AMapMarker = {
  on?: (eventName: string, handler: () => void) => void;
};

type AMapGlobal = {
  Map: new (
    el: HTMLElement,
    opts: { zoom: number; center: [number, number]; mapStyle: string; viewMode: string },
  ) => AMapInstance;
  Marker: new (opts: AMapMarkerOptions) => AMapMarker;
  Pixel: new (x: number, y: number) => unknown;
  Geolocation: new (opts: Record<string, unknown>) => {
    getCurrentPosition: (
      cb: (status: string, result: { position: { lat: number; lng: number } }) => void,
    ) => void;
  };
  Polyline?: new (opts: AMapPolylineOptions) => unknown;
  plugin: (names: string | string[], cb: () => void) => void;
  event?: AMapEventApi;
  AutoComplete?: AMapAutoCompleteConstructor;
  Autocomplete?: AMapAutoCompleteConstructor;
  PlaceSearch?: AMapPlaceSearchConstructor;
};

declare global {
  interface Window {
    AMap?: AMapGlobal;
    _AMapSecurityConfig?: { securityJsCode?: string; serviceHost?: string };
    __calibrate?: (nameFilter?: string) => Promise<Record<string, AmapLngLat>>;
  }
}

type Landmark = {
  id: string;
  name: string;
  geo_point?: { lat: number; lng: number } | null;
  tags?: string[];
};

const EMPTY_ROUTE_IDS: string[] = [];

/** Curated set of key landmarks shown on the homepage map. */
export const FEATURED_IDS = new Set([
  "nanhou-street",
  "nanhou-street-north-archway",
  // 三坊 (three lanes, west side)
  "yijin-lane",
  "wenru-lane",
  "guanglu-lane",
  // 七巷 (seven alleys, east side)
  "yangqiao-alley",
  "langguan-alley",
  "ta-alley",
  "huang-alley",
  "anmin-alley",
  "gong-alley",
  "jipi-alley",
  // Featured residences & spots
  "linjuemin-bingxin",
  "yanfu-former-residence",
  "shenbaozhen-former-residence",
  "xiaohuanglou",
  "shuixie-stage",
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

function parseAmapLocation(
  location: AmapTipResult["location"] | undefined,
): AmapLngLat | null {
  if (!location) return null;
  if (typeof location === "string") {
    const [lngRaw, latRaw] = location.split(",").map(Number);
    if (Number.isFinite(lngRaw) && Number.isFinite(latRaw)) {
      return { lng: lngRaw, lat: latRaw };
    }
    return null;
  }
  if (Number.isFinite(location.lng) && Number.isFinite(location.lat)) {
    return location;
  }
  return null;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => {
    switch (char) {
      case "&":
        return "&amp;";
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case '"':
        return "&quot;";
      default:
        return "&#39;";
    }
  });
}

let amapLoaderPromise: Promise<AMapGlobal | null> | null = null;
let openPatched = false;

function loadAmap(): Promise<AMapGlobal | null> {
  if (typeof window === "undefined") return Promise.resolve(null);
  if (window.AMap) return Promise.resolve(window.AMap);
  if (amapLoaderPromise) return amapLoaderPromise;

  // AMap JS API v2.0 free-tier keys inject ads that call window.open.
  // The app never opens new tabs legitimately, so we neuter window.open
  // before the SDK script loads and leave the patch in place permanently.
  if (!openPatched) {
    window.open = (...args: Parameters<typeof window.open>) => {
      const url = typeof args[0] === "string" ? args[0] : "";
      console.warn("[AmapView] blocked window.open:", url || "(no url)");
      return null;
    };
    openPatched = true;

    // AMap JSAPI v2.0 mandatory security configuration.
    // Must be set before the SDK script loads, otherwise plugins may be blocked.
    const secCode = process.env.NEXT_PUBLIC_AMAP_SECURITY_JS_CODE;
    if (secCode) {
      window._AMapSecurityConfig = { securityJsCode: secCode };
    } else if (!window._AMapSecurityConfig) {
      // Some keys (legacy / demo) work without a security code, but
      // the config object itself may act as a signal to enable full API.
      window._AMapSecurityConfig = {};
    }
  }

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

// ---- AMap JS SDK plugin types ---------------------------------------------
// Use AMap.AutoComplete / AMap.PlaceSearch plugins loaded via map.plugin().

type AmapTipResult = {
  id: string;
  name: string;
  district: string;
  adcode: string;
  location: { lng: number; lat: number } | string;
  address: string;
};

type AmapLngLat = { lng: number; lat: number };
type AmapPoiSearchResult = { poiList?: { pois?: AmapTipResult[] } };

type AutoCompleteInstance = {
  search: (keyword: string, cb: (status: string, result: { tips: AmapTipResult[] }) => void) => void;
};

type PlaceSearchInstance = {
  search: (keyword: string, cb?: (status: string, result: AmapPoiSearchResult) => void) => void;
};

type AMapAutoCompleteConstructor = new (opts: {
  city: string;
  citylimit: boolean;
}) => AutoCompleteInstance;

type AMapPlaceSearchConstructor = new (opts: {
  city: string;
  citylimit: boolean;
  pageSize: number;
  map: AMapInstance;
}) => PlaceSearchInstance;

type AMapEventApi = {
  addListener: (
    target: unknown,
    eventName: string,
    handler: (result: AmapPoiSearchResult) => void,
  ) => unknown;
  removeListener?: (
    target: unknown,
    eventName: string,
    handler: (result: AmapPoiSearchResult) => void,
  ) => void;
};

export function AmapView({
  landmarks,
  activeLandmarkId,
  onMarkerClick,
  onPoiSelected,
  routeLandmarkIds = EMPTY_ROUTE_IDS,
  showSearch = true,
}: {
  landmarks: Landmark[];
  activeLandmarkId?: string | null;
  onMarkerClick?: (landmarkId: string) => void;
  onPoiSelected?: (poi: { name: string; lat: number; lng: number }) => void;
  routeLandmarkIds?: string[];
  showSearch?: boolean;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<AMapInstance | null>(null);
  const markersRef = useRef<AMapMarker[]>([]);
  const routeOverlaysRef = useRef<unknown[]>([]);
  const landmarksRef = useRef(landmarks);
  const searchRef = useRef<HTMLInputElement>(null);
  const autoCompleteRef = useRef<AutoCompleteInstance | null>(null);
  const placeSearchRef = useRef<PlaceSearchInstance | null>(null);
  const styleObserverRef = useRef<MutationObserver | null>(null);
  const [mapReady, setMapReady] = useState(false);

  // ---- POI search via AMap JS SDK plugins ----
  const [suggestions, setSuggestions] = useState<AmapTipResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const routeIdSet = useMemo(
    () => new Set(routeLandmarkIds),
    [routeLandmarkIds],
  );
  const routeOrderById = useMemo(
    () =>
      new Map(
        routeLandmarkIds.map((landmarkId, index) => [landmarkId, index]),
      ),
    [routeLandmarkIds],
  );
  const landmarkById = useMemo(
    () => new Map(landmarks.map((landmark) => [landmark.id, landmark])),
    [landmarks],
  );

  useEffect(() => {
    landmarksRef.current = landmarks;
  }, [landmarks]);

  const handleSearchInput = useCallback(
    (value: string) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);

      if (!value.trim()) {
        setSuggestions([]);
        setSearchLoading(false);
        return;
      }

      setSearchLoading(true);
      debounceRef.current = setTimeout(() => {
        const ac = autoCompleteRef.current;
        if (!ac) {
          setSearchLoading(false);
          return;
        }
        ac.search(value, (status, result) => {
          console.log("[AmapView] AutoComplete search status:", status, "tips:", result.tips?.length ?? 0);
          if (status === "complete" && result.tips) {
            setSuggestions(result.tips);
          } else {
            setSuggestions([]);
          }
          setSearchLoading(false);
        });
      }, 280);
    },
    [],
  );

  const handleSelectTip = useCallback(
    (tip: AmapTipResult) => {
      const map = mapRef.current;
      if (!map) return;

      const ps = placeSearchRef.current;
      const AMap = typeof window !== "undefined" ? window.AMap : undefined;

      const applyLocation = (name: string, lng: number, lat: number) => {
        map.setZoomAndCenter(17, [lng, lat]);
        onPoiSelected?.({ name, lat, lng });
        setSuggestions([]);
        if (searchRef.current) {
          searchRef.current.value = "";
          searchRef.current.blur();
        }
      };

      if (ps && AMap?.event) {
        const eventApi = AMap.event;
        let settled = false;
        const fallbackLocation = parseAmapLocation(tip.location);
        const cleanup = (handler: (result: AmapPoiSearchResult) => void) => {
          eventApi.removeListener?.(ps, "complete", handler);
        };
        const onComplete = (result: AmapPoiSearchResult) => {
          if (settled) return;
          settled = true;
          window.clearTimeout(timeout);
          cleanup(onComplete);
          const [poi] = result.poiList?.pois ?? [];
          const location = parseAmapLocation(poi?.location) ?? fallbackLocation;
          if (!location) return;
          applyLocation(poi?.name ?? tip.name, location.lng, location.lat);
        };
        const timeout = window.setTimeout(() => {
          if (settled) return;
          settled = true;
          cleanup(onComplete);
          if (fallbackLocation) {
            applyLocation(tip.name, fallbackLocation.lng, fallbackLocation.lat);
          }
        }, 4000);
        // AMap v2.0 PlaceSearch uses events, not callbacks
        eventApi.addListener(ps, "complete", onComplete);
        ps.search(tip.name);
      } else {
        // No PlaceSearch plugin available, use tip location directly
        const location = parseAmapLocation(tip.location);
        if (location) {
          applyLocation(tip.name, location.lng, location.lat);
        }
      }
    },
    [onPoiSelected],
  );

  // ---- Map init ----

  useEffect(() => {
    if (!containerRef.current) return;
    let cancelled = false;

    loadAmap().then((AMap) => {
      if (cancelled || !AMap || !containerRef.current) return;

      const isLight =
        typeof document !== "undefined" &&
        document.documentElement.getAttribute("data-mode") === "light";

      const map = new AMap.Map(containerRef.current, {
        zoom: 17,
        center: CENTER,
        mapStyle: isLight ? "amap://styles/normal" : "amap://styles/dark",
        viewMode: "2D",
      });

      mapRef.current = map;

      map.plugin("AMap.Geolocation", () => {
        if (cancelled) return;
        const geolocation = new AMap.Geolocation({
          enableHighAccuracy: true,
          timeout: 10000,
          zoomToAccuracy: false,
          showCircle: false,
          showMarker: false,
          showButton: false,
        });
        geolocation.getCurrentPosition((status, result) => {
          if (status !== "complete" || cancelled) return;
          const pos = result.position;
          const dist = getDistance(pos.lat, pos.lng, CENTER[1], CENTER[0]);
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

      // Load AutoComplete + PlaceSearch plugins via map.plugin()
      map.plugin(["AMap.AutoComplete", "AMap.PlaceSearch"], () => {
        if (cancelled) return;
        // Log available keys for debugging
        console.log(
          "[AmapView] AMap keys with Auto/Place:",
          Object.keys(AMap).filter((k) => /auto|place|search/i.test(k)),
        );

        // Try both case variations — docs are inconsistent
        const AutoCompleteCtor = AMap.AutoComplete || AMap.Autocomplete;
        if (AutoCompleteCtor) {
          autoCompleteRef.current = new AutoCompleteCtor({
            city: "福州",
            citylimit: true,
          }) as AutoCompleteInstance;
          console.log(
            "[AmapView] AutoComplete ready, ctor:",
            AutoCompleteCtor === AMap.AutoComplete ? "AutoComplete" : "Autocomplete",
          );
        } else {
          console.warn("[AmapView] AutoComplete NOT available on AMap");
        }

        const PlaceSearchCtor = AMap.PlaceSearch;
        if (PlaceSearchCtor) {
          placeSearchRef.current = new PlaceSearchCtor({
            city: "福州",
            citylimit: true,
            pageSize: 1,
            map: map,
          }) as PlaceSearchInstance;
          console.log("[AmapView] PlaceSearch ready");
        } else {
          console.warn("[AmapView] PlaceSearch NOT available on AMap");
        }

        // ---- Calibration helper (browser console: window.__calibrate()) ----
        const ps = placeSearchRef.current;
        if (ps && AMap.event) {
          const eventApi = AMap.event;
          window.__calibrate = async (nameFilter?: string) => {
            const ids = [...FEATURED_IDS];
            const results: Record<string, AmapLngLat & { name: string }> = {};
            console.log("[Calibrate] searching %d landmarks via PlaceSearch...", ids.length);
            console.log("[Calibrate] PlaceSearch instance:", ps);
            console.log("[Calibrate] AMap.event:", typeof eventApi.addListener);
            for (const id of ids) {
              const lm = landmarksRef.current.find((l) => l.id === id);
              if (!lm) continue;
              if (nameFilter && !lm.name.includes(nameFilter)) continue;
              const searchKeyword = nameFilter || lm.name;
              console.log("[Calibrate] searching for:", searchKeyword);
              try {
                await new Promise<void>((resolve) => {
                  const timeout = setTimeout(() => {
                    console.warn("[Calibrate] %s TIMEOUT after 8s", searchKeyword);
                    resolve();
                  }, 8000);
                  const onComplete = (result: AmapPoiSearchResult) => {
                    clearTimeout(timeout);
                    console.log("[Calibrate] %s complete event, pois=%s",
                      searchKeyword, result.poiList?.pois?.length ?? 0);
                    const [poi] = result.poiList?.pois ?? [];
                    const loc = parseAmapLocation(poi?.location);
                    if (poi && loc) {
                      results[id] = { name: poi.name, lng: loc.lng, lat: loc.lat };
                      console.log("[Calibrate] %s -> [%.6f, %.6f]", id, loc.lng, loc.lat);
                    } else {
                      console.warn("[Calibrate] %s — no poi, full:", id, JSON.stringify(result).slice(0, 300));
                    }
                    eventApi.removeListener?.(ps, "complete", onComplete);
                    resolve();
                  };
                  // AMap v2.0 PlaceSearch uses events, not callbacks
                  eventApi.addListener(ps, "complete", onComplete);
                  ps.search(searchKeyword);
                });
              } catch (e) {
                console.error("[Calibrate] error searching", searchKeyword, e);
              }
            }
            console.log("[Calibrate] DONE. Copy the JSON below into scenic_demo.json:\n");
            console.log(JSON.stringify(results, null, 2));
            return results;
          };
          console.log("[AmapView] Calibration helper ready — run window.__calibrate() in console");
        }
      });

      setMapReady(true);

      // React to mode changes (dark/light) and update map style
      const observer = new MutationObserver(() => {
        const light =
          document.documentElement.getAttribute("data-mode") === "light";
        try {
          (map as unknown as { setMapStyle: (s: string) => void }).setMapStyle(
            light ? "amap://styles/normal" : "amap://styles/dark",
          );
        } catch {
          /* setMapStyle not available in all SDK versions */
        }
      });
      observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-mode"],
      });
      styleObserverRef.current = observer;
    });

    return () => {
      cancelled = true;
      if (debounceRef.current) clearTimeout(debounceRef.current);
      styleObserverRef.current?.disconnect();
      if (mapRef.current) {
        if (routeOverlaysRef.current.length > 0) {
          mapRef.current.remove(routeOverlaysRef.current);
          routeOverlaysRef.current = [];
        }
        mapRef.current.destroy();
        mapRef.current = null;
      }
    };
  }, []);

  // ---- Landmark markers ----

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
      .filter((lm) => lm.geo_point && (FEATURED_IDS.has(lm.id) || routeIdSet.has(lm.id)))
      .map((lm) => {
        const isActive = lm.id === activeLandmarkId;
        const routeIndex = routeOrderById.get(lm.id) ?? -1;
        const dotSize = isActive ? 12 : routeIndex >= 0 ? 10 : 8;
        const dotColor = isActive ? "#ffffff" : routeIndex >= 0 ? "#88a37d" : "#e8c896";
        const borderColor = isActive ? "#e8c896" : routeIndex >= 0 ? "#e8c896" : "#b3914a";
        const labelPrefix = routeIndex >= 0 ? `${routeIndex + 1}. ` : "";
        const label = escapeHtml(`${labelPrefix}${lm.name}`);
        const marker = new AMap.Marker({
          position: [lm.geo_point!.lng, lm.geo_point!.lat],
          title: lm.name,
          content: `<div style="display:flex;flex-direction:column;align-items:center;transform:translate(-50%,-100%);">
              <div style="width:${dotSize}px;height:${dotSize}px;background:${dotColor};border:2px solid ${borderColor};border-radius:50%;box-shadow:0 0 ${isActive ? 18 : 10}px rgba(232,200,150,0.65);cursor:pointer;"></div>
              <span style="margin-top:3px;padding:2px 6px;font-size:11px;color:#ece9e2;background:rgba(19,23,25,0.85);border-radius:3px;white-space:nowrap;text-shadow:0 1px 2px rgba(0,0,0,0.6);">${label}</span>
            </div>`,
          offset: new AMap.Pixel(0, 0),
        });
        marker.on?.("click", () => {
          onMarkerClick?.(lm.id);
        });
        return marker;
      });
    map.add(markers);
    markersRef.current = markers;
  }, [activeLandmarkId, mapReady, landmarks, onMarkerClick, routeIdSet, routeOrderById]);

  useEffect(() => {
    if (!mapReady || !activeLandmarkId) return;
    const map = mapRef.current;
    const landmark = landmarkById.get(activeLandmarkId);
    if (!map || !landmark?.geo_point) return;
    map.setZoomAndCenter(17, [
      landmark.geo_point.lng,
      landmark.geo_point.lat,
    ]);
  }, [activeLandmarkId, landmarkById, mapReady]);

  useEffect(() => {
    if (!mapReady) return;
    const map = mapRef.current;
    const AMap = typeof window !== "undefined" ? window.AMap : undefined;
    if (!map || !AMap) return;

    if (routeOverlaysRef.current.length > 0) {
      map.remove(routeOverlaysRef.current);
      routeOverlaysRef.current = [];
    }

    const path = routeLandmarkIds.flatMap((id) => {
      const geo = landmarkById.get(id)?.geo_point;
      return geo ? [[geo.lng, geo.lat] as [number, number]] : [];
    });
    if (path.length === 0) return;

    if (AMap.Polyline && path.length > 1) {
      const polyline = new AMap.Polyline({
        path,
        strokeColor: "#e8c896",
        strokeOpacity: 0.84,
        strokeWeight: 5,
        lineJoin: "round",
        lineCap: "round",
        showDir: true,
        zIndex: 20,
      });
      map.add(polyline);
      routeOverlaysRef.current = [polyline];
    }

    map.setZoomAndCenter(path.length > 1 ? 16 : 17, path[0]);
  }, [landmarkById, mapReady, routeLandmarkIds]);

  return (
    <div
      ref={containerRef}
      className="amap-container"
      style={{ width: "100%", height: "100%", position: "relative" }}
    >
      {showSearch && (
      <div
        className="amap-search-bar"
        onClick={() => searchRef.current?.focus()}
      >
        <span className="amap-search-icon" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <circle cx="11" cy="11" r="7" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </span>
        <input
          ref={searchRef}
          className="amap-search-input"
          type="text"
          placeholder="搜索…"
          autoComplete="off"
          onChange={(e) => handleSearchInput(e.target.value)}
          onFocus={() => {
            // Re-trigger search with current value on focus
            if (searchRef.current?.value.trim()) {
              handleSearchInput(searchRef.current.value);
            }
          }}
        />

        {/* Custom suggestions dropdown */}
        {(suggestions.length > 0 || searchLoading) && (
          <ul className="amap-suggestions">
            {searchLoading && suggestions.length === 0 && (
              <li className="amap-sug-item amap-sug-loading">搜索中…</li>
            )}
            {suggestions.map((tip) => (
              <li
                key={tip.id}
                className="amap-sug-item"
                onMouseDown={(e) => {
                  // Prevent input blur before click fires
                  e.preventDefault();
                }}
                onClick={() => handleSelectTip(tip)}
              >
                <span className="amap-sug-name">{tip.name}</span>
                {tip.district && (
                  <span className="amap-sug-district">{tip.district}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
      )}
    </div>
  );
}
