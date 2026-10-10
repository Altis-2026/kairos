import type { ReactNode } from "react";

const INLINE = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\(https?:\/\/[^\s)]+\)|_[^_\s][^_]*_)/g;

function inline(text: string, keyBase: string): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  let i = 0;
  for (const match of text.matchAll(INLINE)) {
    const token = match[0];
    const at = match.index ?? 0;
    if (at > last) out.push(text.slice(last, at));
    const key = `${keyBase}-${i++}`;
    if (token.startsWith("**")) {
      out.push(
        <strong key={key} className="font-semibold text-ink">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith("`")) {
      out.push(
        <code key={key} className="font-mono text-[0.92em] text-teal">
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith("[")) {
      const label = token.slice(1, token.indexOf("]"));
      const href = token.slice(token.indexOf("(") + 1, -1);
      out.push(
        <a
          key={key}
          href={href}
          target="_blank"
          rel="noreferrer"
          className="text-teal underline-offset-2 hover:underline"
        >
          {label}
        </a>
      );
    } else {
      out.push(
        <em key={key} className="italic">
          {token.slice(1, -1)}
        </em>
      );
    }
    last = at + token.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export default function Markdown({
  text,
  size = "text-sm",
  headingClass = "font-mono text-[10px] tracking-[0.18em] text-amber uppercase",
}: {
  text: string;
  size?: string;
  headingClass?: string;
}) {
  const blocks: ReactNode[] = [];
  let para: string[] = [];
  let bullets: string[] = [];
  let ordered = false;

  const flush = (key: string) => {
    if (bullets.length) {
      const items = bullets.map((b, i) => (
        <li key={i} className="flex gap-2">
          <span className="text-amber shrink-0">{ordered ? `${i + 1}.` : "·"}</span>
          <span>{inline(b, `${key}-li${i}`)}</span>
        </li>
      ));
      blocks.push(
        <ul key={`u${key}`} className="space-y-1">
          {items}
        </ul>
      );
      bullets = [];
    }
    if (para.length) {
      blocks.push(<p key={`p${key}`}>{inline(para.join(" "), `p${key}`)}</p>);
      para = [];
    }
  };

  text.split("\n").forEach((raw, i) => {
    const line = raw.trim();
    const numbered = /^\d+[.)]\s+/.test(line);
    if (/^#{1,6}\s/.test(line)) {
      flush(`${i}`);
      blocks.push(
        <h4 key={`h${i}`} className={`${headingClass} mt-3 first:mt-0`}>
          {line.replace(/^#+\s*/, "")}
        </h4>
      );
    } else if (/^[-*•]\s+/.test(line) || numbered) {
      if (para.length) flush(`${i}`);
      ordered = numbered;
      bullets.push(line.replace(/^([-*•]|\d+[.)])\s+/, ""));
    } else if (!line) {
      flush(`${i}`);
    } else {
      if (bullets.length) flush(`${i}`);
      para.push(line);
    }
  });
  flush("end");

  return <div className={`${size} leading-relaxed space-y-2`}>{blocks}</div>;
}
