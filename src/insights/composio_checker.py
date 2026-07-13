"""Composio Toolkit Checker.

Checks if an application already has an integration toolkit available
on Composio.
"""

import asyncio
import logging
import aiohttp
from src.config import settings

logger = logging.getLogger(__name__)


async def check_composio_toolkits(
    app_names: list[str],
) -> dict[str, bool]:
    """Check if Composio already supports these apps.
    
    Since a full crawl of composio.dev/tools might be blocked or 
    require rendering JS, we use a heuristic: checking if the docs page 
    for the app exists at docs.composio.dev.
    """
    results: dict[str, bool] = {}
    
    # Optional: we can hardcode known ones if needed to reduce network calls
    # but let's try the heuristic approach first.
    
    semaphore = asyncio.Semaphore(10)
    
    async def check_app(session: aiohttp.ClientSession, app_name: str) -> tuple[str, bool]:
        # Normalize name for URL: e.g. "Salesforce" -> "salesforce", "Zoho CRM" -> "zoho-crm"
        normalized = app_name.lower().replace(" ", "-").replace(".", "")
        url = f"https://docs.composio.dev/apps/{normalized}"
        
        async with semaphore:
            try:
                headers = {"User-Agent": settings.user_agent}
                async with session.head(url, headers=headers, allow_redirects=True, timeout=5) as response:
                    # 200 means the page exists
                    return app_name.lower(), response.status == 200
            except Exception as e:
                logger.debug(f"Failed to check composio docs for {app_name}: {e}")
                return app_name.lower(), False

    async with aiohttp.ClientSession() as session:
        tasks = [check_app(session, app) for app in app_names]
        results_list = await asyncio.gather(*tasks)
        
        for name, exists in results_list:
            results[name] = exists
            
    return results
