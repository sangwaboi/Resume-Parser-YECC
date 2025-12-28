import os
from flask import Blueprint, render_template, request, jsonify
from werkzeug.utils import secure_filename

from src.config import config
from src.utils import allowed_file, extract_text
from src.services import parser_service, search_service, sync_to_yecc_api
from src.repositories import resume_repository


api = Blueprint('api', __name__)


@api.route('/')
def home():
    return render_template('Home.html')


@api.route('/resume')
def resume_page():
    return render_template('Resume.html')


@api.route('/search')
def search_page():
    return render_template('Search.html')


@api.route('/upload', methods=['POST'])
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
        filepath = os.path.join(config.UPLOAD_FOLDER, filename)
        os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
        file.save(filepath)
        print(f"\n📄 File saved: {filepath}")
        
        try:
            resume_text = extract_text(filepath, filename)
            print(f"📝 Extracted {len(resume_text)} characters")
            
            if len(resume_text) < 50:
                raise Exception("File appears empty or corrupted")
        except Exception as e:
            os.remove(filepath)
            return jsonify({'success': False, 'error': f'Text extraction failed: {str(e)}'}), 500
        
        try:
            parsed_data = parser_service.parse(resume_text, filename)
            
            if not parsed_data:
                raise Exception('No data returned from AI')
            
            parsed_data = parser_service.enhance(parsed_data, resume_text)
            print("✅ Data enhanced with post-processing")
            
            completeness_score = parser_service.score_completeness(parsed_data)
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
        
        try:
            resume_repository.save(parsed_data)
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


@api.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({'success': False, 'error': 'Search query required'}), 400
        
        print(f"\n🔍 Searching for: {query}")
        results = search_service.search(query)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        print(f"❌ Search error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/api/stats')
def get_stats():
    try:
        count = resume_repository.count()
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        return jsonify({'success': False, 'count': 0, 'error': str(e)})
