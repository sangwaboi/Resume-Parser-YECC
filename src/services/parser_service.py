import json
import os
from src.services.ai_service import ai_service
from src.utils.helpers import clean_array, extract_email, extract_phone, extract_linkedin
class ParserService:
    def __init__(self):
        self.json_structure = self._load_json_structure()
        self.system_instruction = "You are a resume parser. Return ONLY valid JSON with no additional text, no markdown, no explanations."
    def _load_json_structure(self):
        structure_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'json_structure.json')
        if not os.path.exists(structure_path):
            structure_path = os.path.join(os.path.dirname(__file__), '..', '..', 'json_structure.json')
        with open(structure_path, 'r') as f:
            return json.load(f)
    def _create_prompt(self, resume_text):
        json_structure_str = json.dumps(self.json_structure, indent=2)
        return f"""Extract information from this resume and return ONLY valid JSON matching this exact structure:
{json_structure_str}
IMPORTANT EXTRACTION RULES:
1. TRACK DETECTION FOR ERP PROJECTS (erp_projects_experience.track):
   - If the track is explicitly mentioned (HCM, SCM, Financials, Technical), use that value.
   - If NOT explicitly mentioned, INFER the track from the modules used in the project:
     * "HCM" or "Human Capital Management" → if modules include: Core HR, Payroll, Benefits, Talent Management, Recruiting, Workforce Management, Time & Labor, Absence Management, Learning
     * "Financials" or "FIN" → if modules include: GL, AP, AR, FA, Cash Management, Expenses, Budgeting, Projects, Revenue Management, Subledger Accounting
     * "SCM" or "Supply Chain" → if modules include: Inventory, Purchasing, Procurement, Order Management, Warehouse, Manufacturing, Planning, Sourcing, Supplier Portal
     * "Technical" → if the role involves: Development, Integration, Reports, RICE, Interfaces, Conversions, Extensions, OIC, VBCS, BI Publisher
   - Do NOT default to "SCM" - determine the correct track based on the actual work described.
2. ROLE DETECTION FOR ERP PROJECTS (erp_projects_experience.role):
   - If explicitly stated, use the mentioned role.
   - If not stated, infer from project description: Functional Consultant, Technical Consultant, Lead, Architect, etc.
3. MODULES ASSIGNMENT:
   - Put HCM-related modules in "hcm_modules"
   - Put Finance-related modules in "financials_modules"  
   - Put Supply Chain modules in "scm_modules"
   - A project can have multiple module types if the consultant worked across tracks.
4. LANGUAGES EXTRACTION:
   - Extract ALL languages the candidate knows (spoken/written).
   - Look for "Languages", "Language Proficiency", "Known Languages" sections.
   - Common languages to look for: English, Hindi, Tamil, Telugu, Kannada, Malayalam, Marathi, Bengali, Gujarati, Punjabi, Urdu, Arabic, French, German, Spanish, etc.
   - If no languages section exists but resume is written in English, include "English" as default.
   - Return as array: ["English", "Hindi", "Tamil"] etc.
Resume:
{resume_text}
Return ONLY the JSON object with no additional text:"""
    def parse(self, resume_text, candidate_name="Unknown"):
        print(f"\n{'='*70}")
        print(f"📄 Parsing Resume (Gemini Primary, Grok Fallback)")
        print(f"{'='*70}")
        print(f"Candidate: {candidate_name}")
        print(f"Resume length: {len(resume_text):,} characters")
        print(f"{'='*70}\n")
        prompt = self._create_prompt(resume_text)
        full_prompt = f"{self.system_instruction}\n\n{prompt}"
        gemini_error = None
        try:
            print(f"🤖 Trying Gemini (Primary)...")
            response = ai_service.call_gemini(full_prompt)
            parsed = ai_service.parse_json_response(response)
            if self._validate_result(parsed):
                score = self.score_completeness(parsed)
                print(f"   Completeness: {score}/100")
                print(f"   ✅ Gemini succeeded!\n")
                return parsed
            else:
                raise Exception("Parsed JSON has no useful data")
        except Exception as e:
            gemini_error = e
            print(f"   ❌ Gemini failed: {str(e)[:100]}")
            print(f"   ⚠️  Falling back to Grok...\n")
        try:
            print(f"🤖 Trying Grok (Fallback)...")
            response = ai_service.call_grok(prompt, self.system_instruction)
            parsed = ai_service.parse_json_response(response)
            score = self.score_completeness(parsed)
            print(f"   Completeness: {score}/100")
            print(f"   ✅ Grok succeeded!\n")
            return parsed
        except Exception as grok_error:
            print(f"   ❌ Grok also failed: {str(grok_error)[:100]}")
            raise Exception(f"All parsers failed. Gemini: {str(gemini_error)[:50]}, Grok: {str(grok_error)[:50]}")
    def _validate_result(self, parsed):
        if not isinstance(parsed, dict):
            return False
        return any([
            parsed.get('name'),
            parsed.get('email'),
            parsed.get('phone'),
            parsed.get('erp_systems'),
            parsed.get('job_experience')
        ])
    def enhance(self, parsed_data, resume_text):
        for field in ['erp_systems', 'erp_modules', 'technical_skills', 'certifications']:
            if field in parsed_data:
                parsed_data[field] = clean_array(parsed_data[field])
        if not parsed_data.get('email'):
            email = extract_email(resume_text)
            if email:
                parsed_data['email'] = email
        if not parsed_data.get('phone'):
            phone = extract_phone(resume_text)
            if phone:
                parsed_data['phone'] = phone
        if not parsed_data.get('linkedin'):
            linkedin = extract_linkedin(resume_text)
            if linkedin:
                parsed_data['linkedin'] = linkedin
        return parsed_data
    def score_completeness(self, parsed_data):
        score = 0
        weights = {
            'name': 15, 'email': 10, 'phone': 10, 'summary': 10,
            'current_role': 10, 'erp_systems': 15, 'erp_modules': 10,
            'job_experience': 10, 'technical_skills': 5, 'education': 5
        }
        for field, weight in weights.items():
            value = parsed_data.get(field)
            if value:
                if isinstance(value, list) and len(value) > 0:
                    score += weight
                elif isinstance(value, str) and value.strip():
                    score += weight
        return min(100, score)
parser_service = ParserService()
