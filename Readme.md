# YourERPCoach — AI Resume Parser & Search System

A powerful Flask application designed to intelligently parse ERP consultant resumes using SkyQ AI, sync candidate data with YECC platform, and enable smart candidate search using RAG (Retrieval Augmented Generation) technology.

## 🌟 Features

- **AI-Powered Resume Parsing** - Upload PDF/DOCX resumes and extract structured data using multiple AI models (llama3:8b, llama3.2:3b, deepseek-r1:8b, gpt-oss:20b)
- **YECC Platform Integration** - Automatically sync parsed candidate data to YECC platform
- **RAG-Enabled Search** - Intelligent candidate search using document embeddings and vector similarity
- **Excel Database** - Store all parsed resume data in a structured Excel database
- **Multi-Model Fallback** - Automatic retry with different AI models for robust parsing
- **Completeness Scoring** - Rate how complete each parsed resume is (0-100%)
- **Natural Language Search** - Search candidates using natural language queries
- **Clean Architecture** - Modular code structure for easy maintenance and scaling

## 📁 Project Structure

```
yourerpcoach-resume-parser/
├── app.py                    # Main application entry point
├── config.py                 # Configuration settings (API keys, endpoints)
├── utils.py                  # Utility functions (file handling, text extraction)
├── resume_parser.py          # Core resume parsing logic
├── yecc_sync.py             # YECC API synchronization
├── rag_handler.py           # RAG document upload functionality
├── database.py              # Excel database operations
├── search.py                # Search functionality (RAG, AI, keyword)
├── routes.py                # Flask routes and endpoints
├── requirements.txt         # Python dependencies
├── templates/               # HTML templates
│   ├── Home.html           # Landing page
│   ├── Resume.html         # Resume upload page
│   └── Search.html         # Candidate search page
├── uploads/                 # Temporary file upload directory (auto-created)
├── docs_for_rag/           # Local RAG documents storage (auto-created)
└── resumes_database.xlsx   # Excel database (auto-created)
```

## 🔧 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Active internet connection (for API calls)
- SkyQ AI account with API token
- YECC platform account with API token (optional)

## 📦 Installation & Setup

### 1. Clone or Download the Repository

```bash
git clone <repository-url>
cd yourerpcoach-resume-parser
```

### 2. Create Virtual Environment (Recommended)

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API Keys

Open `.env` and update the following:

```python
# SkyQ AI Configuration
SKYQ_JWT_TOKEN = "your_skyq_api_token_here"

# YECC API Configuration (optional)
YECC_API_TOKEN = "your_yecc_api_token_here"
```

