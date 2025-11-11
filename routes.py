import os
from flask import render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

from config import UPLOAD_FOLDER, EXCEL_FILE
from utils import allowed_file, extract_text_from_pdf, extract_text_from_docx
from resume_parser import parse_resume_with_skyq, enhance_parsed_data, score_resume_completeness
from yecc_sync import sync_to_yecc_api
from rag_handler import upload_resume_to_docs
from database import save_to_excel, get_resume_count, clean_database
from search import search_with_rag


def register_routes(app):
    """Register all routes with the Flask app"""
    
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
            filepath = os.path.join(UPLOAD_FOLDER, filename)
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
                
                yecc_result = sync_to_yecc_api(parsed_data)
                if yecc_result:
                    parsed_data['_yecc_user_id'] = yecc_result.get('user_id')
                    parsed_data['_yecc_resume_url'] = yecc_result.get('resume_url')
                    parsed_data['_yecc_profile_url'] = yecc_result.get('yecc_profile_url')
                
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
            
            results = search_with_rag(query)
            
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
            count = get_resume_count()
            return jsonify({'success': True, 'count': count})
        except Exception as e:
            return jsonify({'success': False, 'count': 0, 'error': str(e)})
    
    @app.route('/api/clean-database', methods=['POST'])
    def clean_database_route():
        """Clean NaN values from existing database"""
        try:
            success, message = clean_database()
            if success:
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'success': False, 'error': message}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500