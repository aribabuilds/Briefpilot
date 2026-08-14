import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy — BriefPilot",
  description: "What happens to your document, in plain language.",
};

// M23: "I can read, in plain language, exactly what happens to my data — and
// it matches what the code actually does" (CLAUDE.md §5.6). Every claim
// below is written to describe the actual implementation as of M22, not an
// aspiration -- see the inline references to the code/ADR that makes each
// one true. If a future change makes a line here false, that's a bug in
// this page, not just in the code.
export default function PrivacyPage() {
  return (
    <main className="flex min-h-screen flex-col items-center bg-white px-6 py-16 dark:bg-neutral-950">
      <div className="flex w-full max-w-2xl flex-col gap-8">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-50">
            What happens to your document
          </h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-500">
            In plain language, matching what the code actually does — not a legal template.
          </p>
        </div>

        <Section title="No account, ever">
          <p>
            There is nothing to sign up for and nothing to log into. You get a private link to your
            result; anyone who has that exact link can view it while it exists, the same way a
            shared document link works. There is no username, password, or email address anywhere in
            this app.
          </p>
        </Section>

        <Section title="What's stored, and for how long">
          <p>
            Your uploaded photo or PDF, and everything extracted from it (text, dates, amounts,
            explanation), are kept in this server&apos;s memory — not written to a database or a
            disk. That has a consequence worth stating plainly: if the server restarts for any
            reason, everything is gone immediately, before the 24-hour limit below ever applies.
          </p>
          <p>
            Short of a restart, your document is automatically and permanently deleted no more than
            24 hours after upload. A background check runs roughly once an hour and removes anything
            past that age — so in practice something usually disappears a little before the 24-hour
            mark, never meaningfully after it.
          </p>
        </Section>

        <Section title="Delete it yourself, any time">
          <p>
            Every result page has a &quot;Delete my document&quot; button. It asks you to confirm
            once, then removes both your original file and everything extracted from it. The button
            only tells you it&apos;s done after checking that the document is actually gone — not
            just that the delete request was sent.
          </p>
        </Section>

        <Section title="What leaves this server">
          <p>
            The text read from your letter — and only the text, never the original image — is sent
            to Google&apos;s Gemini API to classify the letter type, extract fields, and write the
            plain-English explanation. That is a real third party seeing the content of your letter,
            and you should know that before uploading something sensitive. The photo/PDF itself is
            never sent anywhere except to this server; the text extraction (OCR) that reads it runs
            entirely on this server, with no external service involved.
          </p>
        </Section>

        <Section title="What this app doesn't do">
          <ul className="list-disc space-y-1 pl-5">
            <li>No analytics, no ad trackers, no third-party scripts on any page.</li>
            <li>No selling, sharing, or otherwise monetizing anything you upload.</li>
            <li>
              Technical logs record job IDs, timing, and error types for debugging — never the text
              of your letter or what was extracted from it.
            </li>
          </ul>
        </Section>

        <Section title="One more honest thing">
          <p>
            BriefPilot is an independently-built portfolio project, not an operated commercial
            service with a support team or a company behind it. Everything above describes what the
            current code actually does — worth knowing before uploading a real government letter
            with real consequences.
          </p>
        </Section>

        <Link
          href="/"
          className="text-sm text-neutral-500 underline-offset-4 hover:underline dark:text-neutral-400"
        >
          ← Back to BriefPilot
        </Link>
      </div>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">{title}</h2>
      <div className="flex flex-col gap-2 text-sm leading-relaxed text-neutral-600 dark:text-neutral-400">
        {children}
      </div>
    </div>
  );
}
