import json

from groq import Groq

from app.core.config import get_settings


class GroqService:
    def __init__(self):
        settings = get_settings()
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = "llama-3.1-8b-instant"

    def format_issue(self, raw_title: str, raw_description: str) -> dict:
        # print(f"services/llm_service.py Formatting issue with title: {raw_title}")
        prompt = f"""
You are an expert QA engineer. Analyze the following raw bug report and format it into a professional, structured JSON object.
Raw Title: {raw_title}
Raw Description: {raw_description}

Requirements:
1. 'title': A concise, descriptive title.
2. 'description': A structured markdown description with sections for 'Steps to Reproduce', 'Expected Behavior', and 'Actual Behavior'. If the raw text lacks details, infer reasonably or put N/A.
3. 'priority': Choose one from ["Low", "Medium", "High", "Critical"] based on the severity.

Output ONLY valid JSON in the exact format: {{"title": "...", "description": "...", "priority": "..."}}
"""
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        try:
            # print(f"services/llm_service.py Formatted issue: {response.choices[0].message.content}")
            return json.loads(response.choices[0].message.content)
        except Exception:
            # print("services/llm_service.py Failed to format issue, returning defaults")
            return {"title": raw_title, "description": raw_description, "priority": "Medium"}



    def summarize_timeline(self, recent_issues: list[dict]) -> dict:
        # print(f"services/llm_service.py Summarizing timeline for {len(recent_issues)} recent issues")
        if not recent_issues:
            # print("services/llm_service.py No recent issues to summarize, returning default summary")
            return {"summary": "No recent activity."}
            
        issues_text = "\n".join([f"- [{i['priority']}] {i['title']} ({i['status']})" for i in recent_issues])
        prompt = f"""
You are an engineering manager reviewing recent issue tracker activity.
Write a 1-2 sentence TL;DR plain English summary of the system's current health based on these recent issues. Focus on critical bugs if there are any.

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
            # print(f"services/llm_service.py Timeline summary: {response.choices[0].message.content}")
            return json.loads(response.choices[0].message.content)
        except Exception:
            # print("services/llm_service.py Failed to summarize timeline, returning default summary")
            return {"summary": "Unable to generate summary at this time."}
