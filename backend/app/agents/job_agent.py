import logging
from typing import Any, Dict, List, Optional

from app.models import ResumeProfile
from app.services.job_matcher import match_jobs

logger = logging.getLogger("careerpilot.agents.job")


class JobAgent:
    """Agent responsible for matching, filtering, ranking, and explaining job recommendations."""

    def recommend(
        self,
        profile: ResumeProfile,
        keywords: str = "",
        location: str = "",
        remote_only: bool = False,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """Search and rank matching jobs for a candidate profile with criteria."""
        results = match_jobs(
            profile=profile,
            limit=limit,
            keywords=keywords,
            location=location,
            remote_only=remote_only,
        )
        return results

    def format_recommendations_markdown(
        self,
        jobs: List[Dict[str, Any]],
        total_matched: int,
        filter_summary: str = "",
    ) -> str:
        """Format matching jobs into natural, professional chat markdown."""
        if not jobs:
            return (
                "I searched our 1,800-job database but couldn't find active listings "
                f"matching your criteria{f' ({filter_summary})' if filter_summary else ''}. "
                "Try broadening your search (e.g., removing specific location or skill filters)!"
            )

        header = "### Recommended Job Matches"
        if filter_summary:
            header += f" ({filter_summary})"

        lines = [
            header,
            f"Found **{total_matched} matching roles** in our database. Here are the top {len(jobs)} matches for your profile:\n",
        ]

        for idx, job in enumerate(jobs, start=1):
            title = job.get("title", "Untitled Role")
            company = job.get("company", "Company")
            location = job.get("location", "Location unspecified")
            exp = job.get("experience_required", "Not specified")
            score = job.get("match_score", 0)
            reasons = job.get("match_reasons", [])
            source_url = job.get("source_url", "")
            skills = job.get("skills", [])

            lines.append(f"#### {idx}. {title} @ **{company}**")
            lines.append(f"- **Location:** {location}")
            lines.append(f"- **Experience:** {exp}")
            lines.append(f"- **Match Score:** `{score}/100`")
            if skills:
                lines.append(f"- **Key Skills:** {', '.join(skills[:6])}")
            if reasons:
                reasons_str = "; ".join(reasons[:3])
                lines.append(f"- **Why it matches:** {reasons_str}")
            if source_url:
                lines.append(f"- [View Original Posting ↗]({source_url})")
            lines.append("")

        lines.append(
            "> **Tip:** You can ask me to *'Apply to job 1'*, *'Show only remote roles'*, "
            "or *'Show jobs needing React'*."
        )
        return "\n".join(lines)

