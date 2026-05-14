"use client";

import { CameraGlyph } from "@aether/design-system/icons";
import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import {
  memo,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { IntroScreen } from "./components/IntroScreen";
import { TextStream } from "./components/TextStream";
import { useNavState } from "./components/NavContext";
import {
  createSession,
  fetchTtsAudioUrl,
  getLandmarks,
  wsUrl,
  type Landmark,
} from "./lib/api";

// Lazy-load AMap: the SDK script + wrapper component is ~1MB combined and
// below the fold for chat interaction. Deferring it cuts TTI noticeably.
const AmapView = dynamic(
  () => import("./components/AmapView").then((m) => ({ default: m.AmapView })),
  {
    ssr: false,
    loading: () => <div className="amap-container" aria-hidden="true" />,
  },
);

// Live2D Cubism "Haru Greeter" digital-human floats in the bottom-right corner.
// Pulled in via next/dynamic with ssr:false because pixi.js + the Live2D
// plugin touch `window`/`WebGLRenderingContext` at module-eval time.
const Live2DMao = dynamic(() => import("./components/Live2DMao"), {
  ssr: false,
  loading: () => null,
});

type ChatRole = "user" | "guide";

type ChatMessage = {
  _id: number;
  speaker: "你" | "知行" | "System";
  text: string;
  role: ChatRole;
  citations?: string[];
  cacheHit?: boolean;
};

const PLACEHOLDERS = [
  "附近有什么好吃的？",
  "带孩子看什么？",
  "雨天怎么逛？",
  "30 分钟路线怎么走？",
  "严复故居有什么看点？",
  "哪里适合拍照？",
  "三坊七巷晚上好玩吗？",
  "福州方言怎么学？",
  "有什么非遗体验？",
  "老人怎么走轻松？",
] as const;

type ConnectionState = "connecting" | "online" | "offline" | "reconnecting";

// Same curated set used by AmapView markers; keep it module-level so memo
// dependencies stay primitive and the Set is not rebuilt on every render.
const FEATURED_IDS = new Set([
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

const INITIAL_GREETING =
  "我会根据你在三坊七巷的位置，把名人故居、街巷动线和非遗体验串成一段顺路的游程。";

/** Cheap helper; strips citation tokens the model sometimes leaves inline. */
function stripCitations(text: string): string {
  return text.replace(/\[\^[^\]]+]/g, "");
}

export default function TouristHomePage() {
  return (
    <Suspense fallback={null}>
      <TouristHome />
    </Suspense>
  );
}

function TouristHome() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [introActive, setIntroActive] = useState(() => {
    if (typeof window === "undefined") return false;
    return !sessionStorage.getItem("intro-seen");
  });
  const handleIntroComplete = useCallback(() => {
    try { sessionStorage.setItem("intro-seen", "1"); } catch {}
    setIntroActive(false);
  }, []);
  const initialQueryRef = useRef<string | null>(
    searchParams.get("q")?.trim() || null,
  );
  const shouldAutoSendInitialQueryRef = useRef(
    searchParams.get("autoSend") === "true",
  );
  const initialQuerySentRef = useRef(false);

  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [input, setInput] = useState("");
  const [placeholder, setPlaceholder] = useState<string>(PLACEHOLDERS[0]);
  const [isThinking, setIsThinking] = useState(false);
  const [currentSpotIndex, setCurrentSpotIndex] = useState(0);
  const [latestAnnounce, setLatestAnnounce] = useState("");
  const [isAudioActive, setIsAudioActive] = useState(false);

  // Use a ref for message id generation: a module-level `let` resets under
  // HMR and isn't component-scoped.
  const nextIdRef = useRef(1);
  const mkMessage = useCallback(
    (partial: Omit<ChatMessage, "_id">): ChatMessage => ({
      ...partial,
      _id: nextIdRef.current++,
    }),
    [],
  );

  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      _id: 0,
      speaker: "知行",
      text: INITIAL_GREETING,
      role: "guide",
    },
  ]);

  // Streaming state: to avoid re-rendering the whole conversation on every
  // token, we buffer incoming text in a ref and flush via requestAnimationFrame.
  const streamingIdRef = useRef<number | null>(null);
  const streamingTextRef = useRef<string>("");
  const streamingFrameRef = useRef<number | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const conversationRef = useRef<HTMLElement | null>(null);
  const userScrolledUpRef = useRef(false);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const placeholderIndexRef = useRef(0);

  // --- Audio element (persistent; unlocks TTS autoplay after first click) ---
  const audioElementRef = useRef<HTMLAudioElement | null>(null);
  const pendingAudioUrlRef = useRef<string | null>(null);
  const currentAudioUrlRef = useRef<string | null>(null);

  useEffect(() => {
    const nextIndex = Math.floor(Math.random() * PLACEHOLDERS.length);
    placeholderIndexRef.current = nextIndex;
    setPlaceholder(PLACEHOLDERS[nextIndex]);
  }, []);

  // If the user arrived via /?q=... (e.g. landmark cards), prefill and focus.
  useEffect(() => {
    const q = initialQueryRef.current;
    if (!q) return;
    setInput(q);
    // Focus after a tick so the composer is mounted.
    requestAnimationFrame(() => inputRef.current?.focus());
  }, []);

  useEffect(() => {
    const audio = new Audio();
    audio.preload = "auto";
    audioElementRef.current = audio;

    const releaseCurrent = () => {
      if (currentAudioUrlRef.current) {
        URL.revokeObjectURL(currentAudioUrlRef.current);
        currentAudioUrlRef.current = null;
      }
    };
    const finishPlayback = () => {
      releaseCurrent();
      setIsAudioActive(false);
    };
    const handlePlay = () => setIsAudioActive(true);
    audio.addEventListener("play", handlePlay);
    audio.addEventListener("ended", finishPlayback);
    audio.addEventListener("error", finishPlayback);

    const tryPlayPending = () => {
      const url = pendingAudioUrlRef.current;
      if (!url) return;
      pendingAudioUrlRef.current = null;
      releaseCurrent();
      audio.src = url;
      currentAudioUrlRef.current = url;
      setIsAudioActive(true);
      audio.play().catch(() => {
        pendingAudioUrlRef.current = url;
        currentAudioUrlRef.current = null;
        setIsAudioActive(true);
      });
    };

    document.addEventListener("click", tryPlayPending);
    document.addEventListener("touchstart", tryPlayPending);
    return () => {
      document.removeEventListener("click", tryPlayPending);
      document.removeEventListener("touchstart", tryPlayPending);
      audio.removeEventListener("play", handlePlay);
      audio.removeEventListener("ended", finishPlayback);
      audio.removeEventListener("error", finishPlayback);
      audio.pause();
      audio.src = "";
      if (pendingAudioUrlRef.current) {
        URL.revokeObjectURL(pendingAudioUrlRef.current);
        pendingAudioUrlRef.current = null;
      }
      releaseCurrent();
    };
  }, []);

  const playBlobViaSharedAudio = useCallback((audioUrl: string) => {
    const audio = audioElementRef.current;
    if (!audio) {
      URL.revokeObjectURL(audioUrl);
      return;
    }
    if (pendingAudioUrlRef.current) {
      URL.revokeObjectURL(pendingAudioUrlRef.current);
      pendingAudioUrlRef.current = null;
    }
    if (currentAudioUrlRef.current) {
      URL.revokeObjectURL(currentAudioUrlRef.current);
      currentAudioUrlRef.current = null;
    }
    audio.src = audioUrl;
    currentAudioUrlRef.current = audioUrl;
    setIsAudioActive(true);
    audio.play().catch(() => {
      pendingAudioUrlRef.current = audioUrl;
      currentAudioUrlRef.current = null;
      setIsAudioActive(true);
    });
  }, []);

  const fetchTtsBlob = useCallback(
    async (text: string): Promise<string | null> => {
      const trimmed = text.trim();
      if (!trimmed) return null;
      try {
        return await fetchTtsAudioUrl(trimmed);
      } catch {
        return null;
      }
    },
    [],
  );

  const speakText = useCallback(
    async (text: string) => {
      const url = await fetchTtsBlob(text);
      if (url) playBlobViaSharedAudio(url);
    },
    [fetchTtsBlob, playBlobViaSharedAudio],
  );

  const stopSpeaking = useCallback(() => {
    const audio = audioElementRef.current;
    if (audio) {
      audio.pause();
      audio.src = "";
    }
    if (pendingAudioUrlRef.current) {
      URL.revokeObjectURL(pendingAudioUrlRef.current);
      pendingAudioUrlRef.current = null;
    }
    if (currentAudioUrlRef.current) {
      URL.revokeObjectURL(currentAudioUrlRef.current);
      currentAudioUrlRef.current = null;
    }
    setIsAudioActive(false);
  }, []);

  const { data: landmarks = [] } = useQuery({
    queryKey: ["landmarks"],
    queryFn: () => getLandmarks(),
    // Landmarks are nearly static seed data; a long stale time avoids
    // re-fetching on every tab focus.
    staleTime: 60 * 60 * 1000,
    gcTime: 24 * 60 * 60 * 1000,
  });

  const landmarkNameMap = useMemo(
    () => new Map(landmarks.map((lm) => [lm.id, lm.name])),
    [landmarks],
  );

  // Same curated set used by AmapView markers — only these ID'd landmarks
  const mapLandmarks = useMemo(
    () => landmarks.filter((lm) => lm.geo_point && FEATURED_IDS.has(lm.id)),
    [landmarks],
  );

  // ------------------- Streaming flush (rAF batched) -------------------
  const flushStreamingText = useCallback(() => {
    streamingFrameRef.current = null;
    const sid = streamingIdRef.current;
    if (sid === null) return;
    const text = streamingTextRef.current;
    setMessages((current) =>
      current.map((m) => (m._id === sid ? { ...m, text } : m)),
    );
  }, []);

  const scheduleFlush = useCallback(() => {
    if (streamingFrameRef.current !== null) return;
    streamingFrameRef.current = requestAnimationFrame(flushStreamingText);
  }, [flushStreamingText]);

  // ------------------- WebSocket session lifecycle -------------------
  useEffect(() => {
    let mounted = true;
    let retry = 0;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const openSession = async () => {
      try {
        setConnection((prev) => (prev === "online" ? prev : "connecting"));
        const sessionId = sessionIdRef.current ?? (await createSession()).id;
        sessionIdRef.current = sessionId;
        if (!mounted) return;
        const info = await wsUrl(sessionId);
        const socket = new WebSocket(info.url, info.protocols);
        socketRef.current = socket;

        socket.addEventListener("open", () => {
          if (!mounted) return;
          retry = 0;
          setConnection("online");
        });

        socket.addEventListener("message", (event) => {
          let payload: {
            type?: string;
            data?: {
              content?: string;
              citations?: string[];
              cache_hit?: boolean;
            } | null;
          };
          try {
            payload = JSON.parse(event.data);
          } catch {
            return;
          }

          if (payload.type === "stream_chunk" && payload.data?.content) {
            const token = payload.data.content;
            setIsThinking(false);
            if (streamingIdRef.current === null) {
              const msg = mkMessage({
                speaker: "知行",
                text: token,
                role: "guide",
              });
              streamingIdRef.current = msg._id;
              streamingTextRef.current = token;
              setMessages((current) => [...current, msg]);
            } else {
              streamingTextRef.current += token;
              scheduleFlush();
            }
            return;
          }

          if (payload.type === "stream_ack") {
            return;
          }

          if (payload.type === "stream_end" && payload.data) {
            // Cancel any pending frame; commit authoritative text now.
            if (streamingFrameRef.current !== null) {
              cancelAnimationFrame(streamingFrameRef.current);
              streamingFrameRef.current = null;
            }
            const sid = streamingIdRef.current;
            const cleanText = stripCitations(payload.data.content ?? "");
            if (sid !== null) {
              const citations = payload.data.citations ?? [];
              const cacheHit = payload.data.cache_hit ?? false;
              setMessages((current) =>
                current.map((m) =>
                  m._id === sid
                    ? {
                        ...m,
                        text: cleanText || stripCitations(m.text),
                        citations,
                        cacheHit,
                      }
                    : m,
                ),
              );
            }
            streamingIdRef.current = null;
            streamingTextRef.current = "";
            if (cleanText) {
              setLatestAnnounce(cleanText);
              speakText(cleanText);
            }
            return;
          }

          if (!payload.data) return;
          const text = stripCitations(payload.data.content ?? "");
          if (!text) return;
          setMessages((current) => [
            ...current,
            mkMessage({
              speaker: "知行",
              text,
              role: "guide",
              citations: payload.data?.citations ?? [],
              cacheHit: payload.data?.cache_hit ?? false,
            }),
          ]);
        });

        socket.addEventListener("close", () => {
          if (!mounted) return;
          socketRef.current = null;
          setConnection("reconnecting");
          // Exponential backoff, capped at ~8s.
          const delay = Math.min(1000 * 2 ** retry, 8000);
          retry += 1;
          retryTimer = setTimeout(() => {
            if (!mounted) return;
            openSession();
          }, delay);
        });

        socket.addEventListener("error", () => {
          // Let `close` drive reconnect; just mark reconnecting for UI.
          setConnection("reconnecting");
        });
      } catch (err) {
        console.warn(
          "Session creation failed, running in offline demo mode:",
          err,
        );
        if (!mounted) return;
        setConnection("offline");
      }
    };

    openSession();

    return () => {
      mounted = false;
      if (retryTimer) clearTimeout(retryTimer);
      if (streamingFrameRef.current !== null) {
        cancelAnimationFrame(streamingFrameRef.current);
      }
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [mkMessage, scheduleFlush, speakText]);

  // ------------------- Smart auto-scroll -------------------
  // Track whether the user has scrolled away from the bottom; if so, don't
  // drag them back while new tokens arrive.
  useEffect(() => {
    const node = conversationRef.current;
    if (!node) return;
    const onScroll = () => {
      const distanceFromBottom =
        node.scrollHeight - node.scrollTop - node.clientHeight;
      userScrolledUpRef.current = distanceFromBottom > 140;
    };
    node.addEventListener("scroll", onScroll, { passive: true });
    return () => node.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (userScrolledUpRef.current) return;
    const node = conversationRef.current;
    if (!node) return;
    // Instant scroll during streaming to avoid animation thrashing; the
    // streaming updates are rAF-batched so this fires at most ~60fps.
    node.scrollTop = node.scrollHeight;
  }, [messages, isThinking]);

  // ------------------- Photo identification -------------------
  const handlePhotoClick = useCallback(() => {
    router.push("/photo");
  }, [router]);

  // ------------------- Send -------------------
  const rotatePlaceholder = useCallback(() => {
    placeholderIndexRef.current =
      (placeholderIndexRef.current + 1) % PLACEHOLDERS.length;
    setPlaceholder(PLACEHOLDERS[placeholderIndexRef.current]);
  }, []);

  const sendText = useCallback((rawText: string) => {
    const text = rawText.trim();
    if (!text || isThinking) return;
    setMessages((current) => [
      ...current,
      mkMessage({ speaker: "你", text, role: "user" }),
    ]);
    setIsThinking(true); // show indicator immediately on user gesture
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "user_text", text, locale: "zh-CN" }));
    } else {
      // Offline demo fallback.
      setIsThinking(false);
      setMessages((current) => [
        ...current,
        mkMessage({
          speaker: "知行",
          text: "当前使用本地知识库演示模式。我建议从南后街进入，再顺路看林觉民·冰心故居和严复故居。",
          role: "guide",
          citations: ["fallback:local"],
        }),
      ]);
    }
    setInput("");
    rotatePlaceholder();
  }, [isThinking, mkMessage, rotatePlaceholder]);

  const send = useCallback(() => {
    sendText(input);
  }, [input, sendText]);

  useEffect(() => {
    const q = initialQueryRef.current;
    if (
      !q ||
      !shouldAutoSendInitialQueryRef.current ||
      initialQuerySentRef.current ||
      connection === "connecting" ||
      connection === "reconnecting"
    ) {
      return;
    }
    initialQuerySentRef.current = true;
    sendText(q);
  }, [connection, sendText]);

  const canSend = input.trim().length > 0 && !isThinking;

  // --- Landmark carousel ------------------------------------------------
  const currentLandmark =
    mapLandmarks[currentSpotIndex] ?? mapLandmarks[0] ?? null;

  const goToSpot = useCallback(
    (index: number) => {
      if (mapLandmarks.length <= 1) return;
      setCurrentSpotIndex(((index % mapLandmarks.length) + mapLandmarks.length) % mapLandmarks.length);
    },
    [mapLandmarks.length],
  );

  const handlePrevSpot = useCallback(
    () => goToSpot(currentSpotIndex - 1),
    [currentSpotIndex, goToSpot],
  );
  const handleNextSpot = useCallback(
    () => goToSpot(currentSpotIndex + 1),
    [currentSpotIndex, goToSpot],
  );

  // Trigger AI narration about the currently selected landmark.
  const handleNarrate = useCallback(() => {
    const lm = currentLandmark;
    if (!lm) return;
    sendText(`介绍一下${lm.name}`);
  }, [currentLandmark, sendText]);

  // Keep the old name-based spot variable for any remaining references.
  const spot = currentLandmark?.name ?? "南后街";

  const trustMode: "online" | "visual" | "offline" =
    connection === "online"
      ? "online"
      : connection === "connecting" || connection === "reconnecting"
        ? "offline"
        : "offline";

  const { setNav } = useNavState();
  useEffect(() => {
    setNav(trustMode, connection);
  }, [trustMode, connection, setNav]);

  return (
    <main className="tourist-frame tourist-home">
      {introActive && <IntroScreen onComplete={handleIntroComplete} />}
      <section className="hero-stage">
        <AmapView
          landmarks={landmarks}
          activeLandmarkId={currentLandmark?.id ?? null}
          onMarkerClick={(landmarkId: string) => {
            const idx = mapLandmarks.findIndex((lm) => lm.id === landmarkId);
            if (idx !== -1) setCurrentSpotIndex(idx);
          }}
        />
        <div className="home-masthead" aria-hidden="true">
          <p className="home-masthead-kicker">
            SANFANG QIXIANG / AI WALKING EDITORIAL
          </p>
          <div className="home-masthead-title">
            <span>坊巷</span>
            <span>知行</span>
          </div>
          <p className="home-masthead-copy">
            把散落的故居、坊巷和非遗，排成一页会回答的游览手稿。
          </p>
        </div>
        <div className="guide-presence" aria-label="数字人导览助手">
          {/*
            Live2D "Haru Greeter" 直接落在地图预留的数字人位里(右下角气泡位),
            视觉上与景区地图绑定。尺寸由 .guide-presence 的 CSS 控制
            (width: min(34vw, 220px), aspect-ratio: 0.72)。
            Live2DMao 不传 width/height 时会自动 100% 填满父容器。
          */}
          <Live2DMao audioElementRef={audioElementRef} />
        </div>
        {currentLandmark && (
          <div className="spot-carousel" aria-label="景点轮播">
            {/* Nav arrow — previous */}
            <button
              className="spot-carousel-arrow"
              type="button"
              onClick={handlePrevSpot}
              disabled={mapLandmarks.length <= 1}
              aria-label="上一个景点"
            >
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path
                  d="M15 4L7 12L15 20"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>

            {/* Card body */}
            <div className="spot-carousel-card">
              <div className="spot-carousel-head">
                <h2 className="spot-carousel-name">{spot}</h2>
                <span className="spot-carousel-index">
                  {currentSpotIndex + 1}/{mapLandmarks.length}
                </span>
              </div>
              {currentLandmark.tags.length > 0 && (
                <div className="spot-carousel-tags">
                  {currentLandmark.tags.slice(0, 4).map((tag) => (
                    <span key={tag} className="spot-tag">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
              {currentLandmark.summary && (
                <p className="spot-carousel-summary">
                  {currentLandmark.summary.length > 60
                    ? currentLandmark.summary.slice(0, 60) + "…"
                    : currentLandmark.summary}
                </p>
              )}
              <button
                className="thin-button spot-narrate-btn"
                type="button"
                onClick={handleNarrate}
                disabled={isThinking}
              >
                {isThinking ? "正在讲解…" : `听${spot}的讲解`}
              </button>
            </div>

            {/* Nav arrow — next */}
            <button
              className="spot-carousel-arrow"
              type="button"
              onClick={handleNextSpot}
              disabled={mapLandmarks.length <= 1}
              aria-label="下一个景点"
            >
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path
                  d="M9 4L17 12L9 20"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>
        )}

        {/* Dot indicators */}
        {mapLandmarks.length > 1 && (
          <div className="spot-carousel-dots" aria-hidden="true">
            {mapLandmarks.map((_, i) => (
              <button
                key={i}
                className={`spot-dot ${i === currentSpotIndex ? "active" : ""}`}
                type="button"
                onClick={() => goToSpot(i)}
                aria-label={`切换到${mapLandmarks[i]?.name ?? ""}`}
              />
            ))}
          </div>
        )}
      </section>

      {connection === "reconnecting" ? (
        <div
          role="status"
          className="connection-banner"
          aria-live="polite"
        >
          连接已断开，正在尝试重连…
        </div>
      ) : null}

      <section
        className="conversation"
        ref={conversationRef}
        // Use aria-live="off" here; per-message announcement is handled by
        // the hidden live region below, so screen readers don't re-read
        // every streamed token.
        aria-live="off"
      >
        <div className="conversation-paper-head" aria-hidden="true">
          <span>今日手稿</span>
          <strong>{currentLandmark?.name ?? "三坊七巷"}</strong>
        </div>
        {messages.map((message) => (
          <MessageRow
            key={message._id}
            message={message}
            landmarkNames={landmarkNameMap}
            onSpeak={speakText}
          />
        ))}
        {isThinking ? (
          <article className="message-row thinking-indicator">
            <p className="caption">知行</p>
            <div className="message-bubble">
              <span className="thinking-dots" aria-label="正在思考">
                <span />
                <span />
                <span />
              </span>
            </div>
          </article>
        ) : null}
      </section>

      {/* Off-screen live region: announces only the final assistant reply. */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        style={{
          position: "absolute",
          width: 1,
          height: 1,
          padding: 0,
          margin: -1,
          overflow: "hidden",
          clip: "rect(0, 0, 0, 0)",
          whiteSpace: "nowrap",
          border: 0,
        }}
      >
        {latestAnnounce}
      </div>

      <section className="composer-dock">
        <button
          className="camera-button"
          type="button"
          onClick={handlePhotoClick}
          aria-label="打开拍照识景页"
          title="打开拍照识景页"
        >
          <CameraGlyph width={28} height={28} />
        </button>
        <label className="voice-field">
          <span className="caption">输入问题</span>
          <input
            ref={inputRef}
            className="field-line"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (
                event.key === "Enter" &&
                !event.nativeEvent.isComposing &&
                canSend
              ) {
                send();
              }
            }}
            placeholder={placeholder}
            aria-label="向导览助手提问"
          />
          <span className="wave-bars" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
            <span />
          </span>
        </label>
        {isAudioActive ? (
          <button
            className="audio-stop-button"
            type="button"
            onClick={stopSpeaking}
            aria-label="停止朗读"
            title="停止朗读"
          >
            停止
          </button>
        ) : null}
        <button
          className="primary-button"
          type="button"
          onClick={send}
          disabled={!canSend}
          aria-label={isThinking ? "等待回答中" : "发送问题"}
        >
          {isThinking ? "…" : "发送"}
        </button>
      </section>
    </main>
  );
}

// Extracted + memoised to avoid re-rendering every historical bubble when a
// new streaming token arrives (the streaming message's text changes, but
// previously-committed messages get memo-stable props).
const MessageRow = memo(function MessageRow({
  message,
  landmarkNames,
  onSpeak,
}: {
  message: ChatMessage;
  landmarkNames: Map<string, string>;
  onSpeak: (text: string) => Promise<void> | void;
}) {
  if (message.role === "user") {
    return (
      <article className="message-row user">
        <p className="caption">{message.speaker}</p>
        <div className="message-bubble">{message.text}</div>
      </article>
    );
  }
  return (
    <article className="message-row">
      <p className="caption">{message.speaker}</p>
      <div className="message-bubble">
        <TextStream text={message.text} />
        <CitationStrip
          citations={message.citations ?? []}
          cacheHit={message.cacheHit ?? false}
          landmarkNames={landmarkNames}
        />
        <SpeakButton text={message.text} onPlay={onSpeak} />
      </div>
    </article>
  );
}, areMessageRowsEqual);

function areMessageRowsEqual(
  prev: {
    message: ChatMessage;
    landmarkNames: Map<string, string>;
    onSpeak: (text: string) => Promise<void> | void;
  },
  next: {
    message: ChatMessage;
    landmarkNames: Map<string, string>;
    onSpeak: (text: string) => Promise<void> | void;
  },
) {
  return (
    prev.message._id === next.message._id &&
    prev.message.text === next.message.text &&
    prev.message.cacheHit === next.message.cacheHit &&
    prev.message.citations === next.message.citations &&
    prev.landmarkNames === next.landmarkNames &&
    prev.onSpeak === next.onSpeak
  );
}

function SpeakButton({
  text,
  onPlay,
}: {
  text: string;
  onPlay: (text: string) => Promise<void> | void;
}) {
  const [loading, setLoading] = useState(false);
  const handleClick = async () => {
    if (loading) return;
    setLoading(true);
    try {
      await onPlay(text);
    } finally {
      setLoading(false);
    }
  };
  return (
    <button
      className={`speak-button ${loading ? "speak-loading" : ""}`}
      onClick={handleClick}
      title={loading ? "生成中..." : "朗读"}
      disabled={loading}
      aria-label={loading ? "正在生成语音" : "朗读这段回答"}
      type="button"
    >
      {loading ? "⏳" : "🔊"}
    </button>
  );
}

function CitationStrip({
  citations,
  cacheHit,
  landmarkNames,
}: {
  citations: string[];
  cacheHit: boolean;
  landmarkNames: Map<string, string>;
}) {
  if (!citations.length) return null;
  const isRag = citations.some(
    (citation) =>
      citation.startsWith("landmark:") || citation.startsWith("doc:"),
  );
  const isPersona = citations.includes("persona:current");
  const sourceLabel = isPersona ? "人设" : isRag ? "RAG" : "LLM";
  return (
    <div className="source-strip" aria-label="回答来源">
      <span
        className={`source-pill ${isRag ? "rag" : ""} ${
          isPersona ? "persona" : ""
        }`}
      >
        {sourceLabel}
      </span>
      {cacheHit && !isPersona && <span className="source-pill">缓存</span>}
      {citations.slice(0, 4).map((citation) => (
        <span className="source-chip" key={citation} title={citation}>
          {formatCitation(citation, landmarkNames)}
        </span>
      ))}
    </div>
  );
}

function formatCitation(
  citation: string,
  landmarkNames: Map<string, string>,
) {
  if (citation.startsWith("landmark:")) {
    const landmarkId = citation.slice("landmark:".length);
    return landmarkNames.get(landmarkId) ?? landmarkId;
  }
  if (citation.startsWith("doc:")) return "知识库";
  if (citation === "persona:current") return "人设";
  if (citation.startsWith("llm:")) return "模型";
  if (citation.startsWith("fallback:")) return "本地";
  return citation;
}

// Re-export for callers that import from here (if any).
export type { Landmark };
