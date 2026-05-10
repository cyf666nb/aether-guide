"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { TrustBar, VisitorNav } from "../components/VisitorChrome";
import { createSession, ensureTouristToken } from "../lib/api";

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

async function compressImage(
  source: HTMLVideoElement | HTMLImageElement,
  nativeWidth: number,
  nativeHeight: number,
): Promise<string | null> {
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

export default function PhotoPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [result, setResult] = useState<PhotoResult | null>(null);
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
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
        setCameraActive(true);
      } else {
        stream.getTracks().forEach((t) => t.stop());
      }
    } catch {
      setError("无法访问摄像头，请允许权限或上传图片");
    } finally {
      setCameraStarting(false);
    }
  }, [cameraActive, cameraStarting]);

  // Cleanup: stop camera tracks when user navigates away.
  useEffect(() => {
    const video = videoRef.current;
    return () => {
      // Snapshot the video element at effect-time so the cleanup runs on a
      // stable reference even if the ref is cleared on unmount.
      if (video?.srcObject) {
        (video.srcObject as MediaStream).getTracks().forEach((t) => t.stop());
        video.srcObject = null;
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
      try {
        const token = await ensureTouristToken();
        const apiBase = `${window.location.protocol}//${window.location.hostname}:8000`;
        const res = await fetch(
          `${apiBase}/api/v1/sessions/${sessionId}/photo`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              scenic_id: "demo-scenic",
              image_base64: base64,
            }),
          },
        );
        const data = await res.json();
        if (data.data) {
          setResult(data.data);
        } else {
          setError(data.message || "识别失败");
        }
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

  return (
    <main className="tourist-frame photo-page">
      <TrustBar mode={result?.status === "located" ? "online" : "visual"} />
      <VisitorNav />

      {/* 取景器 */}
      <section className="viewfinder" aria-label="拍照识景取景框">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            borderRadius: "12px",
            display: cameraActive ? "block" : "none",
          }}
        />
        {!cameraActive ? (
          <div className="viewfinder-placeholder">
            <p className="type-body">点击下方按钮开启相机后识别景点。</p>
          </div>
        ) : null}
        <div className="scan-beam" />
        <svg viewBox="0 0 320 320" className="viewfinder-frame">
          <circle
            cx="160"
            cy="160"
            r="112"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.25"
          />
          <path
            d="M80 56H52v42M240 56h28v42M80 264H52v-42M240 264h28v-42"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.25"
            strokeLinecap="round"
          />
        </svg>
      </section>

      {/* 操作按钮 */}
      <section className="photo-actions">
        <button
          className="primary-button"
          onClick={primaryAction}
          disabled={primaryDisabled}
          type="button"
        >
          {primaryLabel}
        </button>
        <label className="thin-button upload-btn">
          上传图片
          <input
            type="file"
            accept="image/*"
            onChange={handleUpload}
            style={{ display: "none" }}
          />
        </label>
      </section>

      {error ? (
        <section className="result-sheet" role="alert">
          <p className="caption">提示</p>
          <p className="type-body">{error}</p>
        </section>
      ) : null}

      {result ? (
        <section className="result-sheet">
          <p className="caption">
            {result.status === "located" ? "已识别" : "识别中 · VPS"}
          </p>
          {result.landmark_name ? (
            <>
              <h1 className="type-heading type-heading-2">
                {result.landmark_name}
              </h1>
              <p className="type-body">
                置信 {Math.round(result.confidence * 100)}%。{result.narration}
              </p>
              {result.follow_up ? (
                <p
                  className="type-body"
                  style={{ marginTop: 8, color: "var(--gold-light)" }}
                >
                  {result.follow_up}
                </p>
              ) : null}
            </>
          ) : (
            <>
              <h1 className="type-heading type-heading-2">未识别到景点</h1>
              <p className="type-body">{result.narration}</p>
            </>
          )}
        </section>
      ) : null}
    </main>
  );
}