**Getting API Keys:**
- **SkyQ AI Token**: Register at [https://ai.skyq.tech](https://ai.skyq.tech) and generate an API token
- **YECC Token**: Register at [https://beta.yecc.tech](https://beta.yecc.tech) (optional, for candidate sync)

### 5. Verify Directory Structure

The app automatically creates necessary directories, but you can verify:

```bash
# These will be created automatically if they don't exist
mkdir -p uploads docs_for_rag
```

## 🚀 Running the Application

Start the Flask development server:

```bash
python app.py
```

You should see:

```
============================================================
🚀 YourERPCoach Resume Parser - SkyQ AI Edition
============================================================
✅ SkyQ AI token configured
📊 Using models: llama3:8b, llama3.2:3b, deepseek-r1:8b, gpt-oss:20b
============================================================

 * Running on http://127.0.0.1:5000
```

Open your browser and navigate to: **http://127.0.0.1:5000**

## 📖 Usage Guide

### Uploading Resumes

1. Navigate to **Resume** page from the home screen
2. Click "Choose File" and select a PDF or DOCX resume
3. Click "Upload & Parse"
4. Wait for the AI to parse the resume (15-30 seconds)
5. View the parsed structured data

**Supported formats:**
- PDF (.pdf)
- Microsoft Word (.docx, .doc)
- Maximum file size: 16 MB

### Searching Candidates

1. Navigate to **Search** page
2. Enter a natural language query, for example:
   - "SAP FICO consultant with 5+ years experience"
   - "Oracle E-Business Suite developer in Bangalore"
   - "Microsoft Dynamics 365 implementation expert"
3. Click "Search"
4. View matched candidates with relevance scores

### Downloading Database

Click the "Download Database" button on any page to download `resumes_database.xlsx` with all parsed resume data.

## 🔌 API Endpoints

### Resume Upload
```http
POST /upload
Content-Type: multipart/form-data

Form field: resume (file)
```

**Response:**
```json
{
  "success": true,
  "message": "Resume parsed and saved successfully",
  "data": {
    "name": "John Doe",
    "email": "john@example.com",
    "erp_systems": ["SAP", "Oracle"],
    ...
  }
}
```

### Search Candidates
```http
POST /search
Content-Type: application/json

{
  "query": "SAP FICO consultant with 5 years experience"
}
```

**Response:**
```json
{
  "success": true,
  "count": 3,
  "results": [
    {
      "Name": "Jane Smith",
      "Email": "jane@example.com",
      "relevance_score": 95,
      "match_reason": "Strong SAP FICO experience"
    }
  ]
}
```

### Get Statistics
```http
GET /api/stats
```

**Response:**
```json
{
  "success": true,
  "count": 25
}
```

### Download Database
```http
GET /download-database
```

Returns the Excel file as attachment.

### Clean Database
```http
POST /api/clean-database
```

Removes NaN values from the database.

## 🏗️ Architecture Overview

### Resume Parsing Flow

```
Upload Resume → Extract Text → AI Parsing (Multi-Model) → 
Enhance Data → Score Completeness → Sync to YECC → 
Upload to RAG → Save to Excel → Return Results
```

### Search Flow

```
Search Query → RAG Search (with embeddings) → 
AI Search (fallback) → Keyword Search (final fallback) → 
Return Ranked Results
```

### AI Models Used

The system uses multiple models with automatic fallback:

1. **llama3:8b** (Primary) - Best for complex parsing
2. **llama3.2:3b** (Fallback 1) - Faster, good accuracy
3. **deepseek-r1:8b** (Fallback 2) - Alternative reasoning
4. **gpt-oss:20b** (Fallback 3) - Last resort, highest capacity

## 📊 Database Schema

The Excel database contains these columns:

| Column | Description |
|--------|-------------|
| Timestamp | Upload date/time |
| Name | Candidate full name |
| Email | Email address |
| Phone | Contact number |
| Location | City/Region |
| LinkedIn | LinkedIn profile URL |
| Summary | Professional summary |
| Total_Years_Experience | Years of experience |
| Current_Role | Current job title |
| Current_Company | Current employer |
| ERP_Systems | ERP platforms (SAP, Oracle, etc.) |
| ERP_Modules | Modules (FI, CO, MM, SD, etc.) |
| Technical_Skills | Programming/technical skills |
| Certifications | Professional certifications |
| Education | Academic background (JSON) |
| Experience | Work history (JSON) |
| Projects | Project details (JSON) |
| RAG_File_ID | RAG document reference |
| Completeness_Score | Parse quality score (0-100) |
| YECC_User_ID | YECC platform user ID |
| YECC_Resume_URL | YECC resume identifier |
| YECC_Profile_URL | YECC profile link |

## 🛠️ Configuration Options

Edit `config.py` to customize:

```python
# File Upload Settings
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc'}

# AI Model Configuration
MODEL_CONFIGS = [
    {"model": "llama3:8b", "temperature": 0.1, "max_tokens": 1500},
    # Add or modify models as needed
]

# Text Processing
MAX_TEXT_LENGTHS = [5000, 4000, 3000, 2500]  # Retry with shorter text
```

## 🔍 Troubleshooting

### API Token Errors

**Problem:** `SkyQ AI token not configured`

**Solution:** Update `SKYQ_JWT_TOKEN` in `config.py` with your valid token

### Resume Parsing Fails

**Problem:** All models fail to parse

**Solutions:**
- Check if resume has extractable text (not scanned images)
- Try a different file format (PDF vs DOCX)
- Verify internet connection
- Check SkyQ AI service status

### Search Returns No Results

**Problem:** Search finds no candidates

**Solutions:**
- Verify database has entries: Check if `resumes_database.xlsx` exists
- Try broader search terms
- Check if RAG_File_ID column has values (RAG may be disabled)

### YECC Sync Failures

**Problem:** User already registered or sync errors

**Solution:** This is non-critical. The app continues without YECC sync. Update YECC token or disable sync by commenting out in `routes.py`.

### File Upload Size Limit

**Problem:** File too large error

**Solution:** Increase `MAX_CONTENT_LENGTH` in `config.py`:
```python
MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32 MB
```

## 🔒 Security Considerations

⚠️ **For Production Use:**

1. **API Keys**: Store tokens in environment variables, not in code
   ```python
   import os
   SKYQ_JWT_TOKEN = os.getenv('SKYQ_JWT_TOKEN')
   ```

2. **File Validation**: Add virus scanning for uploaded files

3. **Rate Limiting**: Implement rate limiting on API endpoints

4. **Authentication**: Add user authentication for access control

5. **HTTPS**: Deploy behind reverse proxy with SSL/TLS

6. **Input Sanitization**: Validate all user inputs

## 🧪 Development & Testing

### Running in Development Mode

The app runs in debug mode by default:

```bash
python app.py
```

### Testing Individual Modules

```python
# Test resume parsing
from resume_parser import parse_resume_with_skyq
result = parse_resume_with_skyq("resume text here")

# Test search
from search import search_with_rag
results = search_with_rag("SAP consultant")
```

### Adding New Features

1. **New AI Model**: Add to `MODEL_CONFIGS` in `config.py`
2. **New Route**: Add to `routes.py` and register in `register_routes()`
3. **New Field**: Update parser prompt in `resume_parser.py` and database schema in `database.py`

## 📈 Performance Tips

1. **RAG Upload**: Disable if not using search features (comment out in `routes.py`)
2. **YECC Sync**: Disable if not needed (comment out in `routes.py`)
3. **Model Selection**: Use smaller models (llama3.2:3b) for faster parsing
4. **Caching**: Implement Redis caching for frequent searches
5. **Batch Processing**: Process multiple resumes via CLI script

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- [ ] Add user authentication
- [ ] Implement batch upload
- [ ] Add resume comparison feature
- [ ] Export to different formats (JSON, CSV)
- [ ] Add more AI models
- [ ] Improve UI/UX with React frontend
- [ ] Add unit tests
- [ ] Docker containerization
- [ ] Cloud deployment scripts

## 📝 License

This project is provided as-is for educational and commercial use.

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review console logs for detailed error messages
3. Verify API credentials are valid
4. Ensure all dependencies are installed correctly

## 🙏 Acknowledgments

- **SkyQ AI** - AI model hosting and API
- **YECC Platform** - Candidate management integration
- **Flask** - Web framework
- **PyPDF2** - PDF text extraction
- **python-docx** - Word document parsing
- **pandas** - Data management

---

**Version:** 2.0  
**Last Updated:** November 2025  
**Python Version:** 3.8+

For the latest updates and documentation, visit the project repository.
