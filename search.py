import os
import json
import pandas as pd
import requests
from config import SKYQ_BASE_URL, SKYQ_HEADERS, EXCEL_FILE


def search_with_rag(search_query):
    """Search using RAG with uploaded files"""
    if not os.path.exists(EXCEL_FILE):
        return []
    
    try:
        df = pd.read_excel(EXCEL_FILE)
        df = df.fillna('')
        
        file_references = []
        for idx, row in df.iterrows():
            file_id = row.get('RAG_File_ID', '')
            if file_id and file_id != '':
                file_references.append({'type': 'file', 'id': file_id})
        
        if not file_references:
            print("⚠️  No RAG files available, using AI search")
            return search_with_ai(search_query)
        
        print(f"🔍 RAG search with {len(file_references)} resume files")
        
        payload = {
            "model": "llama3:8b",
            "messages": [
                {
                    "role": "user",
                    "content": f"""Based on the resume documents, find candidates matching: "{search_query}"
Return ONLY a JSON array:
[
  {{"candidate_name": "John Doe", "score": 95, "reason": "Strong SAP FICO experience"}},
  {{"candidate_name": "Jane Smith", "score": 85, "reason": "Relevant Oracle modules"}}
]
Sort by score descending. Return ONLY the JSON array."""
                }
            ],
            "files": file_references[:20],
            "stream": False,
            "temperature": 0.1
        }
        
        response = requests.post(
            f"{SKYQ_BASE_URL}/api/chat/completions",
            headers=SKYQ_HEADERS,
            json=payload,
            timeout=90
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            if '<think>' in content and '</think>' in content:
                start = content.find('</think>') + 8
                content = content[start:].strip()
            
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
                candidate_name = match.get('candidate_name', '')
                
                for idx, row in df.iterrows():
                    if candidate_name.lower() in str(row.get('Name', '')).lower():
                        resume_data = row.to_dict()
                        
                        for key, value in resume_data.items():
                            if pd.isna(value):
                                resume_data[key] = ''
                        
                        resume_data['relevance_score'] = match.get('score', 80)
                        resume_data['match_reason'] = match.get('reason', 'RAG matched')
                        results.append(resume_data)
                        break
            
            if results:
                print(f"✅ RAG search found {len(results)} matches")
                return results
        
        print("⚠️  RAG search failed, using AI search fallback")
        return search_with_ai(search_query)
        
    except Exception as e:
        print(f"RAG search error: {e}")
        return search_with_ai(search_query)


def search_with_ai(search_query):
    """Search using AI when RAG is not available"""
    if not os.path.exists(EXCEL_FILE):
        return []
    
    try:
        df = pd.read_excel(EXCEL_FILE)
        df = df.fillna('')
        
        candidates_summary = []
        for idx, row in df.iterrows():
            summary = f"{idx+1}. {row.get('Name', 'Unknown')} | {row.get('Current_Role', 'N/A')} | "
            summary += f"ERP: {row.get('ERP_Systems', 'N/A')} | Modules: {row.get('ERP_Modules', 'N/A')} | "
            summary += f"Skills: {str(row.get('Technical_Skills', ''))[:80]} | {row.get('Total_Years_Experience', 'N/A')} yrs"
            candidates_summary.append(summary)
        
        prompt = f"""Search query: "{search_query}"
Find matching candidates from this list. Return ONLY a JSON array with NO thinking tags:
[
  {{"candidate_number": 1, "score": 95, "reason": "Strong SAP FICO match"}},
  {{"candidate_number": 3, "score": 80, "reason": "Relevant modules"}}
]
Candidates:
{chr(10).join(candidates_summary[:15])}
IMPORTANT: Return ONLY the JSON array, no <think> tags, no explanations."""
        
        payload = {
            "model": "llama3:8b",
            "messages": [
                {"role": "system", "content": "Return only valid JSON. No thinking process, no explanations."},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "temperature": 0.1
        }
        
        response = requests.post(
            f"{SKYQ_BASE_URL}/api/chat/completions",
            headers=SKYQ_HEADERS,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            if '<think>' in content and '</think>' in content:
                start = content.find('</think>') + 8
                content = content[start:].strip()
            
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
                idx = match['candidate_number'] - 1
                if 0 <= idx < len(df):
                    resume_data = df.iloc[idx].to_dict()
                    
                    for key, value in resume_data.items():
                        if pd.isna(value):
                            resume_data[key] = ''
                    
                    resume_data['relevance_score'] = match.get('score', 75)
                    resume_data['match_reason'] = match.get('reason', 'AI matched')
                    results.append(resume_data)
            
            print(f"✅ AI search found {len(results)} matches")
            return results
        
    except json.JSONDecodeError as e:
        print(f"AI search JSON error: {e}")
    except Exception as e:
        print(f"AI search error: {e}")
    
    return fallback_excel_search(search_query)


def fallback_excel_search(search_query):
    """Simple keyword search in Excel"""
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