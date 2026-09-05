from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from tools import WebSearch, web_scrape
import os
from dotenv import load_dotenv
load_dotenv()

# ---------------------------------------------------------------------------
# LLM backend — configurable, not hardcoded.
#
# Default is Ollama: fully local, no API key, no cost, but CPU-only
# inference is genuinely slow without a dedicated GPU. Setting
# LLM_PROVIDER=gemini in .env switches to Gemini's free tier instead —
# meaningfully faster since it's not running on your machine's CPU, and
# free (verify current limits at https://ai.google.dev before relying on
# this for a demo, since free-tier terms do change).
#
# This is a deliberate, named tradeoff, not a permanent choice: local =
# private/offline/free but slow on CPU-only hardware; cloud = fast but
# needs an API key and a network connection. Worth stating this explicitly
# if it comes up in an interview — it shows you made the tradeoff on
# purpose rather than not noticing it.
# ---------------------------------------------------------------------------
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

if LLM_PROVIDER == "gemini":
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )
else:
    llm = ChatOllama(
    model="llama3.2:3b",   
    temperature=0
)

# ---------------------------------------------------------------------------
# Search and Reader are no longer wrapped in create_agent(). Both steps
# always do the same tool-use, unconditionally, every run — there's no real
# decision for the LLM to make ("should I search / should I scrape?" was
# never actually in question). create_agent's ReAct loop was spending a full
# LLM inference pass just to decide to do the thing we were always going to
# do anyway, then another pass to restate the tool's result in its own
# words. Calling the tools directly removes both of those passes.
#
# Bonus: the reader step now scrapes the actual URLs returned by search and
# extracts from full page content, instead of re-processing the 200-char
# truncated snippet WebSearch returns. Under the old agent-based version
# there was no guarantee the reader agent ever actually called web_scrape at
# all — it could just re-summarize the summary it was given. This version
# always scrapes, deterministically, so the extraction is grounded in real
# page content rather than a snippet.
# ---------------------------------------------------------------------------
import re as _re


def run_search(query: str) -> str:
    return WebSearch.func(f"recent reliable information on: {query}")


def _extract_urls(search_result: str, limit: int = 3) -> list[str]:
    urls = _re.findall(r"URL:\s*(\S+)", search_result)
    return urls[:limit]


reader_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You extract the most relevant information from research source
material for the topic given. Focus on: key findings, important
models/methods, challenges, and future directions. Be concise and factual —
do not add commentary or claims not present in the source material."""
    ),
    (
        "user",
        """Topic: {query}

Source material:
{content}

Extract the most relevant information for a research summary on this topic."""
    )
])
reader_chain = reader_prompt | llm | StrOutputParser()


def run_reader(query: str, search_result: str) -> str:
    urls = _extract_urls(search_result)
    scraped_pages = []

    for url in urls:
        try:
            scraped_pages.append(web_scrape.func(url))
        except Exception as e:
            print(f"[run_reader] failed to scrape {url}: {e}")

    # Fall back to the search snippets themselves if scraping every URL
    # failed (e.g. no network, all URLs blocked) — better than an empty
    # extraction step.
    content = "\n\n---\n\n".join(scraped_pages) if scraped_pages else search_result[:1500]

    return reader_chain.invoke({"query": query, "content": content[:4000]})


# ---------------------------------------------------------------------------
# Writer Chain
# ---------------------------------------------------------------------------
writer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are an expert AI research assistant and technical writer.

Your task is to create a well-structured, accurate, and insightful research summary using the provided source material.

Guidelines:
- Write in a professional and academic tone.
- Focus on factual correctness and clarity.
- Summarize the key ideas, methodologies, findings, and trends.
- Highlight important technical concepts when relevant.
- Avoid hallucinations or unsupported claims.
- Do not invent citations or references.
- If multiple sources are provided, synthesize information across them coherently.
- Preserve important numerical results, model names, datasets, and benchmarks.
- Explain complex concepts clearly and concisely.
- Organize the output logically using sections and bullet points when useful.
- If the input includes "Previous critic feedback to address", you MUST directly
  address every point raised before anything else. This is a revision, not a
  fresh draft — do not repeat the same weaknesses.

Your response should contain:
1. Overview of the topic
2. Key findings or developments
3. Important models/methods discussed
4. Challenges or limitations
5. Future directions or trends
6. Final concise conclusion

If the provided context is insufficient, explicitly mention the missing information instead of fabricating details.
"""
    ),
    (
        "user",
        """
Research Topic:
{query}

Collected Research Content:
{text}

Write a comprehensive research summary.
"""
    )
])

writer_chain = writer_prompt | llm | StrOutputParser()


# ---------------------------------------------------------------------------
# Critic Chain — now returns structured output instead of free text, so the
# graph has something reliable to route on (approve vs. revise), and so the
# score/verdict/feedback are separate fields instead of buried in prose.
# ---------------------------------------------------------------------------
class CriticVerdict(BaseModel):
    quality_score: int = Field(
        description="Overall quality score from 1 (poor) to 10 (excellent)."
    )
    verdict: Literal["approve", "revise"] = Field(
        description="'approve' if quality_score >= 7 and there are no major "
                    "factual/hallucination concerns, otherwise 'revise'."
    )
    feedback: str = Field(
        description="Specific, actionable feedback the writer should address "
                    "on the next draft. Be concrete: name what's missing or wrong, "
                    "not just that something is wrong."
    )

    @field_validator("quality_score")
    @classmethod
    def normalize_score(cls, v: int) -> int:
        """
        Local models don't reliably respect a described numeric range in a
        prompt (Field(description=...) is documentation for the LLM, not an
        enforced constraint) — in practice this model sometimes scores on a
        0-100 scale despite being told 1-10. Rescale rather than reject, so
        one formatting slip doesn't throw away a real evaluation.
        """
        if v > 10:
            v = round(v / 10) if v <= 100 else 10
        return max(1, min(10, v))


critic_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are an expert research reviewer and critical evaluator.

Your task is to carefully review the generated research summary and identify weaknesses, inaccuracies, missing information, logical issues, and areas for improvement.

Evaluation Guidelines:
- Check factual consistency.
- Detect hallucinated or unsupported claims.
- Verify whether the summary accurately reflects the provided research content.
- Identify missing important concepts, methods, datasets, or findings.
- Evaluate clarity, structure, coherence, and technical depth.
- Check whether conclusions are justified.
- Ensure the writing is concise, professional, and academically appropriate.
- Detect repetition or redundant information.
- Evaluate whether important future directions or limitations were omitted.

Be highly analytical and constructive. Score honestly — do not default to a
high score just to avoid conflict, and do not default to a low score just to
force a revision. The score determines whether this report ships.
"""
    ),
    (
        "user",
        """
Research Topic:
{query}

Original Research Content:
{text}

Generated Summary:
{summary}

Critically evaluate the generated summary.
"""
    )
])

critic_structured_llm = llm.with_structured_output(CriticVerdict)
critic_chain = critic_prompt | critic_structured_llm