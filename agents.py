from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools import WebSearch, web_scrape
import os 
from dotenv import load_dotenv
load_dotenv()

llm = ChatOllama(
    model="mistral:latest",
    temperature=0
)

# 1st Agent: Search Agent
def build_search_agent():
    return create_agent(
        model = llm,
        tools = [WebSearch])
    
    
# 2nd Agent: Scraping Agent
def build_reader_agent():
    return create_agent(
        model = llm,
        tools = [web_scrape]
    )
    


# Writer Chain
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

# critic_chain
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

Provide:
1. Overall quality assessment
2. Strengths
3. Weaknesses
4. Missing information
5. Suggested improvements
6. Hallucination or factual risk warnings (if any)
7. Final verdict

Be highly analytical and constructive.
Do not rewrite the entire summary unless necessary.
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

critic_chain = critic_prompt | llm | StrOutputParser()
