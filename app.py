from flask import Flask, render_template, request, jsonify, send_file
import requests
import PyPDF2
import docx
import json
import pandas as pd
import os
import time
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'doc'}

SKYQ_BASE_URL = "https://ai.skyq.tech"
SKYQ_JWT_TOKEN = "Enter_Your_SkyQ_JWT_Token_Here"
SKYQ_HEADERS = {
    "Authorization": f"Bearer {SKYQ_JWT_TOKEN}",
    "Content-Type": "application/json"
}

EXCEL_FILE = 'resumes_database.xlsx'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

def extract_text_from_docx(file_path):
    """Extract text from Word document"""
    try:
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting DOCX text: {e}")
        raise Exception(f"Failed to extract text from Word document: {str(e)}")

def enhance_parsed_data(parsed_data, resume_text):
    """Post-process and enhance parsed resume data"""
    import re
    
    if not parsed_data.get('email'):
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, resume_text)
        if emails:
            parsed_data['email'] = emails[0]
    
    if not parsed_data.get('phone'):
        phone_pattern = r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'
        phones = re.findall(phone_pattern, resume_text)
        if phones:
            parsed_data['phone'] = phones[0].strip()
    
    erp_mappings = {
        'D365': 'Microsoft Dynamics 365',
        'EBS': 'Oracle E-Business Suite',
        'JDE': 'JD Edwards',
        'PS': 'PeopleSoft',
        'Netsuite': 'NetSuite',
        'Ms Dynamics': 'Microsoft Dynamics'
    }
    
    normalized_erp = []
    for erp in parsed_data.get('erp_systems', []):
        normalized = erp_mappings.get(erp, erp)
        if normalized not in normalized_erp:
            normalized_erp.append(normalized)
    parsed_data['erp_systems'] = normalized_erp
    
    module_mappings = {
        'FICO': ['FI', 'CO', 'Financial Accounting', 'Controlling'],
        'SCM': ['MM', 'SD', 'Supply Chain Management'],
        'HCM': ['HR', 'Human Capital Management']
    }
    
    expanded_modules = set(parsed_data.get('erp_modules', []))
    for module in list(expanded_modules):
        if module in module_mappings:
            expanded_modules.update(module_mappings[module])
    parsed_data['erp_modules'] = list(expanded_modules)
    
    if not parsed_data.get('total_years_experience'):
        years_pattern = r'(\d+)[\+]?\s*(?:years?|yrs?)'
        years_matches = re.findall(years_pattern, resume_text.lower())
        if years_matches:
            parsed_data['total_years_experience'] = max(map(int, years_matches))
        elif parsed_data.get('experience'):
            total_years = 0
            for exp in parsed_data['experience']:
                duration = exp.get('duration', '')
                year_ranges = re.findall(r'(\d{4})', duration)
                if len(year_ranges) >= 2:
                    try:
                        years = int(year_ranges[-1]) - int(year_ranges[0])
                        total_years += max(0, years)
                    except:
                        pass
            if total_years > 0:
                parsed_data['total_years_experience'] = str(total_years)
    
    if not parsed_data.get('linkedin'):
        linkedin_pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+'
        linkedin = re.findall(linkedin_pattern, resume_text, re.IGNORECASE)
        if linkedin:
            parsed_data['linkedin'] = linkedin[0]
    
    if not parsed_data.get('technical_skills'):
        parsed_data['technical_skills'] = []
    
    if not parsed_data.get('certifications'):
        parsed_data['certifications'] = []
    
    return parsed_data

def score_resume_completeness(parsed_data):
    """Score how complete the parsed resume is (0-100)"""
    score = 0
    max_score = 100
    
    if parsed_data.get('name'): score += 5
    if parsed_data.get('email'): score += 5
    if parsed_data.get('phone'): score += 5
    if parsed_data.get('location'): score += 5
    if parsed_data.get('summary'): score += 5
    if parsed_data.get('total_years_experience'): score += 5
    
    if parsed_data.get('erp_systems'): score += 15
    if parsed_data.get('erp_modules'): score += 15
    
    if parsed_data.get('experience') and len(parsed_data['experience']) > 0: score += 10
    if parsed_data.get('current_role'): score += 5
    if parsed_data.get('current_company'): score += 5
    
    if parsed_data.get('education'): score += 5
    if parsed_data.get('technical_skills'): score += 5
    if parsed_data.get('certifications'): score += 5
    if parsed_data.get('projects'): score += 5
    
    return score


