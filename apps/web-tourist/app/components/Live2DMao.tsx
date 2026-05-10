"use client";

/**
 * Live2DMao
 * ---------
 * 在游客端角落浮窗中渲染 Live2D Cubism 5 "Mao Pro" 数字人模型,
 * 并把页面共享的 TTS <audio> 元素的实时音量映射到模型的 LipSync 参数 (ParamA)。
 *
 * 运行时依赖(都通过 dynamic import 延迟到客户端加载):
 *   - pixi.js@^7
 *   - pixi-live2d-display-lipsyncpatch/cubism4
 *   - /live2d/live2dcubismcore.min.js (由 app/layout.tsx 通过 <Script
 *     strategy="beforeInteractive"> 预注入到 <head>)
 *
 * 模型资源:
 *   - /live2d/mao_pro/mao_pro.model3.json
 *
 * 设计要点:
 *   - 组件不做 SSR。调用方应使用
 *     `next/dynamic(() => import(...), { ssr: false })` 包裹。
 *   - 模型 anchor 设为 (0.5, 1) —— 底部中心,这样
 *     `model.x = cw/2; model.y = ch` 即可"贴底居中"而不会溢出。
 *   - TTS 嘴型同步:不重复播放音频,只监听页面共享 <audio> 的波形。
 *     通过 AudioContext + MediaElementAudioSourceNode + AnalyserNode 取 RMS,
 *     在 pixi Ticker 最低优先级(晚于模型自身 update)里写入 ParamA。
 *   - AudioContext / MediaElementSource 对同一 audio 只能 create 一次,所以
 *     我们用 Symbol 在 globalThis / audio 元素上缓存,React StrictMode 或
 *     HMR 重复挂载时复用,不再重建。
 */

import { useEffect, useRef, useState, type RefObject } from "react";

type Status = "idle" | "loading" | "ready" | "error";

type Live2DMaoProps = {
  /** model3.json 的绝对 URL。 */
  modelUrl?: string;
  /**
   * 画布宽度 (CSS px)。不传则让外层容器填满父节点(配合 CSS 控制尺寸)。
   */
  width?: number;
  /**
   * 画布高度 (CSS px)。不传则让外层容器填满父节点。
   */
  height?: number;
  /** 顶层容器额外类名。 */
  className?: string;
  /**
   * 页面共享的 <audio> 元素 ref。一旦其 current 非空,组件会自动
   * 建立 AudioContext → AnalyserNode,并把音量映射到 ParamA。
   */
  audioElementRef?: RefObject<HTMLAudioElement | null>;
  onTapHead?: () => void;
  onTapBody?: () => void;
};

// 全局单例缓存:避免 StrictMode / HMR 重复创建 AudioContext 与 MediaElementSource
const CTX_KEY = Symbol.for("aether.live2d.audioContext");
const SRC_KEY = Symbol.for("aether.live2d.mediaSource");

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyObj = any;

function getSharedAudioContext(): AudioContext | null {
  const g = globalThis as AnyObj;
  if (g[CTX_KEY]) return g[CTX_KEY] as AudioContext;
  const Ctor: typeof AudioContext | undefined =
    (window as AnyObj).AudioContext ?? (window as AnyObj).webkitAudioContext;
  if (!Ctor) return null;
  try {
    const ctx = new Ctor();
    g[CTX_KEY] = ctx;
    return ctx;
  } catch {
    return null;
  }
}

function getOrCreateSource(
  audio: HTMLAudioElement,
  ctx: AudioContext,
): MediaElementAudioSourceNode | null {
  const existing = (audio as AnyObj)[SRC_KEY] as
    | MediaElementAudioSourceNode
    | undefined;
  if (existing) return existing;
  try {
    const src = ctx.createMediaElementSource(audio);
    // Also route to speakers so audio.play() stays audible. Without this the
    // MediaElementSource "steals" the default output and the page goes mute.
    src.connect(ctx.destination);
    (audio as AnyObj)[SRC_KEY] = src;
    return src;
  } catch (err) {
    // Only happens if something already connected this element — extremely
    // unlikely since we dedupe via SRC_KEY, but we defend anyway.
    console.warn("[Live2DMao] createMediaElementSource failed:", err);
    return null;
  }
}

