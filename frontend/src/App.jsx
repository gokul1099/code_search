import { useEffect, useState } from "react";
import { askRepo, getJob, startIndex } from "./api.js";
import IndexForm from "./components/IndexForm.jsx";
import IndexProgress from "./components/IndexProgress.jsx";
import Message from "./components/Message.jsx";
import QuestionForm from "./components/QuestionForm.jsx";
import Welcome from "./components/Welcome.jsx";

const SUGGESTIONS = [
  "What does this project do?",
  "Where does the program start?",
  "How are errors handled?",
];

// "/Users/me/shop" -> "shop", "https://github.com/acme/shop" -> "shop"
const repoName = (source) => source.split(/[\\/]/).filter(Boolean).pop() ?? source;

export default function App() {
  const [repo, setRepo] = useState(null);   // { id, source, files, chunks } once indexing succeeds
  const [job, setJob] = useState(null);     // latest snapshot of the indexing job from the server
  const [asking, setAsking] = useState(false);
  const [messages, setMessages] = useState([]);

  const indexing = job?.status === "running";
  const addMessage = (message) => setMessages((prev) => [...prev, message]);

  // While a job runs, ask the server for its progress about once a second.
  useEffect(() => {
    if (!job || job.status !== "running") return;
    const timer = setTimeout(async () => {
      try {
        const next = await getJob(job.id);
        setJob(next);
        if (next.status === "done") {
          setRepo({
            id: next.result.repo_id,
            source: next.source,
            files: next.result.files,
            chunks: next.result.chunks,
          });
          addMessage({
            role: "system",
            text: `Ready. ${next.result.files} files and ${next.result.chunks} chunks indexed from ${repoName(next.source)}.`,
          });
        } else if (next.status === "failed") {
          addMessage({ role: "system", text: `Indexing failed: ${next.error}`, isError: true });
        }
      } catch (err) {
        setJob((prev) => ({ ...prev, status: "failed", error: `Lost contact with the server: ${err.message}` }));
      }
    }, 1000);
    return () => clearTimeout(timer);
  }, [job]);

  async function handleIndex(source) {
    try {
      const { job_id } = await startIndex(source);
      setRepo(null);
      setMessages([]);
      setJob({ id: job_id, source, status: "running", stage: "Starting...", progress: 0, events: [] });
    } catch (err) {
      addMessage({ role: "system", text: `Could not start indexing: ${err.message}`, isError: true });
    }
  }

  async function handleAsk(question) {
    addMessage({ role: "user", text: question });
    addMessage({ role: "assistant", pending: true });
    setAsking(true);
    try {
      const data = await askRepo(repo.id, question);
      setMessages((prev) => [
        ...prev.slice(0, -1),
        {
          role: "assistant",
          text: data.answer || "(no answer returned)",
          sources: data.sources,
          truncated: data.finish_reason === "length",
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "assistant", text: `Error: ${err.message}`, isError: true },
      ]);
    } finally {
      setAsking(false);
    }
  }

  const placeholder = !repo
    ? indexing
      ? "Indexing... you can ask once it's ready"
      : "Index a repo first"
    : asking
      ? "Waiting for the answer..."
      : "Ask about this code...";

  return (
    <div className="flex h-screen flex-col bg-slate-100 text-slate-900">
      <header className="border-b border-slate-200 bg-white px-4 py-3">
        <div className="mx-auto flex max-w-3xl flex-col gap-3">
          <div className="flex items-center justify-between gap-3">
            <h1 className="text-lg font-semibold">Code Search</h1>
            {repo && (
              <div className="flex min-w-0 items-center gap-2">
                <span
                  className="truncate rounded-full bg-emerald-50 px-2.5 py-1 text-xs text-emerald-700"
                  title={repo.source}
                >
                  {repoName(repo.source)} · {repo.files} files · {repo.chunks} chunks
                </span>
                {messages.length > 0 && (
                  <button
                    onClick={() => setMessages([])}
                    className="shrink-0 text-xs text-slate-500 hover:text-slate-800"
                  >
                    Clear chat
                  </button>
                )}
              </div>
            )}
          </div>
          <IndexForm onSubmit={handleIndex} disabled={indexing} />
          <p className="text-xs text-slate-500">
            Accepts a folder on this computer or a public GitHub URL. Only Python files are indexed.
          </p>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
          {!repo && !job && <Welcome />}
          {job && <IndexProgress job={job} onDismiss={() => setJob(null)} />}

          {messages.map((message, i) => (
            <Message key={i} message={message} />
          ))}

          {repo && messages.length === 0 && (
            <div className="flex flex-wrap gap-2">
              <p className="w-full text-xs text-slate-500">Try asking:</p>
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => handleAsk(suggestion)}
                  disabled={asking}
                  className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-sm hover:border-indigo-400 hover:text-indigo-700 disabled:opacity-50"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}
        </div>
      </main>

      <footer className="border-t border-slate-200 bg-white px-4 py-3">
        <QuestionForm onSubmit={handleAsk} disabled={!repo || asking} placeholder={placeholder} />
      </footer>
    </div>
  );
}
