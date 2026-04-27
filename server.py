"""
USyd Library MCP Server
Allows Claude to search the University of Sydney Library catalogue.
"""

import os
import json
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("USyd Library")

PRIMO_BASE = "https://api-eu.hosted.exlibrisgroup.com/primo/v1/search"
VID = "61USYD_INST:sydney"
TAB = "Everything"
SCOPE = "MyInst_and_CI"
API_KEY = os.environ.get("PRIMO_API_KEY", "")


def format_result(doc: dict) -> dict:
    """Extract the most useful fields from a Primo result."""
    pnx = doc.get("pnx", {})
    display = pnx.get("display", {})
    links = doc.get("delivery", {}).get("link", [])

    title = display.get("title", ["Unknown title"])[0]
    creator = display.get("creator", display.get("contributor", ["Unknown author"]))
    creator = creator[0] if creator else "Unknown author"
    date = display.get("creationdate", ["Unknown date"])[0] if display.get("creationdate") else "Unknown date"
    resource_type = display.get("type", ["Unknown type"])[0] if display.get("type") else "Unknown type"
    description = display.get("description", [""])[0] if display.get("description") else ""
    publisher = display.get("publisher", [""])[0] if display.get("publisher") else ""
    source = display.get("source", [""])[0] if display.get("source") else ""

    # Get a direct link to the record
    record_id = doc.get("pnx", {}).get("control", {}).get("recordid", [""])[0]
    catalogue_link = f"https://sydney.primo.exlibrisgroup.com/permalink/61USYD_INST/1c0gpqp/{record_id}" if record_id else ""

    # Get full text / access link if available
    access_link = ""
    for link in links:
        if link.get("linkType") in ("http://purl.org/vocab/frbr/core#exemplar", "semopac"):
            access_link = link.get("linkURL", "")
            break

    return {
        "title": title,
        "author": creator,
        "year": date,
        "type": resource_type,
        "publisher": publisher,
        "source": source,
        "description": description[:300] + "..." if len(description) > 300 else description,
        "catalogue_link": catalogue_link,
        "access_link": access_link,
    }


@mcp.tool()
async def search_library(
    query: str,
    resource_type: str = "any",
    limit: int = 5,
) -> str:
    """
    Search the University of Sydney Library catalogue.

    Args:
        query: What to search for (e.g. 'climate change policy', 'Shakespeare sonnets')
        resource_type: Filter by type. Options: 'any', 'books', 'articles', 'journals', 'databases', 'images'
        limit: Number of results to return (1-10, default 5)
    """
    limit = max(1, min(10, limit))

    # Map friendly type names to Primo material types
    type_map = {
        "books": "books",
        "articles": "articles",
        "journals": "journals",
        "databases": "databases",
        "images": "images",
        "any": "",
    }
    material_type = type_map.get(resource_type.lower(), "")

    params = {
        "q": f"any,contains,{query}",
        "vid": VID,
        "tab": TAB,
        "scope": SCOPE,
        "limit": limit,
        "offset": 0,
        "lang": "en",
        "mode": "simple",
        "apikey": API_KEY,
    }
    if material_type:
        params["qInclude"] = f"facet_rtype,exact,{material_type}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(PRIMO_BASE, params=params)

        if response.status_code == 401:
            # Fall back to guest sandbox with direct URL scraping approach
            return await _fallback_search(query, resource_type, limit)

        if response.status_code != 200:
            return f"Search failed (HTTP {response.status_code}). Try searching directly at: https://sydney.primo.exlibrisgroup.com/discovery/search?vid=61USYD_INST:sydney&query=any,contains,{query.replace(' ', '%20')}"

        data = response.json()
        docs = data.get("docs", [])

        if not docs:
            return f"No results found for '{query}'. Try a broader search, or visit the catalogue directly: https://sydney.primo.exlibrisgroup.com/discovery/search?vid=61USYD_INST:sydney&query=any,contains,{query.replace(' ', '%20')}"

        total = data.get("info", {}).get("total", len(docs))
        results = [format_result(doc) for doc in docs]

        output = [f"Found {total:,} results for '{query}' in the USyd Library. Showing top {len(results)}:\n"]
        for i, r in enumerate(results, 1):
            output.append(f"**{i}. {r['title']}**")
            output.append(f"   Author: {r['author']}")
            output.append(f"   Year: {r['year']} | Type: {r['type']}")
            if r['publisher']:
                output.append(f"   Publisher: {r['publisher']}")
            if r['description']:
                output.append(f"   Summary: {r['description']}")
            if r['catalogue_link']:
                output.append(f"   Catalogue: {r['catalogue_link']}")
            if r['access_link']:
                output.append(f"   Access: {r['access_link']}")
            output.append("")

        return "\n".join(output)

    except httpx.TimeoutException:
        return "Search timed out. Please try again, or search directly at the USyd Library catalogue."
    except Exception as e:
        return f"An error occurred: {str(e)}"


