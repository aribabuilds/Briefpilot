import Link from "next/link";

import { ConnectionStatus } from "@/components/ConnectionStatus";
import { UploadForm } from "@/components/UploadForm";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 bg-white px-6 py-16 text-center dark:bg-neutral-950">
      <ConnectionStatus />

      <div className="flex flex-col items-center gap-3">
        <h1 className="text-4xl font-bold tracking-tight text-neutral-900 sm:text-5xl dark:text-neutral-50">
          BriefPilot
        </h1>
        <p className="text-lg text-neutral-600 dark:text-neutral-400">
          Understand your German mail in plain English
        </p>
        <p className="max-w-md text-sm text-neutral-500 dark:text-neutral-500">
          Upload a photo or PDF of an official German letter and get a plain-English explanation,
          the deadlines that matter, and what to do next — with every claim traceable back to the
          original text.
        </p>
      </div>

      <UploadForm />

      <Link
        href="/privacy"
        className="text-xs text-neutral-400 underline-offset-4 hover:underline dark:text-neutral-600"
      >
        No account. Auto-deleted within 24h. What happens to your data →
      </Link>
    </main>
  );
}
