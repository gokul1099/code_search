import { useEffect, useRef } from "react";

// Live view of an indexing job: current step, percentage bar, and the full log.
export default function IndexProgress({ job, onDismiss }) {
  const running = job.status === "running";
  const failed = job.status === "failed";
  const percent = Math.round(job.progress * 100);
  const logRef = useRef(null);

  // Keep the newest log line in view.
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [job.events.length]);

  const headline = running ? job.stage : failed ? "Indexing failed" : "Indexing complete";
  const dot = running ? "bg-indigo-500 animate-pulse" : failed ? "bg-red-500" : "bg-emerald-500";
  const bar = failed ? "bg-red-500" : "bg-indigo-600";

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${dot}`} />
          <p className="truncate text-sm font-medium" title={headline}>{headline}</p>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <span className="text-xs tabular-nums text-slate-500">{percent}%</span>
          {!running && (
            <button onClick={onDismiss} className="text-xs text-slate-400 hover:text-slate-600">
              Dismiss
            </button>
          )}
        </div>
      </div>

      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full transition-all duration-500 ${bar}`}
          style={{ width: `${percent}%` }}
        />
      </div>

      {failed && job.error && (
        <p className="mt-3 rounded-lg bg-red-50 p-2 text-xs text-red-700">{job.error}</p>
      )}

      <details open={running || failed} className="mt-3">
        <summary className="cursor-pointer text-xs text-slate-500 select-none">
          Activity log ({job.events.length})
        </summary>
        <ol
          ref={logRef}
          className="mt-2 max-h-48 space-y-1 overflow-y-auto rounded-lg bg-slate-50 p-3 font-mono text-xs text-slate-600"
        >
          {job.events.map((event, i) => (
            <li key={i} className="flex gap-2">
              <span className="shrink-0 text-slate-400">{event.time}</span>
              <span className="break-all">{event.message}</span>
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}
