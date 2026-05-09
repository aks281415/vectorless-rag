"""
Vectorless RAG POC — Service Layer
PageIndex + DeepSeek + RAG orchestration
"""

import json
import logging
import os
import copy
from typing import Optional
from dotenv import load_dotenv
from pageindex import PageIndexClient
import openai

load_dotenv()

logger = logging.getLogger("vectorless.backend.services")

# ──────────────────────────────────────────────
# Tree Utilities (ported from pageindex.utils)
# ──────────────────────────────────────────────

def remove_fields(node: dict | list, fields: list[str]) -> dict | list:
    """Recursively remove specified fields from tree nodes."""
    if isinstance(node, list):
        return [remove_fields(item, fields) for item in node]
    if not isinstance(node, dict):
        return node

    cleaned = {k: v for k, v in node.items() if k not in fields}
    if "nodes" in cleaned:
        cleaned["nodes"] = [remove_fields(child, fields) for child in cleaned["nodes"]]
    return cleaned


def create_node_mapping(node: dict | list, mapping: Optional[dict] = None) -> dict:
    """Flatten tree into {node_id: node} dict for O(1) lookup."""
    if mapping is None:
        mapping = {}
    if isinstance(node, list):
        for item in node:
            create_node_mapping(item, mapping)
        return mapping
    if not isinstance(node, dict):
        return mapping

    mapping[node["node_id"]] = node
    for child in node.get("nodes", []):
        create_node_mapping(child, mapping)
    return mapping


# ──────────────────────────────────────────────
# PageIndex Service
# ──────────────────────────────────────────────

class PageIndexService:
    """Wraps the PageIndex SDK for document processing."""

    def __init__(self):
        api_key = os.getenv("PAGEINDEX_API_KEY")
        if not api_key:
            raise ValueError("PAGEINDEX_API_KEY not set in environment")
        logger.info("Initializing PageIndexClient")
        self.client = PageIndexClient(api_key=api_key)

    def submit_document(self, file_path: str) -> dict:
        """Submit a PDF for tree generation. Returns the full PageIndex submission response."""
        logger.info("Submitting document to PageIndex: %s", file_path)
        return self.client.submit_document(file_path)

    def check_status(self, doc_id: str) -> str:
        """Check if document processing is complete. Returns status string."""
        logger.debug("Checking PageIndex status for doc_id=%s", doc_id)
        if self.client.is_retrieval_ready(doc_id):
            return "completed"
        return "processing"

    def get_tree(self, doc_id: str) -> dict:
        """Fetch the generated tree structure with summaries and text."""
        logger.info("Fetching tree from PageIndex for doc_id=%s", doc_id)
        return self.client.get_tree(doc_id, node_summary=True)["result"]


# ──────────────────────────────────────────────
# LLM Service (DeepSeek via OpenAI-compatible SDK)
# ──────────────────────────────────────────────

class LLMService:
    """Calls DeepSeek using the OpenAI-compatible API."""

    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not set in environment")

        logger.info("Initializing LLMService with model %s", model)
        self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def call(self, prompt: str, temperature: float = 0) -> str:
        """Send a prompt to DeepSeek, return the response text."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()

    async def call_stream(self, prompt: str, temperature: float = 0):
        """Stream response from DeepSeek, yields text chunks."""
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content


# ──────────────────────────────────────────────
# RAG Service (Tree Search + Answer Generation)
# ──────────────────────────────────────────────

TREE_SEARCH_PROMPT = """
You are given a question and a tree structure of a document.
Each node contains a node id, node title, and a corresponding summary.
Your task is to find all nodes that are likely to contain the answer to the question.

Question: {query}

Document tree structure:
{tree_json}

Please reply in the following JSON format:
{{
    "thinking": "<Your thinking process on which nodes are relevant to the question>",
    "node_list": ["node_id_1", "node_id_2", ..., "node_id_n"]
}}
Directly return the final JSON structure. Do not output anything else.
"""

ANSWER_PROMPT = """
Answer the question based on the context:

Question: {query}
Context: {context}

Provide a clear, concise answer based only on the context provided.
If the context doesn't contain enough information to fully answer the question, say so.
"""


class RAGService:
    """Orchestrates the full vectorless RAG pipeline."""

    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    async def tree_search(self, tree: dict, query: str) -> dict:
        """
        Step 1: LLM reasons over tree structure to find relevant nodes.
        Returns {thinking, node_list}.
        """
        logger.info("Starting tree search for query=%s", query)
        # Strip text to create lightweight search structure
        tree_skeleton = remove_fields(copy.deepcopy(tree), fields=["text"])
        tree_json = json.dumps(tree_skeleton, indent=2)

        prompt = TREE_SEARCH_PROMPT.format(query=query, tree_json=tree_json)
        result = await self.llm.call(prompt)

        # Parse JSON response (handle potential markdown code blocks)
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]  # remove first line
            cleaned = cleaned.rsplit("```", 1)[0]  # remove last ```

        return json.loads(cleaned)

    async def generate_answer(self, tree: dict, query: str) -> dict:
        """
        Full RAG pipeline:
        1. Tree search → find relevant nodes
        2. Extract context from nodes
        3. Generate answer from context
        Returns {answer, reasoning, sources[]}.
        """
        # Step 1: Tree search
        search_result = await self.tree_search(tree, query)
        node_list = search_result.get("node_list", [])
        reasoning = search_result.get("thinking", "")

        # Step 2: Extract context
        node_map = create_node_mapping(tree)
        sources = []
        context_parts = []

        for node_id in node_list:
            if node_id in node_map:
                node = node_map[node_id]
                text = node.get("text", "")
                context_parts.append(text)
                sources.append({
                    "node_id": node_id,
                    "title": node.get("title", ""),
                    "page_index": node.get("page_index"),
                    "text_preview": text[:300] + "..." if len(text) > 300 else text,
                })

        context = "\n\n".join(context_parts)

        # Step 3: Generate answer
        if not context:
            return {
                "answer": "I couldn't find relevant information in the document to answer this question.",
                "reasoning": reasoning,
                "sources": [],
            }

        prompt = ANSWER_PROMPT.format(query=query, context=context)
        answer = await self.llm.call(prompt)

        return {
            "answer": answer,
            "reasoning": reasoning,
            "sources": sources,
        }
