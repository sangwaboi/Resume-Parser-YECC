import os
import json
import pandas as pd
from datetime import datetime
from config import EXCEL_FILE


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
            'Projects': json.dumps(parsed_data.get('projects', [])),
            'RAG_File_ID': parsed_data.get('_rag_file_id', ''),
            'Completeness_Score': parsed_data.get('_completeness_score', 0),
            'YECC_User_ID': parsed_data.get('_yecc_user_id', ''),
            'YECC_Resume_URL': parsed_data.get('_yecc_resume_url', ''),
            'YECC_Profile_URL': parsed_data.get('_yecc_profile_url', '')
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


def get_resume_count():
    """Get the total count of resumes in database"""
    try:
        if os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE)
            return len(df)
        return 0
    except Exception as e:
        print(f"Error getting resume count: {e}")
        return 0


def clean_database():
    """Clean NaN values from existing database"""
    try:
        if not os.path.exists(EXCEL_FILE):
            return False, "No database found"
        
        df = pd.read_excel(EXCEL_FILE)
        original_count = len(df)
        
        df = df.fillna('')
        df.to_excel(EXCEL_FILE, index=False)
        
        return True, f'Database cleaned successfully. {original_count} records processed.'
    except Exception as e:
        return False, str(e)