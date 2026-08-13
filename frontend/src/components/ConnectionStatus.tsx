"use client";

import { useEffect, useState } from "react";

import { getHealth } from "@/services/api";

type Status = "checking" | "connected" | "unreachable";

export function ConnectionStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let cancelled = false;
    setStatus("checking");
    getHealth()
      .then(() => {
        if (!cancelled) setStatus("connected");
      })
      .catch(() => {
        if (!cancelled) setStatus("unreachable");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const dotColor =
    status === "connected"
      ? "bg-green-500"
      : status === "unreachable"
        ? "bg-red-500"
        : "bg-neutral-400";

  const label =
    status === "connected"
      ? "Backend connected"
      : status === "unreachable"
        ? "Backend unreachable"
        : "Checking backend…";

  return (
    <div
      role="status"
      className="flex items-center gap-2 rounded-full border border-neutral-200 px-3 py-1 text-xs text-neutral-600 dark:border-neutral-800 dark:text-neutral-400"
    >
      <span className={`h-2 w-2 rounded-full ${dotColor}`} aria-hidden="true" />
      {label}
    </div>
  );
}
