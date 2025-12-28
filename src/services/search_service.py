import json
import google.generativeai as genai
from src.config import config
from src.repositories import resume_repository
from src.services.ai_service import ai_service
class SearchService:
    def __init__(self, repository=None):
        self.repository = repository or resume_repository
    def search(self, query):
        resumes = self.repository.get_all()
        if not resumes:
            return []
        try:
            summaries = []
            for idx, resume in enumerate(resumes):
                summary = f"{idx+1}. {resume.get('Name', 'Unknown')} | {resume.get('Current_Role', 'N/A')} | "
                summary += f"ERP: {resume.get('ERP_Systems', 'N/A')} | Modules: {resume.get('ERP_Modules', 'N/A')} | "
                summary += f"Skills: {str(resume.get('Technical_Skills', ''))[:100]} | {resume.get('Total_Years_Experience', 'N/A')} yrs"
                summaries.append(summary)
            prompt = f"""Search query: "{query}"
Find matching candidates from this list. Return ONLY a JSON array:
[
  {{"candidate_number": 1, "score": 95, "reason": "Strong match"}},
  {{"candidate_number": 3, "score": 80, "reason": "Relevant skills"}}
]
Candidates:
{chr(10).join(summaries[:30])}
IMPORTANT: Return ONLY the JSON array, no explanations."""
            print(f"🔍 AI search with {len(summaries)} candidates")
            response = ai_service.call_gemini(prompt)
            matches = self._parse_matches(response)
            results = []
            for match in matches:
                idx = match.get('candidate_number', 0) - 1
                if 0 <= idx < len(resumes):
                    resume_data = resumes[idx].copy()
                    resume_data['relevance_score'] = match.get('score', 80)
                    resume_data['match_reason'] = match.get('reason', 'AI matched')
                    results.append(resume_data)
            if results:
                print(f"✅ AI search found {len(results)} matches")
                return results
            return self._fallback_search(query)
        except Exception as e:
            print(f"AI search error: {e}")
            return self._fallback_search(query)
    def _parse_matches(self, response):
        content = response.strip()
        if content.startswith('```json'):
            content = content[7:]
        elif content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        return json.loads(content.strip())
    def _fallback_search(self, query):
        results = self.repository.search(query)
        for result in results:
            result['relevance_score'] = 70
            result['match_reason'] = f"Keyword match: {query}"
        print(f"Keyword search found {len(results)} matches")
        return results
search_service = SearchService()
