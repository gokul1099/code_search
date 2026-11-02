import { useState } from "react";

export default function QuestionForm({ onSubmit, disabled, placeholder }) {
  const [question, setQuestion] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setQuestion("");
  }

  return (
    <form onSubmit={handleSubmit} className="mx-auto flex max-w-3xl gap-2">
      <input
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        disabled={disabled}
        aria-label="Question about the indexed code"
        placeholder={placeholder}
        className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none disabled:bg-slate-100 disabled:text-slate-400"
      />
      <button
        type="submit"
        disabled={disabled}
        className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        Send
      </button>
    </form>
  );
}