export default function Live2DMao({
  modelUrl = "/live2d/mao_pro/mao_pro.model3.json",
  width,
  height,
  className,
  audioElementRef,
  onTapHead,
  onTapBody,
}: Live2DMaoProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let disposed = false;

    // Mutable handles so the cleanup closure can reach the latest instances.
    const handles: {
      app: AnyObj;
      model: AnyObj;
      resizeObserver: ResizeObserver | null;
      canvas: HTMLCanvasElement | null;
      analyser: AnalyserNode | null;
      dataArray: Uint8Array<ArrayBuffer> | null;
      tickerFn: (() => void) | null;
    } = {
      app: null,
      model: null,
      resizeObserver: null,
      canvas: null,
      analyser: null,
      dataArray: null,
      tickerFn: null,
    };

    setStatus("loading");
    setError(null);

    const waitForCubismCore = async (timeoutMs = 10_000) => {
      const start = performance.now();
      while (typeof (window as AnyObj).Live2DCubismCore === "undefined") {
        if (performance.now() - start > timeoutMs) {
          throw new Error(
            "Cubism Core 加载超时 (/live2d/live2dcubismcore.min.js)",
          );
        }
        await new Promise((r) => setTimeout(r, 50));
      }
    };

    (async () => {
      try {
        await waitForCubismCore();

        const PIXI = await import("pixi.js");
        const { Live2DModel } = await import(
          "pixi-live2d-display-lipsyncpatch/cubism4"
        );

        if (disposed) return;

        // The plugin uses window.PIXI.Ticker internally to drive animations.
        (window as AnyObj).PIXI = PIXI;

        // --- Canvas + PIXI Application ------------------------------------
        const canvas = document.createElement("canvas");
        canvas.className = "live2d-mao-canvas";
        container.appendChild(canvas);
        handles.canvas = canvas;

        const app = new PIXI.Application({
          view: canvas,
          width: container.clientWidth || width || 260,
          height: container.clientHeight || height || 380,
          backgroundAlpha: 0,
          antialias: true,
          autoDensity: true,
          resolution: window.devicePixelRatio || 1,
        });
        handles.app = app;

        // --- Load model ---------------------------------------------------
        const model = await Live2DModel.from(modelUrl, {
          autoInteract: true, // eye tracking + hit events
        });
        if (disposed) {
          model.destroy();
          app.destroy(true, {
            children: true,
            texture: true,
            baseTexture: true,
          });
          return;
        }
        handles.model = model;

        // Bottom-center anchor: now x/y refer to the bottom-center point of
        // the model's bounding box. This fixes the off-by-half-a-width bug
        // where the character was drawn with its top-left at the given coords.
        model.anchor.set(0.5, 1.0);

        app.stage.addChild(model as unknown as import("pixi.js").DisplayObject);

        // --- Fit model into viewport --------------------------------------
        const fit = () => {
          const { width: cw, height: ch } = app.screen;
          // Reset scale to read native bounds, then re-scale.
          model.scale.set(1);
          const nativeW = model.width;
          const nativeH = model.height;
          if (!nativeW || !nativeH) return;
          // Take ~92% of canvas height; the character can lean slightly wider
          // than the canvas (head/hair overflow) but we cap by width too.
          const scale = Math.min((cw * 1.2) / nativeW, (ch * 0.98) / nativeH);
          model.scale.set(scale);
          // Because anchor = (0.5, 1), placing x=cw/2, y=ch anchors the
          // character's feet-center to the canvas bottom-center.
          model.x = cw / 2;
          model.y = ch;
        };
        fit();

        const ro = new ResizeObserver(() => {
          if (!handles.app) return;
          app.renderer.resize(
            container.clientWidth,
            container.clientHeight,
          );
          fit();
        });
        ro.observe(container);
        handles.resizeObserver = ro;

        // --- Pointer interactions -----------------------------------------
        (model as AnyObj).on("hit", () => {
          queueMicrotask(() => {
            const m = model as AnyObj;
            try {
              if (typeof m.motion === "function") m.motion("");
              if (typeof m.expression === "function") m.expression();
            } catch (e) {
              console.warn("[Live2DMao] motion/expression trigger failed", e);
            }
          });
          onTapHead?.();
          onTapBody?.();
        });

        // --- TTS lip-sync -------------------------------------------------
        // Attach to the page-shared <audio>. We only do this once per audio
        // element (via SRC_KEY), so StrictMode double-mount is safe.
        const audio = audioElementRef?.current ?? null;
        if (audio) {
          const ctx = getSharedAudioContext();
          if (ctx) {
            const source = getOrCreateSource(audio, ctx);
            if (source) {
              const analyser = ctx.createAnalyser();
              analyser.fftSize = 512;
              analyser.smoothingTimeConstant = 0.6;
              source.connect(analyser);
              // Explicit ArrayBuffer so the Uint8Array's generic is
              // `Uint8Array<ArrayBuffer>` — required by the TS 5.7+ stricter
              // signature of AnalyserNode.getByteTimeDomainData.
              const dataArray = new Uint8Array(
                new ArrayBuffer(analyser.frequencyBinCount),
              );
              handles.analyser = analyser;
              handles.dataArray = dataArray;

              // Resume the context the first time the user interacts. Browsers
              // start AudioContext in "suspended" state until a gesture.
              const resumeOnce = () => {
                ctx.resume().catch(() => {
                  /* noop */
                });
                document.removeEventListener("click", resumeOnce);
                document.removeEventListener("touchstart", resumeOnce);
                document.removeEventListener("keydown", resumeOnce);
              };
              document.addEventListener("click", resumeOnce, { once: true });
              document.addEventListener("touchstart", resumeOnce, {
                once: true,
              });
              document.addEventListener("keydown", resumeOnce, { once: true });

              // Pixi Ticker callback drives the mouth parameter. Lowest
              // priority (-25) runs AFTER Live2DModel.update, so our
              // setParameterValueById isn't overwritten by motion playback.
              const tickerFn = () => {
                if (!handles.analyser || !handles.dataArray) return;
                const coreModel = (model as AnyObj).internalModel?.coreModel;
                if (!coreModel || typeof coreModel.setParameterValueById !== "function") {
                  return;
                }

                // If audio isn't playing, close the mouth.
                const playing =
                  audio && !audio.paused && !audio.ended && audio.currentTime > 0;
                if (!playing) {
                  coreModel.setParameterValueById("ParamA", 0);
                  return;
                }

                handles.analyser.getByteTimeDomainData(handles.dataArray);
                // RMS centered at 128 (mid-point of Uint8 waveform).
                let sum = 0;
                const n = handles.dataArray.length;
                for (let i = 0; i < n; i++) {
                  const v = (handles.dataArray[i] - 128) / 128;
                  sum += v * v;
                }
                const rms = Math.sqrt(sum / n);
                // Map RMS [0, ~0.25] -> ParamA [0, 1]. Apply a small gate to
                // avoid jitter from ambient noise / silence artifacts.
                const gated = rms < 0.02 ? 0 : rms;
                const value = Math.max(0, Math.min(1, gated * 4));
                coreModel.setParameterValueById("ParamA", value);
              };
              handles.tickerFn = tickerFn;
              // UPDATE_PRIORITY.LOW = -25 in PIXI 7
              app.ticker.add(tickerFn, undefined, -25);
            }
          }
        }

        setStatus("ready");
      } catch (err) {
        console.error("[Live2DMao] init failed:", err);
        if (!disposed) {
          setStatus("error");
          setError(err instanceof Error ? err.message : String(err));
        }
      }
    })();

    return () => {
      disposed = true;
      try {
        handles.resizeObserver?.disconnect();
      } catch {
        /* noop */
      }
      try {
        if (handles.tickerFn && handles.app?.ticker) {
          handles.app.ticker.remove(handles.tickerFn);
        }
      } catch {
        /* noop */
      }
      try {
        handles.analyser?.disconnect();
      } catch {
        /* noop */
      }
      try {
        handles.model?.destroy();
      } catch {
        /* noop */
      }
      try {
        handles.app?.destroy(true, {
          children: true,
          texture: true,
          baseTexture: true,
        });
      } catch {
        /* noop */
      }
      if (handles.canvas && handles.canvas.parentNode) {
        handles.canvas.parentNode.removeChild(handles.canvas);
      }
      // NOTE: we intentionally do NOT close the shared AudioContext or
      // disconnect the MediaElementSource. They're attached to the page's
      // <audio> element and must survive component unmounts / HMR so that
      // the next Live2DMao instance (or plain TTS audio) keeps working.
    };
    // audioElementRef is a stable RefObject — its identity doesn't change —
    // so listing it in deps is safe and won't re-run the effect unnecessarily.
  }, [modelUrl, width, height, onTapHead, onTapBody, audioElementRef]);

  return (
    <div
      ref={containerRef}
      className={className ?? "live2d-mao-container"}
      style={
        width !== undefined && height !== undefined
          ? { width, height }
          : { width: "100%", height: "100%" }
      }
      data-status={status}
      aria-hidden={status !== "ready"}
      role="img"
      aria-label="Live2D 数字人导览助手"
    >
      {status === "error" ? (
        <div className="live2d-mao-error" role="alert">
          数字人加载失败
          <br />
          <span style={{ fontSize: 10, opacity: 0.7 }}>{error}</span>
        </div>
      ) : null}
    </div>
  );
}
