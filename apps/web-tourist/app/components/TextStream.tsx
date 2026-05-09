export function TextStream({ text }: { text: string }) {
  if (!text) return null;

  // Split into word-like chunks (Chinese: 2-3 chars, English: words)
  const words: string[] = [];
  for (const match of text.matchAll(/[一-鿿]{1,3}|\S+\s*/g)) {
    words.push(match[0]);
  }

  return (
    <span aria-label={text} role="text">
      <span aria-hidden="true">
        {words.map((word, index) => (
          <span
            className="token-entry"
            key={`${word}-${index}`}
            style={{ animationDelay: `${Math.min(index * 60, 600)}ms` }}
          >
            {word}
          </span>
        ))}
      </span>
    </span>
  );
}
