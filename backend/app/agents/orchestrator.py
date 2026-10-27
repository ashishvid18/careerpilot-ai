import logging
import re
from typing import Any, Dict, List, Optional

from app.agents.application_agent import ApplicationAgent
from app.agents.job_agent import JobAgent
from app.agents.resume_agent import ResumeAgent
from app.models import ChatRequest, ChatResponse, ResumeProfile
from app.services.gemini_service import reply_to_message

logger = logging.getLogger("careerpilot.agents.orchestrator")


class OrchestratorAgent:
    """
    Central Orchestrator Agent that routes conversational queries to specialized sub-agents:
    - ResumeAgent: parsing and profile extraction
    - JobAgent: matching, ranking, filtering with reasons
    - ApplicationAgent: applying, duplicate checking, and status tracking
    """

    def __init__(self):
        self.resume_agent = ResumeAgent()
        self.job_agent = JobAgent()
        self.application_agent = ApplicationAgent()

    def handle_message(self, request: ChatRequest) -> ChatResponse:
        message = request.message.strip()
        lower = message.lower()
        profile = request.resume_profile
        current_jobs = request.current_jobs or []
        session_id = request.session_id or "local-session"

        # -------------------------------------------------------------
        # 1. Intent: Check Application Status
        # -------------------------------------------------------------
        status_triggers = [
            "show my applied jobs",
            "applied jobs",
            "my applications",
            "show applications",
            "application status",
            "what jobs have i applied to",
            "what have i applied for",
            "view applications",
            "status of applications",
        ]
        if any(trigger in lower for trigger in status_triggers) or (
            "applied" in lower and any(w in lower for w in ["show", "list", "check", "my", "status", "view"])
        ):
            logger.info("Orchestrator routing to ApplicationAgent (status inquiry)")
            reply = self.application_agent.format_status_markdown(session_id)
            apps = self.application_agent.list_applications_enriched(session_id)
            return ChatResponse(
                reply=reply,
                intent="application_status",
                applications=apps,
                suggested_actions=[
                    "Recommend matching jobs",
                    "Show remote roles",
                    "Jobs needing React",
                ],
            )

        # -------------------------------------------------------------
        # 2. Intent: Apply to a Job
        # -------------------------------------------------------------
        apply_triggers = ["apply", "submit application", "apply for"]
        is_apply_intent = any(trigger in lower for trigger in apply_triggers) or (
            re.search(r"\bapply\s+to\b", lower) is not None
        )

        if is_apply_intent:
            logger.info("Orchestrator routing to ApplicationAgent (apply)")
            target_job, err = self.application_agent.resolve_job(message, current_jobs)
            if target_job:
                result = self.application_agent.apply(session_id, target_job)
                actions = ["Show my applied jobs", "Show remote roles"]
                if len(current_jobs) > 1:
                    actions.insert(0, "Apply to next job")
                return ChatResponse(
                    reply=result["message"],
                    intent="apply_job",
                    jobs=[target_job],
                    suggested_actions=actions,
                )
            else:
                return ChatResponse(
                    reply=err or "Please specify which job you'd like to apply to (e.g. *'Apply to job 1'*).",
                    intent="apply_job_error",
                    suggested_actions=["Show matching jobs", "Show my applied jobs"],
                )

        # -------------------------------------------------------------
        # 3. Intent: Filter / Refine or Recommend Jobs
        # -------------------------------------------------------------
        job_words = ["job", "jobs", "role", "roles", "position", "positions", "opening", "openings", "opportunity", "opportunities"]
        matching_words = ["match", "matching", "recommend", "recommendation", "recommendations", "find", "show", "search", "filter", "fit", "remote", "wfh"]

        has_job_term = any(w in lower for w in job_words)
        has_match_term = any(w in lower for w in matching_words)

        # Refinement signals like 'remote only', 'jobs with python', etc.
        is_job_intent = has_job_term or has_match_term or ("remote" in lower)

        if is_job_intent and (profile is not None or "find" in lower or "show" in lower or "search" in lower):
            logger.info("Orchestrator routing to JobAgent (match and filter)")

            # Extract criteria
            remote_only = any(term in lower for term in ["remote", "work from home", "wfh", "work-from-home"])

            keywords = ""
            if "react" in lower:
                keywords = "React"
            elif "python" in lower:
                keywords = "Python"
            elif "data" in lower and ("scientist" in lower or "analyst" in lower or "science" in lower):
                keywords = "Data"
            elif "ml" in lower or "machine learning" in lower or "ai" in lower:
                keywords = "AI"
            elif "frontend" in lower or "front end" in lower:
                keywords = "Frontend"
            elif "backend" in lower or "back end" in lower:
                keywords = "Backend"
            elif "full stack" in lower or "fullstack" in lower:
                keywords = "Full Stack"
            else:
                # Check for explicit 'jobs needing X' or 'roles with X'
                explicit_match = re.search(
                    r"(?:jobs?|roles?)\s+(?:for|needing|requiring|with|in)\s+([a-zA-Z0-9+#. -]+)",
                    lower,
                )
                if explicit_match:
                    candidate_kw = explicit_match.group(1).strip()
                    stop_keywords = {
                        "my profile", "my resume", "me", "myself", "my skills",
                        "my experience", "profile", "resume", "remote", "india",
                        "my background", "my target role", "freshers",
                    }
                    if candidate_kw.lower() not in stop_keywords:
                        keywords = candidate_kw

            location = ""
            for loc in ["bengaluru", "bangalore", "mumbai", "pune", "hyderabad", "chennai", "delhi", "noida", "gurgaon"]:
                if loc in lower:
                    location = "Bengaluru" if loc == "bangalore" else loc.capitalize()
                    break

            # Build dummy profile if user hasn't uploaded a resume yet but asked for jobs
            effective_profile = profile or ResumeProfile(
                designation="Software Engineer",
                skills=["Python", "JavaScript", "React"],
                experience="1-2 years",
            )

            results = self.job_agent.recommend(
                profile=effective_profile,
                keywords=keywords,
                location=location,
                remote_only=remote_only,
                limit=5,
            )

            filter_parts = []
            if remote_only:
                filter_parts.append("Remote")
            if keywords:
                filter_parts.append(f"Skill: {keywords}")
            if location:
                filter_parts.append(f"Location: {location}")
            filter_summary = ", ".join(filter_parts)

            matching_jobs = results.get("results", [])
            total_matched = results.get("total", len(matching_jobs))

            reply = self.job_agent.format_recommendations_markdown(
                jobs=matching_jobs,
                total_matched=total_matched,
                filter_summary=filter_summary,
            )

            actions = []
            if matching_jobs:
                actions.append("Apply to Job 1")
                if len(matching_jobs) > 1:
                    actions.append("Apply to Job 2")
            if not remote_only:
                actions.append("Show only remote roles")
            if "React" not in keywords:
                actions.append("Jobs needing React")
            actions.append("Show my applied jobs")

            return ChatResponse(
                reply=reply,
                intent="recommend_jobs" if not filter_summary else "refine_jobs",
                jobs=matching_jobs,
                suggested_actions=actions[:4],
            )

        # -------------------------------------------------------------
        # 4. Intent: General Conversation / Advice
        # -------------------------------------------------------------
        logger.info("Orchestrator routing to Conversational LLM service")
        conversational_reply = reply_to_message(message=message, resume_profile=profile)

        default_actions = [
            "Show matching jobs",
            "Show remote roles",
            "Show my applied jobs",
        ]
        return ChatResponse(
            reply=conversational_reply,
            intent="general",
            suggested_actions=default_actions,
        )

