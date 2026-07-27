import { UploadForm } from "@/components/UploadForm";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 bg-white px-6 py-16 text-center dark:bg-neutral-950">
      <div className="flex flex-col items-center gap-3">
        <h1 className="text-4xl font-bold tracking-tight text-neutral-900 sm:text-5xl dark:text-neutral-50">
          BriefPilot
        </h1>
        <p className="text-lg text-neutral-600 dark:text-neutral-400">
          AI Case Manager for German Bureaucracy
        </p>
        <p className="max-w-md text-sm text-neutral-500 dark:text-neutral-500">
          Upload a photo or PDF of an official German letter and get a plain-English explanation,
          the deadlines that matter, and what to do next.
        </p>
      </div>

      <UploadForm />
    </main>
  );
}
