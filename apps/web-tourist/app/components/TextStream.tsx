"use client";

import dynamic from "next/dynamic";
import { Fragment } from "react";

// react-markdown + unified + remark + rehype pulls in ~100KB of parsed JS.
// The vast majority of guide replies are plain Chinese text with at most
// line breaks, so we:
//   1) render plain text synchronously via a tiny regex split, and
//   2) only load react-markdown when the text actually contains markdown.
const Markdown = dynamic(() => import("react-markdown"), { ssr: false });

// Detects characters that markdown cares about: fenced code, headings,
// lists, links, bold/italic, blockquotes, tables, inline code.
const MARKDOWN_HINT = /(^|\n)\s*(#|>|[-*+] |\d+\. |```)|[*_`~\[!]/;

export function TextStream({ text }: { text: string }) {
  if (!text) return null;

  if (!MARKDOWN_HINT.test(text)) {
    // Preserve paragraph-ish line breaks cheaply.
    const lines = text.split(/\n/);
    return (
      <span className="guide-markdown">
        {lines.map((line, i) => (
          <Fragment key={i}>
            {line}
            {i < lines.length - 1 ? <br /> : null}
          </Fragment>
        ))}
      </span>
    );
  }

  return (
    <span className="guide-markdown">
      <Markdown>{text}</Markdown>
    </span>
  );
}
