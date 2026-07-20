"""The deep-research agent: searches the web, scrapes promising pages, and saves good ones
as new sources in the notebook. Standalone and stateless — invoked once per web-search request,
not part of the chat agent's conversation.
"""

from __future__ import annotations

import os

from firecrawl import Firecrawl
from firecrawl.v2.types import ScrapeOptions
from langchain.agents import create_agent
from langchain_core.tools import tool

from core.store import Source, SourceStore, store

MODEL = os.getenv("NOTEBOOKLM_CHAT_MODEL", "google_genai:gemini-flash-latest")

SYSTEM_PROMPT = """You are a research assistant that finds high-quality web sources on a topic \
and adds them to a notebook, so they can later be searched and cited in chat.

You have three tools: web_search, web_scrape, and web_crawl.

For most topics, follow this process:
1. Call web_search with 2-4 different phrasings of the topic, to cover it from different \
angles (e.g. a direct phrasing, a more specific sub-question, a related term).
2. From the combined results, pick the URLs that look most relevant, authoritative, and \
information-dense. Prefer official docs, reputable publications, and primary sources over thin \
or promotional pages. Skip obvious duplicates.
3. Call web_scrape on each picked URL to read its actual content, and judge whether it's \
genuinely substantive and relevant to the topic.
4. Call save_source for each page that passes your judgment, so it gets indexed into the \
notebook.

If a single page clearly won't cover the topic and a site has a whole section dedicated to it \
(e.g. a documentation site), call web_crawl on that section's URL instead of scraping pages one \
by one — it follows internal links and saves every substantive page it finds automatically.

Be selective — a few well-chosen sources are better than saving everything you find. When done, \
reply with a short plain-text summary of which sources you saved and why.
"""


def _make_tools(store: SourceStore, firecrawl: Firecrawl, saved: list[Source]):
    scraped: dict[str, tuple[str, str]] = {}

    @tool
    def web_search(query: str, limit: int = 5) -> str:
        """Search the web for a query. Returns candidate results (title, url, short description) —
        not full content. Call this with several different phrasings to cover a topic from
        different angles, then use web_scrape on the URLs that look most relevant."""
        try:
            data = firecrawl.search(query, limit=limit)
        except Exception as exc:  # noqa: BLE001 - surface any API error to the agent
            return f"Search failed: {exc}"
        results = data.web or []
        if not results:
            return "No results found for this query."
        return "\n".join(f"- {r.title!r} — {r.url}\n  {r.description or ''}" for r in results)

    @tool
    def web_scrape(url: str) -> str:
        """Fetch and read the full content of a URL found via web_search. Returns a preview of the
        content so you can judge its quality and relevance; call save_source(url) afterwards to
        keep it as a source if it's good."""
        try:
            doc = firecrawl.scrape(url, formats=["markdown"])
        except Exception as exc:  # noqa: BLE001
            return f"Could not scrape {url}: {exc}"
        content = (doc.markdown or "").strip()
        if not content:
            return f"No readable content extracted from {url}."
        title = (doc.metadata.title if doc.metadata else None) or url
        scraped[url] = (title, content)
        preview = content[:800]
        return f"Title: {title}\n\n{preview}{'...' if len(content) > 800 else ''}"

    @tool
    def save_source(url: str, name: str | None = None) -> str:
        """Save a URL previously read with web_scrape as a new source in the notebook. Only call
        this for pages you judged relevant and high-quality."""
        if url not in scraped:
            return f"Call web_scrape on {url} first, then save_source once you've judged it."
        title, content = scraped[url]
        source = store.add(name=name or title, content=f"Source URL: {url}\n\n{content}")
        saved.append(source)
        return f"Saved {source.name!r} (id={source.id}) as a new source."

    @tool
    def web_crawl(url: str, limit: int = 10) -> str:
        """Crawl a website starting from a URL, following its internal links to gather multiple
        pages (e.g. a whole docs section) in one call. Use this instead of web_search/web_scrape
        when a single page won't cover the topic. Saves every substantive page it finds as a
        source directly — no separate save_source call needed."""
        try:
            job = firecrawl.crawl(url, limit=limit, scrape_options=ScrapeOptions(formats=["markdown"]))
        except Exception as exc:  # noqa: BLE001
            return f"Could not crawl {url}: {exc}"
        added = []
        for doc in job.data or []:
            content = (doc.markdown or "").strip()
            if not content:
                continue
            page_title = (doc.metadata.title if doc.metadata else None) or url
            page_url = (doc.metadata.url if doc.metadata else None) or url
            source = store.add(name=page_title, content=f"Source URL: {page_url}\n\n{content}")
            saved.append(source)
            added.append(source.name)
        if not added:
            return f"Crawled {url} but found no readable content."
        return f"Crawled and saved {len(added)} page(s): {', '.join(added)}"

    return [web_search, web_scrape, save_source, web_crawl]


def research(topic: str) -> list[Source]:
    """Run the deep-research agent for a topic; returns the sources it added to the notebook."""
    firecrawl = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])
    saved: list[Source] = []

    agent = create_agent(
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
        tools=_make_tools(store, firecrawl, saved),
    )
    agent.invoke(
        {"messages": [{"role": "user", "content": f"Research this topic: {topic}"}]}
    )
    return saved
