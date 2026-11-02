import { useState } from "react";

export default function IndexForm({ onSubmit, disabled }) {
  const [source, setSource] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = source.trim();
    if (trimmed && !disabled) onSubmit(trimmed);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-1 gap-2">
      <input
        value={source}
        onChange={(e) => setSource(e.target.value)}
        disabled={disabled}
        required
        aria-label="Folder path or GitHub URL"
        placeholder="e.g. /Users/you/project or https://github.com/owner/repo"
        className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none disabled:bg-slate-100"
      />
      <button
        type="submit"
        disabled={disabled}
        className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {disabled ? "Indexing..." : "Index"}
      </button>
    </form>
  );
}
