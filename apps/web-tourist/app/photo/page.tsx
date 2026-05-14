"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { createSession, ensureTouristToken, identifyPhoto } from "../lib/api";

type PhotoResult = {
  status: string;
  landmark_id: string | null;
  landmark_name: string | null;
  confidence: number;
  narration: string;
  follow_up: string | null;
};

// Cap uploaded image dimensions. Upstream VLMs run happily on <=1280px; larger
// images just inflate base64 payload and latency without improving accuracy.
const MAX_DIMENSION = 1280;
const JPEG_QUALITY = 0.72;
const PHOTO_RESULT_STORAGE_KEY = "aether.photo.lastResult";

async function compressImage(
  source: HTMLVideoElement | HTMLImageElement,
  nativeWidth: number,
  nativeHeight: number,
): Promise<string | null> {
  if (nativeWidth <= 0 || nativeHeight <= 0) return null;
  const scale = Math.min(1, MAX_DIMENSION / Math.max(nativeWidth, nativeHeight));
  const width = Math.round(nativeWidth * scale);
  const height = Math.round(nativeHeight * scale);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  ctx.drawImage(source, 0, 0, width, height);
  const dataUrl = canvas.toDataURL("image/jpeg", JPEG_QUALITY);
  const base64 = dataUrl.split(",")[1];
  return base64 ?? null;
}

async function readImageFile(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("无法读取图片"));
    };
    img.src = url;
  });
}

function readStoredResult(): PhotoResult | null {
  if (typeof window !== "object") return null;
  try {
    const raw = window.sessionStorage.getItem(PHOTO_RESULT_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as PhotoResult) : null;
  } catch {
    return null;
  }
}

function writeStoredResult(result: PhotoResult | null): void {
  if (typeof window !== "object") return;
  try {
    if (result) {
      window.sessionStorage.setItem(
        PHOTO_RESULT_STORAGE_KEY,
        JSON.stringify(result),
      );
    } else {
      window.sessionStorage.removeItem(PHOTO_RESULT_STORAGE_KEY);
    }
  } catch {
    // sessionStorage may be unavailable in private/sandboxed contexts.
  }
}

