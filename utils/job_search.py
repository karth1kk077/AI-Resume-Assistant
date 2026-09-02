"""Job search engine that aggregates open postings from ToS-compliant sources.

Queries RemoteOK, Adzuna, Greenhouse job boards, and Lever postings, then
normalizes the results into a single list of dicts and de-duplicates them.
Deliberately avoids scraping sites like LinkedIn/Indeed which violate their
Terms of Service and rely on unreliable auth walls / anti-bot measures.
"""

import os
import logging
from typing import List, Dict, Optional
import requests

logger = logging.getLogger(__name__)


class JobSearchEngine:
    """
    Searches for open job postings using public, ToS-compliant sources:
      - RemoteOK  (https://remoteok.com/api)          -> no key required
      - Adzuna    (https://developer.adzuna.com/)      -> free API key required
      - Greenhouse job boards (public per-company API) -> no key, needs board token(s)
      - Lever job boards (public per-company API)       -> no key, needs company slug(s)

    We deliberately avoid scraping sites like LinkedIn/Indeed directly, since doing so
    violates their Terms of Service and is unreliable (auth walls, anti-bot measures).
    """

    REMOTEOK_URL = "https://remoteok.com/api"
    ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"

    def __init__(self):
        self.adzuna_app_id = os.getenv("ADZUNA_APP_ID")
        self.adzuna_app_key = os.getenv("ADZUNA_APP_KEY")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "AI-Resume-Assistant/1.0"})

    # ---------- Public entrypoint ----------

    def search(
        self,
        keywords: str,
        location: str = "",
        max_results: int = 25,
        sources: Optional[List[str]] = None,
        greenhouse_boards: Optional[List[str]] = None,
        lever_companies: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Returns a normalized list of job postings:
        {source, title, company, location, description, url, posted_at}
        """
        sources = sources or ["remoteok", "adzuna", "greenhouse", "lever"]
        results: List[Dict] = []

        if "remoteok" in sources:
            try:
                results.extend(self._search_remoteok(keywords))
            except Exception as e:
                logger.warning(f"RemoteOK search failed: {e}")

        if "adzuna" in sources and self.adzuna_app_id and self.adzuna_app_key:
            try:
                results.extend(self._search_adzuna(keywords, location))
            except Exception as e:
                logger.warning(f"Adzuna search failed: {e}")

        if "greenhouse" in sources and greenhouse_boards:
            for board in greenhouse_boards:
                try:
                    results.extend(self._search_greenhouse(board, keywords))
                except Exception as e:
                    logger.warning(f"Greenhouse search failed for {board}: {e}")

        if "lever" in sources and lever_companies:
            for company in lever_companies:
                try:
                    results.extend(self._search_lever(company, keywords))
                except Exception as e:
                    logger.warning(f"Lever search failed for {company}: {e}")

        # De-duplicate by URL and cap results
        seen = set()
        deduped = []
        for job in results:
            if job["url"] not in seen:
                seen.add(job["url"])
                deduped.append(job)

        return deduped[:max_results]

    # ---------- Individual sources ----------

    def _search_remoteok(self, keywords: str) -> List[Dict]:
        resp = self.session.get(self.REMOTEOK_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        keyword_terms = [k.strip().lower() for k in keywords.split() if k.strip()]
        jobs = []
        for entry in data:
            if not isinstance(entry, dict) or "position" not in entry:
                continue  # first element is often a metadata blob, not a job

            searchable = f"{entry.get('position', '')} {entry.get('description', '')} {' '.join(entry.get('tags', []))}".lower()
            if keyword_terms and not any(term in searchable for term in keyword_terms):
                continue

            jobs.append({
                "source": "remoteok",
                "title": entry.get("position", "Unknown role"),
                "company": entry.get("company", "Unknown company"),
                "location": entry.get("location", "Remote"),
                "description": entry.get("description", "") or entry.get("position", ""),
                "url": entry.get("url") or f"https://remoteok.com/remote-jobs/{entry.get('id', '')}",
                "posted_at": entry.get("date", ""),
            })
        return jobs

    def _search_adzuna(self, keywords: str, location: str, country: str = "us", results_per_page: int = 20) -> List[Dict]:
        url = self.ADZUNA_URL.format(country=country, page=1)
        params = {
            "app_id": self.adzuna_app_id,
            "app_key": self.adzuna_app_key,
            "what": keywords,
            "where": location,
            "results_per_page": results_per_page,
            "content-type": "application/json",
        }
        resp = self.session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        jobs = []
        for entry in data.get("results", []):
            jobs.append({
                "source": "adzuna",
                "title": entry.get("title", "Unknown role"),
                "company": (entry.get("company") or {}).get("display_name", "Unknown company"),
                "location": (entry.get("location") or {}).get("display_name", ""),
                "description": entry.get("description", ""),
                "url": entry.get("redirect_url", ""),
                "posted_at": entry.get("created", ""),
            })
        return jobs

    def _search_greenhouse(self, board_token: str, keywords: str) -> List[Dict]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
        resp = self.session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        keyword_terms = [k.strip().lower() for k in keywords.split() if k.strip()]
        jobs = []
        for entry in data.get("jobs", []):
            title = entry.get("title", "")
            content = entry.get("content", "") or ""
            searchable = f"{title} {content}".lower()
            if keyword_terms and not any(term in searchable for term in keyword_terms):
                continue

            jobs.append({
                "source": "greenhouse",
                "title": title,
                "company": board_token,
                "location": (entry.get("location") or {}).get("name", ""),
                "description": content,
                "url": entry.get("absolute_url", ""),
                "posted_at": entry.get("updated_at", ""),
                "apply_meta": {"board_token": board_token, "job_id": entry.get("id")},
            })
        return jobs

    def _search_lever(self, company: str, keywords: str) -> List[Dict]:
        url = f"https://api.lever.co/v0/postings/{company}?mode=json"
        resp = self.session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        keyword_terms = [k.strip().lower() for k in keywords.split() if k.strip()]
        jobs = []
        for entry in data:
            title = entry.get("text", "")
            description = entry.get("descriptionPlain", "") or entry.get("description", "") or ""
            searchable = f"{title} {description}".lower()
            if keyword_terms and not any(term in searchable for term in keyword_terms):
                continue

            jobs.append({
                "source": "lever",
                "title": title,
                "company": company,
                "location": (entry.get("categories") or {}).get("location", ""),
                "description": description,
                "url": entry.get("hostedUrl", ""),
                "posted_at": entry.get("createdAt", ""),
                "apply_meta": {"company": company, "posting_id": entry.get("id")},
            })
        return jobs
