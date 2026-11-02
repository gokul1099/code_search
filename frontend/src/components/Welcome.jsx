const STEPS = [
  { title: "Index a repo", text: "Point it at a local folder or a public GitHub repo. Only Python files are read." },
  { title: "Watch it work", text: "The progress panel shows each file as it is parsed and embedded." },
  { title: "Ask in plain English", text: "Answers come only from the code, with the file and line numbers they used." },
];

export default function Welcome() {
  return (
    <section className="rounded-xl border border-dashed border-slate-300 bg-white p-6">
      <h2 className="text-base font-semibold">How it works</h2>
      <ol className="mt-4 space-y-4">
        {STEPS.map((step, i) => (
          <li key={step.title} className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700">
              {i + 1}
            </span>
            <div>
              <p className="text-sm font-medium">{step.title}</p>
              <p className="text-sm text-slate-500">{step.text}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
