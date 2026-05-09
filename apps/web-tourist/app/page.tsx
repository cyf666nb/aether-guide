"use client";

import { HumanBadge } from "@aether/design-system/icons";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { TextStream } from "./components/TextStream";
import { TrustBar, VisitorNav } from "./components/VisitorChrome";
import { createSession, getLandmarks, wsUrl } from "./lib/api";

type ChatMessage = {
  speaker: "你" | "知行" | "System";
  text: string;
  role: "user" | "guide";
};

export default function TouristHome() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("你好，给我介绍一下附近最值得先看的景点。");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      speaker: "知行",
      text: "我会根据你所在的位置，把讲解、路线和安全提醒串成一段顺路的旅程。",
      role: "guide"
    }
  ]);
  const socketRef = useRef<WebSocket | null>(null);
  const { data: landmarks = [] } = useQuery({
    queryKey: ["landmarks"],
    queryFn: () => getLandmarks()
  });

  useEffect(() => {
    let mounted = true;
    createSession()
      .then((session) => {
        if (!mounted) return;
        setSessionId(session.id);
        const socket = new WebSocket(wsUrl(session.id));
        socketRef.current = socket;
        socket.addEventListener("message", (event) => {
          const payload = JSON.parse(event.data) as { data: { content: string } };
          setMessages((current) => [
            ...current,
            { speaker: "知行", text: payload.data.content.replace(/\[\^seed:intro]/g, ""), role: "guide" }
          ]);
        });
      })
      .catch(() => {
        // Backend unavailable — demo data and offline mode already work via fallback
      });
    return () => {
      mounted = false;
      socketRef.current?.close();
    };
  }, []);

  function send() {
    const text = input.trim();
    if (!text) return;
    setMessages((current) => [...current, { speaker: "你", text, role: "user" }]);
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "user_text", text, locale: "zh-CN" }));
    } else {
      setMessages((current) => [
        ...current,
        { speaker: "知行", text: "当前使用本地知识库演示模式。我先带你从月门听泉走到松台远眺。", role: "guide" }
      ]);
    }
    setInput("");
  }

  const spot = landmarks[0]?.name ?? "月门听泉";

  return (
    <main className="tourist-frame">
      <TrustBar mode={sessionId ? "online" : "offline"} />
      <VisitorNav />
      <section className="hero-stage">
        <img src="/scenes/forest.png" alt="清晨森林景区" />
        <div className="scene-mask" />
        <div className="guide-presence" aria-label="数字人等待中">
          <HumanBadge />
        </div>
        <div className="current-spot">
          <div>
            <p className="caption">当前讲解</p>
            <strong>{spot}</strong>
          </div>
          <button className="thin-button" type="button">
            跳过 ▸
          </button>
        </div>
      </section>
      <section className="conversation" aria-live="polite">
        {messages.map((message, index) => (
          <article className={`message-row ${message.role === "user" ? "user" : ""}`} key={index}>
            <p className="caption">{message.speaker}</p>
            <div className="message-bubble">
              {message.role === "guide" ? <TextStream text={message.text} /> : message.text}
              {message.role === "guide" && <span className="citation">1</span>}
            </div>
          </article>
        ))}
      </section>
      <section className="composer-dock">
        <label className="voice-field">
          <span className="caption">按住说话</span>
          <input
            className="field-line"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="输入文字..."
          />
          <span className="wave-bars" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
            <span />
          </span>
        </label>
        <button className="primary-button" type="button" onClick={send}>
          发送
        </button>
      </section>
    </main>
  );
}