export default function PhotoPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const cameraStreamRef = useRef<MediaStream | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [result, setResult] = useState<PhotoResult | null>(readStoredResult);
  const [loading, setLoading] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraStarting, setCameraStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionLoading, setSessionLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await ensureTouristToken();
        const session = await createSession();
        if (!cancelled) setSessionId(session.id);
      } catch (err) {
        if (!cancelled) {
          setError(
            `会话创建失败: ${err instanceof Error ? err.message : String(err)}`,
          );
        }
      } finally {
        if (!cancelled) setSessionLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Only start the camera from an explicit user gesture — browsers (esp.
  // iOS Safari) are much more permissive when getUserMedia fires inside a
  // click handler, and it's a clearer privacy model for the user.
  const startCamera = useCallback(async () => {
    if (cameraActive || cameraStarting) return;
    setError(null);
    setCameraStarting(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "environment",
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      });
      cameraStreamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
        setCameraActive(true);
      } else {
        stream.getTracks().forEach((t) => t.stop());
        cameraStreamRef.current = null;
      }
    } catch (err) {
      const name = err instanceof DOMException ? err.name : "";
      if (name === "NotAllowedError" || name === "SecurityError") {
        setError("摄像头权限被拒绝，请在浏览器设置中允许访问，或改用上传图片。");
      } else if (name === "NotFoundError" || name === "OverconstrainedError") {
        setError("没有找到可用摄像头，请改用上传图片。");
      } else {
        setError("无法访问摄像头，请允许权限或上传图片。");
      }
    } finally {
      setCameraStarting(false);
    }
  }, [cameraActive, cameraStarting]);

  // Cleanup: stop camera tracks when user navigates away.
  useEffect(() => {
    return () => {
      const stream = cameraStreamRef.current;
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
        cameraStreamRef.current = null;
      }
    };
  }, []);

  const identifyImage = useCallback(
    async (base64: string) => {
      if (!sessionId) {
        setError("会话未就绪，请稍后再试");
        return;
      }
      setLoading(true);
      setError(null);
      setResult(null);
      writeStoredResult(null);
      try {
        const nextResult = await identifyPhoto(sessionId, base64);
        setResult(nextResult);
        writeStoredResult(nextResult);
      } catch {
        setError("网络错误，请重试");
      } finally {
        setLoading(false);
      }
    },
    [sessionId],
  );

  const capture = useCallback(async () => {
    const video = videoRef.current;
    if (!video || !cameraActive) return;
    const base64 = await compressImage(
      video,
      video.videoWidth,
      video.videoHeight,
    );
    if (!base64) {
      setError("无法读取画面，请重试");
      return;
    }
    await identifyImage(base64);
  }, [cameraActive, identifyImage]);

  const handleUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      e.target.value = ""; // allow re-selecting the same file
      if (!file) return;
      try {
        const img = await readImageFile(file);
        const base64 = await compressImage(img, img.width, img.height);
        if (!base64) throw new Error("compress_failed");
        await identifyImage(base64);
      } catch {
        setError("无法读取该图片，换一张试试？");
      }
    },
    [identifyImage],
  );

  const handleRetake = useCallback(() => {
    setResult(null);
    setError(null);
    writeStoredResult(null);
    if (!cameraActive) {
      void startCamera();
    }
  }, [cameraActive, startCamera]);

  const primaryLabel = sessionLoading
    ? "连接中..."
    : loading
      ? "识别中..."
      : !cameraActive
        ? "开始取景"
        : "拍照识别";

  const primaryAction = !cameraActive ? startCamera : capture;
  const primaryDisabled =
    sessionLoading || loading || cameraStarting;
  const askHref = result?.landmark_name
    ? `/?q=${encodeURIComponent(`详细介绍${result.landmark_name}`)}&autoSend=true`
    : null;

  return (
    <main className="tourist-frame photo-page">
      <div className="photo-body">
        {/* Viewfinder */}
        <section className="viewfinder" aria-label="拍照识景取景框">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className={`viewfinder-video ${cameraActive ? "active" : ""}`}
          />
          {!cameraActive && (
            <div className="viewfinder-placeholder">
              <div className="viewfinder-icon" aria-hidden="true">
                <svg viewBox="0 0 64 64" fill="none">
                  <rect x="8" y="14" width="48" height="36" rx="6" stroke="currentColor" strokeWidth="1.5" />
                  <circle cx="32" cy="32" r="10" stroke="currentColor" strokeWidth="1.5" />
                  <circle cx="32" cy="32" r="4" fill="currentColor" opacity="0.5" />
                  <rect x="26" y="8" width="12" height="6" rx="2" stroke="currentColor" strokeWidth="1.5" />
                </svg>
              </div>
              <p className="type-body">开启相机，对准古厝或街巷</p>
              <p className="caption">AI 将自动识别景点并为你讲解</p>
            </div>
          )}
          {loading && (
            <div className="viewfinder-scanning">
              <span className="scanning-line" />
              <p className="caption">正在识别…</p>
            </div>
          )}
          {/* Corner brackets */}
          <div className="viewfinder-corners" aria-hidden="true">
            <span className="vc tl" />
            <span className="vc tr" />
            <span className="vc bl" />
            <span className="vc br" />
          </div>
        </section>

        {/* Sidebar: capture button + upload + result */}
        <div className="photo-side">
          <div className="photo-action-row">
            <button
              className="photo-action-button primary"
              onClick={primaryAction}
              disabled={primaryDisabled}
              type="button"
              aria-label={primaryLabel}
            >
              <span>相机</span>
              <strong>{primaryLabel}</strong>
            </button>

            <label className="photo-action-button upload">
              <span>相册</span>
              <strong>上传图片</strong>
              <input
                type="file"
                accept="image/*"
                onChange={handleUpload}
                style={{ display: "none" }}
              />
            </label>
          </div>

          {(error || result) && (
            <section className={`photo-result ${result ? "has-data" : "is-error"}`}>
              {error ? (
                <>
                  <p className="caption">提示</p>
                  <p className="type-body">{error}</p>
                  <details className="camera-help">
                    <summary>如何开启权限</summary>
                    <p>
                      iOS Safari 可到「设置 / Safari / 相机」允许访问；Android 可在浏览器或系统应用权限里开启摄像头。也可以直接上传相册图片识别。
                    </p>
                  </details>
                </>
              ) : result ? (
                <>
                  <p className="caption">
                    {result.status === "located" ? "已识别景点" : "视觉定位中"}
                  </p>
                  {result.landmark_name ? (
                    <>
                      <h2 className="photo-result-name">{result.landmark_name}</h2>
                      <p className="type-body">{result.narration}</p>
                      <p className="photo-confidence">
                        置信度 {Math.round(result.confidence * 100)}%
                      </p>
                      {result.follow_up && (
                        <p className="photo-followup">{result.follow_up}</p>
                      )}
                      <div className="photo-result-actions">
                        {askHref && (
                          <Link className="primary-button" href={askHref}>
                            听 {result.landmark_name} 讲解
                          </Link>
                        )}
                        <button
                          className="thin-button"
                          type="button"
                          onClick={handleRetake}
                        >
                          重拍
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <h2 className="photo-result-name">未识别到景点</h2>
                      <p className="type-body">{result.narration}</p>
                      <div className="photo-result-actions">
                        <button
                          className="thin-button"
                          type="button"
                          onClick={handleRetake}
                        >
                          再试一次
                        </button>
                      </div>
                    </>
                  )}
                </>
              ) : null}
            </section>
          )}
        </div>
      </div>
    </main>
  );
}