def parse_resume_with_skyq(resume_text, candidate_name="Unknown", retry_count=0):
    """Parse resume using SkyQ AI with automatic retry and model fallback"""
    
    max_lengths = [5000, 4000, 3000, 2500] 
    max_length = max_lengths[min(retry_count, len(max_lengths)-1)]
    truncated_text = resume_text[:max_length]
    
    prompt = f"""You are an expert resume parser specializing in ERP consultants. Extract ALL information accurately.

RESUME TEXT:
\"\"\"
{truncated_text}
\"\"\"

Extract this information and return ONLY valid JSON (no markdown, no explanations):

{{
  "name": "",  // Full name (look for "Name:", first line, or email prefix)
  "email": "",  // Email address (look for @ symbol)
  "phone": "",  // Phone/mobile number (with country code if present)
  "location": "",  // City, State, Country (look for "Location:", "Address:", current city)
  "linkedin": "",  // LinkedIn profile URL
  "summary": "",  // Professional summary/objective (2-3 sentences)
  "total_years_experience": "",  // Total years (e.g., "5", "8+", calculate from experience dates)
  "current_role": "",  // Current/most recent job title
  "current_company": "",  // Current/most recent company name
  "erp_systems": [],  // ALL ERP systems mentioned (SAP, Oracle EBS, Oracle Cloud, PeopleSoft, Microsoft Dynamics 365, D365, NetSuite, Infor, JD Edwards, Workday, Epicor, IFS, Sage, Odoo, etc.)
  "erp_modules": [],  // ALL modules (FI, CO, MM, SD, PP, PS, HR, HCM, FICO, SCM, CRM, WM, QM, PM, AM, BI, Analytics, Finance, Procurement, Manufacturing, etc.)
  "experience": [  // ALL work experience entries, most recent first
    {{
      "company": "",  // Company name
      "role": "",  // Job title
      "duration": "",  // e.g., "Jan 2020 - Present", "2018-2020", calculate total months/years
      "responsibilities": ""  // Key achievements and responsibilities (3-5 bullet points)
    }}
  ],
  "education": [  // ALL education entries
    {{
      "degree": "",  // Degree name (B.Tech, MBA, M.Sc, CA, etc.)
      "university": "",  // University/College name
      "year": ""  // Graduation year or duration
    }}
  ],
  "technical_skills": [],  // ALL technical skills (SQL, Python, ABAP, PL/SQL, Java, BODS, ODI, OBIEE, Power BI, Excel, etc.)
  "certifications": [],  // ALL certifications (SAP Certified, Oracle Certified, PMP, Prince2, etc.)
  "projects": []  // Major projects with client names if mentioned
}}

PARSING RULES:
1. Be thorough - extract ALL ERP systems and modules mentioned anywhere in the resume
2. For total_years_experience: Calculate from dates or look for "X+ years" phrases
3. For location: Extract city and country/state
4. For ERP systems: Include variations (e.g., "D365" = "Microsoft Dynamics 365", "EBS" = "Oracle E-Business Suite")
5. For modules: Look for abbreviations AND full names (e.g., both "FICO" and "Financial Accounting")
6. For skills: Include programming languages, tools, databases, and soft skills
7. If multiple companies listed, current_company = most recent one
8. Use empty string "" or empty array [] only if information is truly not present

Return ONLY the JSON object. No thinking process, no markdown, no explanations."""
    
    model_configs = [
        {"model": "deepseek-r1:8b", "temperature": 0.1, "max_tokens": 2000},
        {"model": "llama3.2:latest", "temperature": 0.1, "max_tokens": 2000},
        {"model": "llama3:latest", "temperature": 0.1, "max_tokens": 1500},
        {"model": "deepseek-r1:latest", "temperature": 0.1, "max_tokens": 2000},
    ]
    
    last_error = None
    
    for idx, config in enumerate(model_configs):
        try:
            print(f"Attempt {retry_count+1}, Model {idx+1}/{len(model_configs)}: {config['model']} (text: {len(truncated_text)} chars)")
            
            payload = {
                "model": config["model"],
                "messages": [
                    {"role": "system", "content": "You are a resume parsing assistant. Extract structured information and return ONLY valid JSON. No markdown, no explanations."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "temperature": config["temperature"],
                "max_tokens": config.get("max_tokens", 2000)
            }
            
            response = requests.post(
                f"{SKYQ_BASE_URL}/api/chat/completions",
                headers=SKYQ_HEADERS,
                json=payload,
                timeout=90
            )
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                content = None
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0].get('message', {}).get('content')
                elif 'response' in result:
                    content = result['response']
                
                if not content:
                    print("No content in response")
                    continue
                
                print(f"Response preview: {content[:150]}...")
                
                content = content.strip()
                
                if '<think>' in content and '</think>' in content:
                    start = content.find('</think>') + 8
                    content = content[start:].strip()
                    print("Removed reasoning tags")
                
                if content.startswith('```json'):
                    content = content[7:]
                elif content.startswith('```'):
                    content = content[3:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                
                parsed_data = json.loads(content)
                print(f"✅ Resume parsed successfully with {config['model']}")
                return parsed_data
                
            elif response.status_code == 500:
                error_detail = response.text
                print(f"Model {config['model']} returned 500: {error_detail[:100]}")
                last_error = f"500 error with {config['model']}"
                
                if "Ollama: 500" in error_detail:
                    print("Ollama internal error, trying next model...")
                    time.sleep(1)
                    continue
            else:
                last_error = f"Status {response.status_code}"
                print(f"Model {config['model']} failed: {last_error}")
                
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            if 'content' in locals():
                print(f"Failed content: {content[:300]}")
            last_error = f"JSON error: {str(e)}"
            
        except requests.exceptions.Timeout:
            print(f"Model {config['model']} timed out")
            last_error = "Request timeout"
            
        except Exception as e:
            print(f"Model {config['model']} error: {e}")
            last_error = str(e)
    
    if retry_count < 3:
        print(f"\n⚠️ All models failed, retrying with shorter text (attempt {retry_count + 2}/4)...\n")
        time.sleep(2)
        return parse_resume_with_skyq(resume_text, candidate_name, retry_count + 1)
    
    raise Exception(f"All retry attempts exhausted. Last error: {last_error}")

def upload_resume_to_docs(resume_text, filename, parsed_data):
    """Upload resume to docs folder and try to upload to Open WebUI knowledge base"""
    try:
        doc_content = f"""CANDIDATE: {parsed_data.get('name', 'Unknown')}
EMAIL: {parsed_data.get('email', 'N/A')}
PHONE: {parsed_data.get('phone', 'N/A')}
LOCATION: {parsed_data.get('location', 'N/A')}
CURRENT ROLE: {parsed_data.get('current_role', 'N/A')}
CURRENT COMPANY: {parsed_data.get('current_company', 'N/A')}
EXPERIENCE: {parsed_data.get('total_years_experience', 'N/A')} years
ERP SYSTEMS: {', '.join(parsed_data.get('erp_systems', []))}
ERP MODULES: {', '.join(parsed_data.get('erp_modules', []))}
TECHNICAL SKILLS: {', '.join(parsed_data.get('technical_skills', []))}
CERTIFICATIONS: {', '.join(parsed_data.get('certifications', []))}

SUMMARY:
{parsed_data.get('summary', '')}

FULL RESUME TEXT:
{resume_text[:3000]}
"""
        
        local_docs_dir = 'docs_for_rag'
        os.makedirs(local_docs_dir, exist_ok=True)
        local_path = os.path.join(local_docs_dir, f"resume_{filename.replace('.pdf', '').replace('.docx', '')}.txt")
        
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(doc_content)
        
        print(f"✅ Document saved for RAG: {local_path}")
        
        try:
            with open(local_path, 'rb') as f:
                files = {'file': (f"resume_{parsed_data.get('name', 'unknown')}.txt", f, 'text/plain')}
                
                response = requests.post(
                    f"{SKYQ_BASE_URL}/api/v1/knowledge",
                    headers={"Authorization": f"Bearer {SKYQ_JWT_TOKEN}"},
                    files=files,
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    print(f"✅ Uploaded to Open WebUI knowledge base")
                else:
                    print(f"⚠️  Knowledge upload returned {response.status_code} (manual upload recommended)")
        except Exception as upload_error:
            print(f"⚠️  Auto-upload to knowledge base failed: {upload_error}")
            print(f"💡 Tip: Manually upload {local_path} via Open WebUI interface")
        
        return True
        
    except Exception as e:
        print(f"Warning: Could not save document for RAG: {e}")
        return False

def save_to_excel(parsed_data):
    """Save parsed resume data to Excel"""
    try:
        flat_data = {
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Name': parsed_data.get('name', ''),
            'Email': parsed_data.get('email', ''),
            'Phone': parsed_data.get('phone', ''),
            'Location': parsed_data.get('location', ''),
            'LinkedIn': parsed_data.get('linkedin', ''),
            'Summary': parsed_data.get('summary', ''),
            'Total_Years_Experience': parsed_data.get('total_years_experience', ''),
            'Current_Role': parsed_data.get('current_role', ''),
            'Current_Company': parsed_data.get('current_company', ''),
            'ERP_Systems': ', '.join(parsed_data.get('erp_systems', [])),
            'ERP_Modules': ', '.join(parsed_data.get('erp_modules', [])),
            'Technical_Skills': ', '.join(parsed_data.get('technical_skills', [])),
            'Certifications': ', '.join(parsed_data.get('certifications', [])),
            'Education': json.dumps(parsed_data.get('education', [])),
            'Experience': json.dumps(parsed_data.get('experience', [])),
            'Projects': json.dumps(parsed_data.get('projects', []))
        }
        
        if os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE)
            df = pd.concat([df, pd.DataFrame([flat_data])], ignore_index=True)
        else:
            df = pd.DataFrame([flat_data])
        
        df.to_excel(EXCEL_FILE, index=False)
        print(f"✅ Data saved to {EXCEL_FILE}")
        return True
    except Exception as e:
        print(f"Error saving to Excel: {e}")
        raise Exception(f"Failed to save data to Excel: {str(e)}")

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
        if 'content' in locals():
            print(f"Failed content: {content[:300]}")
    except Exception as e:
        print(f"AI search error: {e}")
    
    return []

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

# Routes
@app.route('/')
def home():
    return render_template('Home.html')

@app.route('/resume')
def resume():
    return render_template('Resume.html')

@app.route('/search')
def search_page():
    return render_template('Search.html')

@app.route('/upload', methods=['POST'])
def upload_resume():
    try:
        if 'resume' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['resume']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        print(f"\n📄 File saved: {filepath}")
        
        try:
            if filename.lower().endswith('.pdf'):
                resume_text = extract_text_from_pdf(filepath)
            else:
                resume_text = extract_text_from_docx(filepath)
            
            print(f"📝 Extracted {len(resume_text)} characters")
            
            if len(resume_text) < 50:
                raise Exception("File appears empty or corrupted")
            
        except Exception as e:
            os.remove(filepath)
            return jsonify({'success': False, 'error': f'Text extraction failed: {str(e)}'}), 500
        
        try:
            parsed_data = parse_resume_with_skyq(resume_text, filename)
            
            if not parsed_data:
                raise Exception('No data returned from AI')
            
            parsed_data = enhance_parsed_data(parsed_data, resume_text)
            print("✅ Data enhanced with post-processing")
            
            completeness_score = score_resume_completeness(parsed_data)
            print(f"📊 Resume completeness: {completeness_score}%")
            parsed_data['_completeness_score'] = completeness_score
            
        except Exception as e:
            os.remove(filepath)
            return jsonify({'success': False, 'error': f'AI parsing failed: {str(e)}'}), 500
        
        upload_resume_to_docs(resume_text, filename, parsed_data)
        
        try:
            save_to_excel(parsed_data)
        except Exception as e:
            os.remove(filepath)
            return jsonify({'success': False, 'error': f'Database save failed: {str(e)}'}), 500
        
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'message': 'Resume parsed and saved successfully',
            'data': parsed_data
        })
    
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({'success': False, 'error': 'Search query required'}), 400
        
        print(f"\n🔍 Searching for: {query}")
        
        results = search_with_ai(query)
        
        if not results:
            print("AI search failed, using keyword search...")
            results = fallback_excel_search(query)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        print(f"❌ Search error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download-database')
def download_database():
    if os.path.exists(EXCEL_FILE):
        return send_file(EXCEL_FILE, as_attachment=True)
    return jsonify({'error': 'No database found'}), 404

@app.route('/api/stats')
def get_stats():
    try:
        if os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE)
            return jsonify({'success': True, 'count': len(df)})
        return jsonify({'success': True, 'count': 0})
    except Exception as e:
        return jsonify({'success': False, 'count': 0, 'error': str(e)})

@app.route('/api/clean-database', methods=['POST'])
def clean_database():
    """Clean NaN values from existing database"""
    try:
        if not os.path.exists(EXCEL_FILE):
            return jsonify({'success': False, 'error': 'No database found'}), 404
        
        df = pd.read_excel(EXCEL_FILE)
        original_count = len(df)
        
        df = df.fillna('')
        
        df.to_excel(EXCEL_FILE, index=False)
        
        return jsonify({
            'success': True,
            'message': f'Database cleaned successfully',
            'records': original_count
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 YourERPCoach Resume Parser - SkyQ AI Edition")
    print("="*60)
    print("✅ SkyQ AI token configured")
    print("📊 Using models: deepseek-r1:8b, llama3.2, llama3")
    print("="*60 + "\n")
    app.run(debug=True, port=5000)