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

    def _heuristic_extract(self, raw_title: str, raw_description: str) -> dict:
        """Extract structured fields from raw text using regex/heuristics."""
        import re

        text = (raw_description or "").strip()
        result = {
            "title": raw_title.strip() if raw_title else "Reported Defect",
            "description": text,
            "steps_to_reproduce": None,
            "expected_behavior": None,
            "actual_behavior": None,
            "environment": None,
            "browser": None,
            "priority": "Medium",
            "severity": "Major",
        }

        if not text:
            return result

        # 1. Steps to reproduce
        steps_match = re.search(
            r'(?:steps(?:\s+to\s+reproduce)?|how\s+to\s+reproduce|repro\s+steps?)[\s:]*\n([\s\S]*?)(?=(?:\n\s*(?:environment|browser|expected|actual|tested\s+on|notes|os)[\s:]|\Z))',
            text,
            re.IGNORECASE
        )
        if steps_match:
            steps_text = steps_match.group(1).strip()
            if steps_text:
                result["steps_to_reproduce"] = steps_text
        elif re.search(r'(?:^|\s|\n)1[\.\)]\s+', text):
            numbered = re.findall(r'(?:^|\s|\n)(\d+[\.\)]\s+[^\n\r]+?)(?=(?:\s+\d+[\.\)]|\n|\Z))', text)
            if len(numbered) >= 2:
                result["steps_to_reproduce"] = "\n".join(s.strip() for s in numbered)


        # 2. Environment
        env_match = re.search(
            r'(?:environment|operating\s+system)[\s:]*\n?([^\n\r]+)',
            text,
            re.IGNORECASE
        )
        if env_match:
            val = env_match.group(1).strip().rstrip('.')
            if val and not any(k in val.lower() for k in ["browser", "steps", "expected", "actual"]):
                result["environment"] = val
        else:
            env_keywords = []
            env_tier = re.search(r'\b(development|staging|qa|production|dev|uat|prod)\s*(?:environment|env)?\b', text, re.IGNORECASE)
            if env_tier:
                env_keywords.append(env_tier.group(0).strip())
            os_match = re.search(r'\b(windows\s*(?:10|11|server)?|macOS(?:\s*\w+)?|ubuntu(?:\s*[\d\.]+)?|linux|ios(?:\s*\d+)?|android(?:\s*\d+)?)\b', text, re.IGNORECASE)
            if os_match:
                env_keywords.append(os_match.group(0).strip())
            if env_keywords:
                result["environment"] = ", ".join(dict.fromkeys(env_keywords))

        # 3. Browser
        browser_match = re.search(
            r'(?:browser|browser\s+details|tested\s+on)[\s:]*\n?([^\n\r]+)',
            text,
            re.IGNORECASE
        )
        if browser_match:
            val = browser_match.group(1).strip().rstrip('.')
            if val and not any(k in val.lower() for k in ["environment", "steps", "expected", "actual"]):
                result["browser"] = val
        else:
            browser_find = re.search(r'\b(google\s+chrome|chrome(?:\s+[\d\.]+)?|mozilla\s+firefox|firefox(?:\s+[\d\.]+)?|microsoft\s+edge|edge(?:\s+[\d\.]+)?|safari(?:\s+[\d\.]+)?|opera)\b', text, re.IGNORECASE)
            if browser_find:
                result["browser"] = browser_find.group(0).strip()

        # 4. Expected Behavior
        expected_match = re.search(
            r'(?:expected(?:\s+behavior|\s+result)?)[\s:]*\n?([^\n\r]+(?:\n[^\n\r]+)*?)(?=(?:\n\s*(?:actual|steps|environment|browser)[\s:]|\Z))',
            text,
            re.IGNORECASE
        )
        if expected_match:
            result["expected_behavior"] = expected_match.group(1).strip()

        # 5. Actual Behavior
        actual_match = re.search(
            r'(?:actual(?:\s+behavior|\s+result)?)[\s:]*\n?([^\n\r]+(?:\n[^\n\r]+)*?)(?=(?:\n\s*(?:expected|steps|environment|browser)[\s:]|\Z))',
            text,
            re.IGNORECASE
        )
        if actual_match:
            result["actual_behavior"] = actual_match.group(1).strip()

        summary_clean = re.split(r'\n\s*(?:steps|environment|browser|expected|actual)[\s:]', text, flags=re.IGNORECASE)[0].strip()
        if summary_clean and len(summary_clean) >= 10:
            result["description"] = summary_clean

        return result

    def format_issue(self, raw_title: str, raw_description: str) -> dict:
        fallback = self._heuristic_extract(raw_title, raw_description)
        if not self.client:
            print("services/llm_service.py format_issue: Groq client not available, returning heuristic extraction.")
            return fallback

        print(f"services/llm_service.py Formatting issue with title: {raw_title}")
        prompt = f"""
You are an expert QA engineer and defect triage specialist. Analyze the following raw defect report and extract structured, professional defect fields into a valid JSON object. Do not include markdown code blocks.
Raw Title: {raw_title}
Raw Description: {raw_description}

Extraction Guidelines:
1. 'title': A concise, descriptive title summarizing the defect.
2. 'description': A clear summary of the core defect without repeating separate headers.
3. 'steps_to_reproduce': Sequential numbered reproduction steps (e.g. "1. Open login page\n2. Enter credentials\n3. Click Submit"). Extract from explicit headings or action sentences. If NO steps are mentioned, return null. (DO NOT invent steps, do NOT output "N/A").
4. 'expected_behavior': What should happen according to expected requirements (or null if not mentioned).
5. 'actual_behavior': What actually happened / error observed (or null if not mentioned).
6. 'environment': The environment, operating system, or deployment tier (e.g. "Development", "QA", "Production", "Windows 11", "Ubuntu 22.04", "macOS Sonoma"). Extract from explicit headings ("Environment:", "OS:") or natural language context ("tested in QA on Windows 11"). If no environment is mentioned, return null. (DO NOT hallucinate an environment).
7. 'browser': The browser and version (e.g. "Google Chrome", "Chrome 120", "Firefox", "Edge", "Safari"). Extract from explicit headings ("Browser:") or natural language context ("using Chrome"). If no browser is mentioned, return null. (DO NOT hallucinate a browser).
8. 'priority': Choose one from ["Low", "Medium", "High", "Critical"] based on business urgency.
9. 'severity': Choose one from ["Minor", "Major", "Critical"] based on technical impact.

Output ONLY valid JSON in the exact format: {{"title": "...", "description": "...", "steps_to_reproduce": "...", "expected_behavior": "...", "actual_behavior": "...", "environment": "...", "browser": "...", "priority": "...", "severity": "..."}}
"""
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            # Merge with heuristic fallback if LLM omitted non-hallucinated fields
            if not data.get("steps_to_reproduce") or data.get("steps_to_reproduce") == "N/A":
                if fallback.get("steps_to_reproduce"):
                    data["steps_to_reproduce"] = fallback["steps_to_reproduce"]
                else:
                    data["steps_to_reproduce"] = None
            if not data.get("environment") or data.get("environment") == "N/A":
                data["environment"] = fallback.get("environment")
            if not data.get("browser") or data.get("browser") == "N/A":
                data["browser"] = fallback.get("browser")
            if not data.get("expected_behavior") or data.get("expected_behavior") == "N/A":
                data["expected_behavior"] = fallback.get("expected_behavior")
            if not data.get("actual_behavior") or data.get("actual_behavior") == "N/A":
                data["actual_behavior"] = fallback.get("actual_behavior")
            return data
        except Exception as e:
            print(f"services/llm_service.py format_issue LLM call failed: {e}; returning heuristic fallback.")
            return fallback


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

    def _parse_json(self, content: str) -> dict:
        """Robustly parse JSON output from LLM, stripping markdown fences or extracting outer object."""
        if not content:
            raise ValueError("Empty response from AI model")
        text = content.strip()
        import re
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            text = match.group(1)
        return json.loads(text)

    def generate_test_cases(self, defect: dict) -> dict:
        """
        Generate structured, multi-perspective QA test cases for a defect with robust fallback.
        """
        if not self.client:
            return {
                "summary": {
                    "total_count": 0,
                    "by_type": {},
                    "overview": "AI service is currently unavailable. Please check API key configuration."
                },
                "test_cases": []
            }

        title = defect.get("title", "Unknown")
        description = defect.get("description", "No description provided")
        steps = defect.get("reproduction_steps", "N/A")
        expected = defect.get("expected_behavior", "N/A")
        actual = defect.get("actual_behavior", "N/A")
        severity = defect.get("severity_name", "Unknown")
        priority = defect.get("priority_name", "Unknown")
        module = defect.get("module_name", "General")
        category = defect.get("category_name", "General")
        root_cause = defect.get("root_cause") or defect.get("ai_root_cause") or "Not determined yet"

        system_msg = "You are an expert Lead Software QA Engineer. You must return ONLY a valid JSON object matching the requested schema. Do not output markdown fences, code blocks, or extra text."
        user_prompt = f"""Analyze the following software defect and generate comprehensive, structured test cases for QA engineers.

DEFECT DETAILS:
Title: {title}
Description: {description}
Module / Component: {module}
Category: {category}
Severity: {severity}
Priority: {priority}
Steps to Reproduce: {steps}
Expected Behavior: {expected}
Actual Behavior: {actual}
Identified Root Cause: {root_cause}

INSTRUCTIONS:
1. Generate between 8 to 14 high-quality, realistic test cases directly relevant to this specific defect and its affected components.
2. Cover multiple QA perspectives:
   - Positive / Functional test cases (valid scenarios and primary paths)
   - Negative / Validation test cases (invalid inputs, missing mandatory fields, boundary errors)
   - Boundary & Edge test cases (min/max limits, empty values, special characters)
   - Regression test cases (verifying that related existing functionality remains unbroken)
   - Concurrency / Security / Error Handling test cases (if relevant to the defect)
3. Do NOT generate generic filler test cases. Every test must be directly tailored to this defect.
4. Provide structured, step-by-step instructions with clear preconditions, sample test data, and precise expected results.

Output ONLY valid JSON in this EXACT structure:
{{
  "summary": {{
    "total_count": 10,
    "by_type": {{
      "Positive / Functional": 3,
      "Negative / Validation": 3,
      "Boundary / Edge": 2,
      "Regression": 2
    }},
    "overview": "Summary of the test coverage strategy..."
  }},
  "test_cases": [
    {{
      "test_case_id": "TC-001",
      "scenario": "Short description of scenario",
      "test_type": "Positive / Functional",
      "priority": "High",
      "preconditions": "Prerequisites needed before test",
      "steps": ["Step 1...", "Step 2...", "Step 3..."],
      "test_data": "Input values used (or N/A)",
      "expected_result": "Expected system behavior"
    }}
  ]
}}"""

        # Attempt 1: with json_object response format
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            return self._parse_json(response.choices[0].message.content)
        except Exception as e1:
            print(f"generate_test_cases attempt 1 failed: {e1}. Retrying without format constraint...")
            try:
                # Attempt 2: retry directly without strict response_format flag
                response = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_prompt}
                    ],
                    model=self.model,
                    temperature=0.2
                )
                return self._parse_json(response.choices[0].message.content)
            except Exception as e2:
                print(f"generate_test_cases attempt 2 failed: {e2}")
                return {
                    "summary": {
                        "total_count": 0,
                        "by_type": {},
                        "overview": "Failed to generate test cases. Please try again."
                    },
                    "test_cases": []
                }

    def detect_missing_scenarios(self, defect: dict, existing_test_cases: list[dict] | None = None) -> dict:
        """
        Analyze defect and test cases to identify overlooked edge cases and test coverage gaps with robust fallback.
        """
        if not self.client:
            return {
                "already_covered_summary": ["Basic defect reproduction"],
                "missing_scenarios": [],
                "disclaimer": "These recommendations are AI-identified coverage gaps to assist QA testing and do not guarantee complete test coverage."
            }

        title = defect.get("title", "Unknown")
        description = defect.get("description", "No description provided")
        steps = defect.get("reproduction_steps", "N/A")
        expected = defect.get("expected_behavior", "N/A")
        actual = defect.get("actual_behavior", "N/A")
        root_cause = defect.get("root_cause") or defect.get("ai_root_cause") or "Not determined yet"

        existing_tests_text = "No prior test cases provided."
        if existing_test_cases and len(existing_test_cases) > 0:
            parts = []
            for tc in existing_test_cases[:15]:
                parts.append(f"- [{tc.get('test_case_id', 'TC')}] ({tc.get('test_type', 'Test')}) {tc.get('scenario', '')}")
            existing_tests_text = "\n".join(parts)

        system_msg = "You are an expert QA Architect specializing in exploratory testing and edge-case discovery. You must return ONLY a valid JSON object matching the requested schema. Do not output markdown fences or conversational text."
        user_prompt = f"""Analyze the defect and any existing test scenarios to identify overlooked edge cases, missing validation paths, boundary conditions, concurrency risks, and coverage gaps.

DEFECT DETAILS:
Title: {title}
Description: {description}
Steps to Reproduce: {steps}
Expected Behavior: {expected}
Actual Behavior: {actual}
Root Cause: {root_cause}

EXISTING / PLANNED TEST CASES:
{existing_tests_text}

INSTRUCTIONS:
1. Identify 4 to 8 potentially missing or overlooked test scenarios that QA should validate for this defect.
2. Focus on subtle edge cases such as:
   - Session/token expiration during action
   - Network drop, latency, or timeout during processing
   - Double submission or rapid repeated clicks
   - Boundary limits, special characters, unicode, XSS attempts
   - Role/permission constraints
   - Concurrency or race conditions
   - Database/cache inconsistency or recovery
3. Summarize what is already covered vs. what is potentially missing.
4. For each missing scenario, explain why it matters, assess its risk (High, Medium, Low), and provide a concrete suggested validation test.
5. NEVER claim that these are all possible test cases. Clearly communicate them as AI recommendations.

Output ONLY valid JSON in this EXACT structure:
{{
  "already_covered_summary": [
    "Primary happy path defect reproduction",
    "Standard form submission"
  ],
  "missing_scenarios": [
    {{
      "scenario": "Session expiration during submission",
      "why_it_matters": "User may lose entered data or receive an unhandled error instead of a graceful re-login prompt.",
      "risk": "High",
      "suggested_test": "Expire auth token right before clicking submit and verify graceful re-auth handling without data loss.",
      "priority": "High"
    }}
  ],
  "disclaimer": "These recommendations are AI-identified coverage gaps to assist QA testing and do not guarantee complete test coverage."
}}"""

        # Attempt 1: with json_object format
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            return self._parse_json(response.choices[0].message.content)
        except Exception as e1:
            print(f"detect_missing_scenarios attempt 1 failed: {e1}. Retrying without format constraint...")
            try:
                # Attempt 2: retry directly without strict response_format flag
                response = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_prompt}
                    ],
                    model=self.model,
                    temperature=0.2
                )
                return self._parse_json(response.choices[0].message.content)
            except Exception as e2:
                print(f"detect_missing_scenarios attempt 2 failed: {e2}")
                return {
                    "already_covered_summary": ["Basic defect reproduction"],
                    "missing_scenarios": [],
                    "disclaimer": "These recommendations are AI-identified coverage gaps to assist QA testing and do not guarantee complete test coverage."
                }

# Create a singleton instance for use throughout the application
llm_service = GroqService()
