export function TextStream({ text }: { text: string }) {
  return (
    <>
      {Array.from(text).map((char, index) => (
        <span
          className="token-entry"
          key={`${char}-${index}`}
          style={{ animationDelay: `${Math.min(index * 12, 420)}ms` }}
        >
          {char}
        </span>
      ))}
    </>
  );
}

