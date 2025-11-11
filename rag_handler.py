import os
import requests
from config import SKYQ_BASE_URL, SKYQ_JWT_TOKEN, SKYQ_HEADERS, LOCAL_DOCS_DIR
from utils import safe_join


def upload_resume_to_docs(resume_text, filename, parsed_data):
    """Upload resume to Open WebUI for RAG capabilities"""
    try:
        doc_content = f"""CANDIDATE: {parsed_data.get('name', 'Unknown')}
EMAIL: {parsed_data.get('email', 'N/A')}
PHONE: {parsed_data.get('phone', 'N/A')}
LOCATION: {parsed_data.get('location', 'N/A')}
CURRENT ROLE: {parsed_data.get('current_role', 'N/A')}
CURRENT COMPANY: {parsed_data.get('current_company', 'N/A')}
EXPERIENCE: {parsed_data.get('total_years_experience', 'N/A')} years
ERP SYSTEMS: {safe_join(parsed_data.get('erp_systems', []))}
ERP MODULES: {safe_join(parsed_data.get('erp_modules', []))}
TECHNICAL SKILLS: {safe_join(parsed_data.get('technical_skills', []))}
CERTIFICATIONS: {safe_join(parsed_data.get('certifications', []))}
SUMMARY:
{parsed_data.get('summary', '')}
FULL RESUME TEXT:
{resume_text[:3000]}
"""
        
        os.makedirs(LOCAL_DOCS_DIR, exist_ok=True)
        local_filename = f"resume_{filename.replace('.pdf', '').replace('.docx', '')}.txt"
        local_path = os.path.join(LOCAL_DOCS_DIR, local_filename)
        
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(doc_content)
        
        print(f"✅ Document saved locally: {local_path}")
        
        try:
            with open(local_path, 'rb') as f:
                files = {'file': (local_filename, f, 'text/plain')}
                headers = {
                    'Authorization': f"Bearer {SKYQ_JWT_TOKEN}",
                    'Accept': 'application/json'
                }
                
                response = requests.post(
                    f"{SKYQ_BASE_URL}/api/v1/files/",
                    headers=headers,
                    files=files,
                    timeout=30
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    file_id = result.get('id') or result.get('file_id')
                    print(f"✅ Uploaded to Open WebUI RAG: file_id={file_id}")
                    
                    parsed_data['_rag_file_id'] = file_id
                    return True
                else:
                    print(f"⚠️  Upload returned {response.status_code}: {response.text[:200]}")
                    
        except Exception as upload_error:
            print(f"⚠️  RAG upload failed: {upload_error}")
            print(f"💡 Tip: File saved locally in {local_path}")
        
        return True
        
    except Exception as e:
        print(f"Warning: Could not save document: {e}")
        return False