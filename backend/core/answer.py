from __future__ import annotations

from groq import Groq

from core.config import settings
from core.search import search

SYSTEM = (
    "You answer questions about a code repository using only the code excerpts provided.\n"
    "Rules:\n"
    "1. Answer in at most 4 sentences. Do not paste code unless the question asks for it.\n"
    "2. After each claim, cite the excerpt it comes from in this exact form: (id, lines X-Y).\n"
    "3. If none of the excerpts answer the question, reply exactly: "
    "\"The provided code does not answer this.\" Do not guess or use outside knowledge."
)


class LLMNotConfigured(RuntimeError):
    pass


def _excerpt(hit: dict) -> str:
    return (f'<excerpt id="{hit["id"]}" lines="{hit["start_line"]}-{hit["end_line"]}">\n'
            f'{hit["code"]}\n</excerpt>')


def answer(repo_id: str, question: str, k: int = 5) -> dict:
    """Retrieve the k most relevant chunks, then ask the Groq model to answer from them."""
    if not settings.groq_api_key:
        raise LLMNotConfigured("GROQ_API_KEY is not set in backend/.env")

    hits = search(repo_id, question, k)
    context = "\n\n".join(_excerpt(h) for h in hits)

    client = Groq(api_key=settings.groq_api_key)
    response = client.chat.completions.create(
        model=settings.groq_model,
        max_completion_tokens=2000,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"{context}\n\nQuestion: {question}"},
        ],
    )

    choice = response.choices[0]
    return {
        "answer": choice.message.content or "",
        "finish_reason": choice.finish_reason,   # "length" means the answer was cut off
        "sources": [{"id": h["id"], "start_line": h["start_line"], "end_line": h["end_line"],
                     "score": h["score"]} for h in hits],
    }
