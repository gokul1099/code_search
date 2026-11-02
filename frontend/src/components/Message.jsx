export default function Message({ message }) {
  const { role, text, sources = [], truncated, pending, isError } = message;

  if (role === "system") {
    return (
      <p className={`text-center text-xs ${isError ? "text-red-600" : "text-slate-500"}`}>{text}</p>
    );
  }

  if (role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2 text-sm whitespace-pre-wrap text-white">
          {text}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-2 text-sm whitespace-pre-wrap shadow-sm">
        {pending ? (
          <span className="text-slate-400">Thinking...</span>
        ) : (
          <span className={isError ? "text-red-600" : ""}>{text}</span>
        )}

        {truncated && (
          <p className="mt-2 text-xs text-amber-600">The answer was cut off. Try a narrower question.</p>
        )}

        {sources.length > 0 && (
          <>
            <p className="mt-3 text-xs font-medium text-slate-500">Sources</p>
            <div className="mt-1 flex flex-wrap gap-1">
              {sources.map((s) => (
                <span
                  key={`${s.id}-${s.start_line}`}
                  className="rounded-full bg-slate-100 px-2 py-0.5 font-mono text-xs text-slate-600"
                >
                  {`${s.id} : ${s.start_line}-${s.end_line}`}
                </span>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
