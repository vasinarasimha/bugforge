import json
from groq import Groq
from app.core.config import get_settings

class GroqService:
    def __init__(self, model_name: str = "openai/gpt-oss-20b"):
        settings = get_settings()
        self.model = model_name
        self.client = None
        try:
            if settings.groq_api_key:
                self.client = Groq(api_key=settings.groq_api_key)
            else:
                print("services/llm_service.py Groq API key not set; AI features disabled.")
        except Exception as e:
            print(f"services/llm_service.py Groq client init failed: {e}; AI features disabled.")
            self.client = None

    def format_issue(self, raw_title: str, raw_description: str) -> dict:
        if not self.client:
            print("services/llm_service.py format_issue: Groq client not available, returning fallback.")
            return {"title": raw_title, "description": raw_description, "priority": "Medium"}
        print(f"services/llm_service.py Formatting issue with title: {raw_title}")
        prompt = f"""
You are an expert QA engineer. Analyze the following raw defect report and format it into a professional, structured JSON object. Do not include markdown code blocks.
Raw Title: {raw_title}
Raw Description: {raw_description}

Requirements:
1. 'title': A concise, descriptive title.
2. 'description': A brief overall summary of the issue.
3. 'steps_to_reproduce': A clear numbered list of steps to reproduce. If raw text lacks details, infer reasonably or put N/A.
4. 'expected_behavior': What should happen. If raw text lacks details, infer reasonably or put N/A.
5. 'actual_behavior': What actually happened. If raw text lacks details, infer reasonably or put N/A.
6. 'priority': Choose one from ["Low", "Medium", "High", "Critical"] based on the severity.
7. 'severity': Choose one from ["Minor", "Major", "Critical"] based on the impact.

Output ONLY valid JSON in the exact format: {{"title": "...", "description": "...", "steps_to_reproduce": "...", "expected_behavior": "...", "actual_behavior": "...", "priority": "...", "severity": "..."}}
"""
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        try:
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {"title": raw_title, "description": raw_description, "priority": "Medium"}

    def summarize_timeline(self, recent_issues: list[dict]) -> dict:
        if not self.client:
            return {"summary": "AI features disabled."}
        if not recent_issues:
            return {"summary": "No recent activity."}
        issues_text = "\n".join([f"- [{i['priority']}] {i['title']} ({i['status']})" for i in recent_issues])
        prompt = f"""
You are an engineering manager reviewing recent issue tracker activity.
Write a 1-2 sentence TL;DR plain English summary of the system's current health based on these recent issues. Focus on critical defects if there are any.

RECENT ISSUES:
{issues_text}

Output ONLY valid JSON in the exact format: {{"summary": "your short summary here"}}
"""
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        try:
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {"summary": "Unable to generate summary at this time."}

    def generate_resolution_assistance(self, issue: dict, similar_resolved: list[dict]) -> dict:
        if not self.client:
            return {
                "historical_resolutions": [],
                "investigation_areas": ["Review application logs", "Check recent code changes"],
                "possible_causes": ["Unexpected null or undefined value"],
                "suggested_resolution": "Review the relevant module for unhandled exceptions.",
                "similar_defects_summary": "AI features disabled."
            }
            
        similar_text = ""
        if similar_resolved:
            parts = []
            for i, s in enumerate(similar_resolved, 1):
                comments_text = "\n    - ".join(s.get("relevant_comments", []))
                parts.append(
                    f"[Similar Defect {i}] {s.get('defect_id', 'N/A')}: {s.get('title', '')}\n"
                    f"  Similarity: {s.get('similarity_score', 0)}\n"
                    f"  Description: {s.get('description', '')[:300]}\n"
                    f"  Root Cause: {s.get('root_cause', 'N/A')}\n"
                    f"  Resolution: {s.get('resolution', 'N/A')}\n"
                    f"  Comments:\n    - {comments_text if comments_text else 'None'}"
                )
            similar_text = "\n\n".join(parts)
        else:
            similar_text = "No similar resolved defects found in the database."

        prompt = f"""
You are a senior software engineer providing resolution assistance for a defect tracker.

CURRENT DEFECT:
Title: {issue.get('title', '')}
Description: {issue.get('description', '')[:500]}
Severity: {issue.get('severity_name', 'Unknown')}
Priority: {issue.get('priority_name', 'Unknown')}

SIMILAR HISTORICAL DEFECTS (from database):
{similar_text}

Based on the above, provide structured resolution assistance. Be specific and practical.
Use the similar historical defects as evidence to recommend a resolution if they share the same root cause.
DO NOT hallucinate historical defects. ONLY use the historical defects provided above. If none exist, output an empty array for historical_resolutions.

Output ONLY valid JSON in this EXACT format:
{{
  "historical_resolutions": [
    {{
      "defect_id": "...",
      "similarity_score": 0.89,
      "root_cause": "...",
      "resolution": "...",
      "relevant_comments": ["..."]
    }}
  ],
  "investigation_areas": ["...", "..."],
  "possible_causes": ["...", "..."],
  "suggested_resolution": "...",
  "similar_defects_summary": "..."
}}
"""
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        try:
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {
                "historical_resolutions": [],
                "investigation_areas": ["Review application logs", "Check recent code changes"],
                "possible_causes": ["Unexpected null or undefined value"],
                "suggested_resolution": "Review the relevant module for unhandled exceptions.",
                "similar_defects_summary": "No clear historical match found."
            }

    # Create a singleton instance for use throughout the application
llm_service = GroqService()
