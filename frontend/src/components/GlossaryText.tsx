"use client";

import { useState } from "react";

import { GLOSSARY } from "@/lib/glossary";

// Longest-first so a multi-word term ("Punkte in Flensburg") matches before
// a shorter term that happens to be its substring.
const TERMS = Object.keys(GLOSSARY).sort((a, b) => b.length - a.length);

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// One shared, module-level regex: rebuilding it per render is wasted work,
// and String.split (unlike .exec()/.test()) doesn't depend on the regex's
// own lastIndex state, so a single shared instance is safe to reuse.
const TERM_PATTERN = new RegExp(`\\b(${TERMS.map(escapeRegExp).join("|")})\\b`, "gi");

function lookup(term: string): string | undefined {
  const key = TERMS.find((candidate) => candidate.toLowerCase() === term.toLowerCase());
  return key ? GLOSSARY[key] : undefined;
}

interface GlossaryTextProps {
  text: string;
}

// Splits text on every known glossary term and renders each match as a
// tappable button with a definition popover -- everything else renders as
// plain text, untouched. Client-only (needs onClick state), unlike the
// server-renderable pieces of the results page.
export function GlossaryText({ text }: GlossaryTextProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  if (TERMS.length === 0) return <>{text}</>;

  const parts = text.split(TERM_PATTERN);

  return (
    <>
      {parts.map((part, index) => {
        const definition = lookup(part);
        if (!definition) {
          return <span key={index}>{part}</span>;
        }
        const isActive = activeIndex === index;
        return (
          <span key={index} className="relative">
            <button
              type="button"
              onClick={() => setActiveIndex(isActive ? null : index)}
              className="underline decoration-neutral-400 decoration-dotted underline-offset-2 hover:decoration-neutral-600 dark:decoration-neutral-500 dark:hover:decoration-neutral-300"
              aria-expanded={isActive}
            >
              {part}
            </button>
            {isActive && (
              <span
                role="tooltip"
                className="absolute left-0 top-full z-10 mt-1 w-64 rounded-lg border border-neutral-200 bg-white p-2 text-left text-xs font-normal text-neutral-700 shadow-lg dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-300"
              >
                <span className="mb-1 block font-semibold text-neutral-900 dark:text-neutral-50">
                  {part}
                </span>
                {definition}
              </span>
            )}
          </span>
        );
      })}
    </>
  );
}
