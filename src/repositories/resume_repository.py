import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from src.config import config
class ResumeRepository:
    def __init__(self):
        self.database_url = config.DATABASE_URL
        if not self.database_url:
            raise Exception("DATABASE_URL environment variable is required")
        self._init_database()
    def _get_connection(self):
        conn = psycopg2.connect(self.database_url)
        return conn
    def _init_database(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resumes (
                id SERIAL PRIMARY KEY,
                timestamp TEXT NOT NULL,
                name TEXT,
                email TEXT,
                phone TEXT,
                location TEXT,
                linkedin TEXT,
                summary TEXT,
                total_years_experience TEXT,
                role_title TEXT,
                company_name TEXT,
                erp_systems TEXT,
                erp_modules TEXT,
                technical_skills TEXT,
                certifications TEXT,
                education TEXT,
                job_experience TEXT,
                erp_projects TEXT,
                completeness_score INTEGER DEFAULT 0,
                yecc_user_id TEXT,
                yecc_resume_url TEXT,
                yecc_profile_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_name ON resumes(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_email ON resumes(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_erp_systems ON resumes(erp_systems)')
        conn.commit()
        conn.close()
        print("✅ PostgreSQL database initialized")
    def save(self, parsed_data):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO resumes (
                timestamp, name, email, phone, location, linkedin, summary,
                total_years_experience, role_title, company_name,
                erp_systems, erp_modules, technical_skills, certifications,
                education, job_experience, erp_projects,
                completeness_score, yecc_user_id, yecc_resume_url, yecc_profile_url
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            parsed_data.get('name', ''),
            parsed_data.get('email', ''),
            parsed_data.get('phone', ''),
            parsed_data.get('location', ''),
            parsed_data.get('linkedin', ''),
            parsed_data.get('summary', ''),
            parsed_data.get('total_years_experience', ''),
            parsed_data.get('current_role', ''),
            parsed_data.get('current_company', ''),
            ', '.join(parsed_data.get('erp_systems', [])),
            ', '.join(parsed_data.get('erp_modules', [])),
            ', '.join(parsed_data.get('technical_skills', [])),
            ', '.join(parsed_data.get('certifications', [])),
            json.dumps(parsed_data.get('education', [])),
            json.dumps(parsed_data.get('job_experience', [])),
            json.dumps(parsed_data.get('erp_projects_experience', [])),
            parsed_data.get('_completeness_score', 0),
            parsed_data.get('_yecc_user_id', ''),
            parsed_data.get('_yecc_resume_url', ''),
            parsed_data.get('_yecc_profile_url', '')
        ))
        resume_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        print(f"✅ Data saved to PostgreSQL (ID: {resume_id})")
        return resume_id
    def count(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM resumes')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    def get_all(self):
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM resumes ORDER BY id DESC')
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_dict(row) for row in rows]
    def search(self, query):
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        pattern = f"%{query}%"
        cursor.execute('''
            SELECT * FROM resumes
            WHERE name ILIKE %s OR email ILIKE %s OR role_title ILIKE %s 
                  OR erp_systems ILIKE %s OR erp_modules ILIKE %s OR technical_skills ILIKE %s
                  OR location ILIKE %s OR summary ILIKE %s
            ORDER BY id DESC
        ''', (pattern,) * 8)
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_dict(row) for row in rows]
    def _row_to_dict(self, row):
        return {
            'id': row['id'],
            'Name': row['name'],
            'Email': row['email'],
            'Phone': row['phone'],
            'Location': row['location'],
            'Current_Role': row['role_title'],
            'Current_Company': row['company_name'],
            'Total_Years_Experience': row['total_years_experience'],
            'ERP_Systems': row['erp_systems'],
            'ERP_Modules': row['erp_modules'],
            'Technical_Skills': row['technical_skills'],
            'Certifications': row['certifications'],
            'Summary': row['summary'],
            'Completeness_Score': row['completeness_score'],
            'YECC_User_ID': row['yecc_user_id'],
            'YECC_Resume_URL': row['yecc_resume_url'],
            'YECC_Profile_URL': row['yecc_profile_url'],
            'Timestamp': row['timestamp']
        }
resume_repository = ResumeRepository()
