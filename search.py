import os
import json
import pandas as pd
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL, EXCEL_FILE

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel(
    model_name=GEMINI_MODEL,
    generation_config={
        "temperature": 0.1,
        "max_output_tokens": 2000,
    }
)


def search_with_rag(search_query):
    if not os.path.exists(EXCEL_FILE):
        return []
    
    try:
        df = pd.read_excel(EXCEL_FILE)
        df = df.fillna('')
        
        candidates_summary = []
        for idx, row in df.iterrows():
            summary = f"{idx+1}. {row.get('Name', 'Unknown')} | {row.get('Current_Role', 'N/A')} | "
            summary += f"ERP: {row.get('ERP_Systems', 'N/A')} | Modules: {row.get('ERP_Modules', 'N/A')} | "
            summary += f"Skills: {str(row.get('Technical_Skills', ''))[:100]} | {row.get('Total_Years_Experience', 'N/A')} yrs"
            candidates_summary.append(summary)
        
        if not candidates_summary:
            return []
        
        prompt = f"""Search query: "{search_query}"
Find matching candidates from this list. Return ONLY a JSON array:
[
  {{"candidate_number": 1, "score": 95, "reason": "Strong SAP FICO match"}},
  {{"candidate_number": 3, "score": 80, "reason": "Relevant modules"}}
]
Candidates:
{chr(10).join(candidates_summary[:30])}
IMPORTANT: Return ONLY the JSON array, no explanations."""

        print(f"🔍 AI search with {len(candidates_summary)} candidates")
        
        response = gemini_model.generate_content(prompt)
        
        if response.text:
            content = response.text.strip()
            
            if content.startswith('```json'):
                content = content[7:]
            elif content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            
            content = content.strip()
            matches = json.loads(content)
            
            results = []
            for match in matches:
                idx = match.get('candidate_number', 0) - 1
                if 0 <= idx < len(df):
                    resume_data = df.iloc[idx].to_dict()
                    
                    for key, value in resume_data.items():
                        if pd.isna(value):
                            resume_data[key] = ''
                    
                    resume_data['relevance_score'] = match.get('score', 80)
                    resume_data['match_reason'] = match.get('reason', 'AI matched')
                    results.append(resume_data)
            
            if results:
                print(f"✅ AI search found {len(results)} matches")
                return results
        
        return fallback_excel_search(search_query)
        
    except Exception as e:
        print(f"AI search error: {e}")
        return fallback_excel_search(search_query)


def search_with_ai(search_query):
    return search_with_rag(search_query)


def fallback_excel_search(search_query):
    if not os.path.exists(EXCEL_FILE):
        return []
    
    try:
        df = pd.read_excel(EXCEL_FILE)
        df = df.fillna('')
        
        search_lower = search_query.lower()
        
        matched_candidates = []
        for idx, row in df.iterrows():
            searchable_text = ' '.join([
                str(row.get('Name', '')),
                str(row.get('Current_Role', '')),
                str(row.get('ERP_Systems', '')),
                str(row.get('ERP_Modules', '')),
                str(row.get('Technical_Skills', '')),
                str(row.get('Location', ''))
            ]).lower()
            
            if search_lower in searchable_text:
                candidate_data = row.to_dict()
                
                for key, value in candidate_data.items():
                    if pd.isna(value):
                        candidate_data[key] = ''
                
                candidate_data['relevance_score'] = 70
                candidate_data['match_reason'] = f"Keyword match: {search_query}"
                matched_candidates.append(candidate_data)
        
        print(f"Keyword search found {len(matched_candidates)} matches")
        return matched_candidates
    except Exception as e:
        print(f"Fallback search error: {e}")
        return []