async def _fallback_search(query: str, resource_type: str, limit: int) -> str:
    """
    Fallback: query the public Primo search endpoint directly
    (no API key required for basic catalogue searches).
    """
    # Use the public-facing search API which doesn't require an institutional key
    url = "https://sydney.primo.exlibrisgroup.com/primaws/rest/pub/pnxs"

    type_map = {
        "books": "books",
        "articles": "articles",
        "journals": "journals",
        "any": "",
    }
    material_type = type_map.get(resource_type.lower(), "")

    params = {
        "blendFacetsSeparately": "false",
        "disableCache": "false",
        "getMore": "0",
        "inst": "61USYD_INST",
        "lang": "en",
        "limit": limit,
        "mode": "simple",
        "newspapersActive": "false",
        "newspapersSearch": "false",
        "offset": "0",
        "pcAvailability": "false",
        "q": f"any,contains,{query}",
        "qExclude": "",
        "qInclude": f"facet_rtype,exact,{material_type}" if material_type else "",
        "rapido": "false",
        "refEntryActive": "false",
        "rtaLinks": "true",
        "scope": SCOPE,
        "skipDelivery": "Y",
        "tab": TAB,
        "vid": VID,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; USyd-Library-MCP/1.0)",
        "Accept": "application/json",
        "Referer": "https://sydney.primo.exlibrisgroup.com/",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, params=params, headers=headers)

    if response.status_code != 200:
        catalogue_url = f"https://sydney.primo.exlibrisgroup.com/discovery/search?vid=61USYD_INST:sydney&tab=Everything&search_scope=MyInst_and_CI&query=any,contains,{query.replace(' ', '%20')}"
        return f"Could not retrieve results automatically. Search directly at:\n{catalogue_url}"

    data = response.json()
    docs = data.get("docs", [])

    if not docs:
        return f"No results found for '{query}'."

    total = data.get("info", {}).get("total", len(docs))
    results = [format_result(doc) for doc in docs]

    output = [f"Found {total:,} results for '{query}' in the USyd Library. Showing top {len(results)}:\n"]
    for i, r in enumerate(results, 1):
        output.append(f"**{i}. {r['title']}**")
        output.append(f"   Author: {r['author']}")
        output.append(f"   Year: {r['year']} | Type: {r['type']}")
        if r['publisher']:
            output.append(f"   Publisher: {r['publisher']}")
        if r['description']:
            output.append(f"   Summary: {r['description']}")
        if r['catalogue_link']:
            output.append(f"   Catalogue: {r['catalogue_link']}")
        output.append("")

    return "\n".join(output)


@mcp.tool()
async def get_library_databases(subject: str = "") -> str:
    """
    Find USyd Library subject databases and research resources.

    Args:
        subject: Optional subject area to filter by (e.g. 'medicine', 'law', 'engineering')
    """
    base_url = "https://libguides.library.usyd.edu.au/az.php"
    if subject:
        url = f"{base_url}?subject={subject.replace(' ', '+')}"
    else:
        url = base_url

    return (
        f"USyd Library A-Z Databases: {url}\n\n"
        "This page lists all databases USyd subscribes to. "
        "You can filter by subject area to find the most relevant research databases for your field. "
        "Popular databases include:\n"
        "- **Web of Science** – multidisciplinary research\n"
        "- **Scopus** – science, technology, medicine\n"
        "- **PsycINFO** – psychology & behavioural sciences\n"
        "- **LexisNexis** – law\n"
        "- **Business Source Complete** – business & economics\n\n"
        f"Search the full list at: {url}"
    )


if __name__ == "__main__":
    import uvicorn
    from starlette.middleware.trustedhost import TrustedHostMiddleware
    port = int(os.environ.get("PORT", 8000))
    app = mcp.streamable_http_app()
    # Allow Railway's domain and any subdomain
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    uvicorn.run(app, host="0.0.0.0", port=port)
