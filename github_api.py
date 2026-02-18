"""
SoClose Community Bot — GitHub API Integration
Fetches and caches public repositories from the SoCloseSociety organization.
"""

import logging
import asyncio

import requests

import config
import database

logger = logging.getLogger(__name__)

# Category mapping based on repo name prefixes/keywords
_CATEGORIES = {
    "BOT-": "bot",
    "BOT_": "bot",
    "Booster": "bot",
    "Scrapp": "scraper",
    "Scraper": "scraper",
    "Bulk": "automation",
    "Sender": "automation",
    "Pinterest": "automation",
    "Script_": "template",
    "Template": "template",
}


def classify_project(name: str) -> str:
    """Classify a project into a category based on its name."""
    for prefix, category in _CATEGORIES.items():
        if prefix.lower() in name.lower():
            return category
    return "tool"


def friendly_name(repo_name: str) -> str:
    """Convert repo name to a human-friendly display name."""
    name = repo_name.replace("BOT-", "").replace("BOT_", "").replace("_", " ").replace("-", " ")
    return name.strip()


def fetch_repos() -> list[dict]:
    """Fetch all public repos from the GitHub organization."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"token {config.GITHUB_TOKEN}"

    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/orgs/{config.GITHUB_ORG}/repos"
        params = {"per_page": 100, "page": page, "type": "public", "sort": "updated"}
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"GitHub API error: {e}")
            break

        data = resp.json()
        if not isinstance(data, list) or not data:
            break

        for repo in data:
            repos.append({
                "name": repo["name"],
                "friendly_name": friendly_name(repo["name"]),
                "description": repo.get("description") or "No description",
                "url": repo["html_url"],
                "language": (repo.get("language") or "N/A"),
                "stars": repo.get("stargazers_count", 0),
                "category": classify_project(repo["name"]),
                "updated_at": repo.get("updated_at", ""),
            })
        page += 1

    logger.info(f"Fetched {len(repos)} repos from GitHub")
    return repos


async def sync_projects() -> list[dict]:
    """Fetch repos from GitHub and sync to database."""
    repos = await asyncio.to_thread(fetch_repos)
    for repo in repos:
        await database.upsert_project(
            name=repo["name"],
            description=repo["description"],
            url=repo["url"],
            language=repo["language"],
            stars=repo["stars"],
            category=repo["category"],
            updated_at=repo["updated_at"],
        )
    logger.info(f"Synced {len(repos)} projects to database")
    return repos


def fetch_repo_readme(repo_name: str) -> str | None:
    """Fetch the README content for a specific repo."""
    headers = {"Accept": "application/vnd.github.v3.raw"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"token {config.GITHUB_TOKEN}"

    url = f"https://api.github.com/repos/{config.GITHUB_ORG}/{repo_name}/readme"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.text[:3000]
    except requests.RequestException as e:
        logger.error(f"Failed to fetch README for {repo_name}: {e}")
    return None


def format_project_list(projects: list[dict]) -> str:
    """Format a list of projects for WhatsApp display."""
    if not projects:
        return "Aucun projet trouve."

    lines = []
    for i, p in enumerate(projects, 1):
        emoji = {"bot": "🤖", "scraper": "🔍", "automation": "⚡", "template": "📄", "tool": "🔧"}.get(
            p.get("category", "tool"), "📦"
        )
        stars = f" ⭐{p['stars']}" if p.get("stars") else ""
        lines.append(f"{i}. {emoji} *{friendly_name(p['name'])}*{stars}")
        if p.get("description") and p["description"] != "No description":
            desc = p["description"][:80]
            lines.append(f"   {desc}")

    return "\n".join(lines)


def format_project_detail(project: dict) -> str:
    """Format a single project for WhatsApp detail view."""
    emoji = {"bot": "🤖", "scraper": "🔍", "automation": "⚡", "template": "📄", "tool": "🔧"}.get(
        project.get("category", "tool"), "📦"
    )
    return (
        f"{emoji} *{friendly_name(project['name'])}*\n\n"
        f"{project.get('description', 'No description')}\n\n"
        f"⭐ Stars: {project.get('stars', 0)}\n"
        f"💻 Langage: {project.get('language', 'N/A')}\n"
        f"📂 Categorie: {project.get('category', 'tool')}\n"
        f"🔗 GitHub: {project.get('url', '')}\n\n"
        f"Tape *menu* pour revenir au menu."
    )
