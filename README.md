# Vectorless RAG

A lightweight Retrieval-Augmented Generation (RAG) proof of concept that uses **reasoning-driven retrieval** instead of embeddings for efficient document retrieval and querying.

## 🎯 Overview

Vectorless RAG demonstrates an alternative approach to RAG systems by leveraging reasoning-driven retrieval through [PageIndex] instead of traditional vector embeddings. This approach is more lightweight, faster to set up, and reduces infrastructure complexity while maintaining effective retrieval capabilities.

**Key Features:**
- 📄 PDF upload and processing
- 💬 Chat interface with LLM integration
- ⚡ RESTful API backend (FastAPI)
- 🎨 Modern Next.js frontend
- 📐 Mathematical formula rendering (KaTeX support)

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- DeepSeek API key
- PageIndex API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd vectorless
   ```

2. **Backend Setup**
   ```bash
   cd backend
   
   # Create virtual environment
   python -m venv .venv
   
   # Activate virtual environment
   # On Windows:
   .\.venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source .venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

4. **Configure Environment**
   
   Create a `.env` file in the `backend/` directory:
   ```env
   DEEPSEEK_API_KEY=your_api_key_here
   PAGEINDEX_API_KEY=your_pageindex_api_key_here
   ```

### Running the Application

1. **Start the Backend** (from `backend/` directory):
   ```bash
   uvicorn main:app --reload
   ```
   The API will be available at `http://localhost:8000`

2. **Start the Frontend** (from `frontend/` directory):
   ```bash
   npm run dev
   ```
   The web app will be available at `http://localhost:3000`

## 📚 Project Structure

```
vectorless/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── services.py             # Core RAG services (PageIndex, LLM, RAG)
│   ├── requirements.txt         # Python dependencies
│   ├── cache.json             # Local document cache
│   └── uploads/               # Uploaded PDF files
│
├── frontend/
│   ├── src/
│   │   └── app/               # Next.js app directory
│   ├── package.json           # Node dependencies
│   ├── next.config.mjs        # Next.js configuration
│   └── public/                # Static assets
│
└── README.md                   # This file
```

## 🔧 API Endpoints

### POST `/upload`
Upload a PDF file for indexing.
```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@document.pdf"
```

### GET `/status/{doc_id}`
Check processing status of an uploaded document.
```bash
curl http://localhost:8000/status/{doc_id}
```

### POST `/chat`
Send a chat message and retrieve RAG-based response.
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "document_id",
    "message": "Your question here"
  }'
```

## 💻 Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **DeepSeek API** - LLM integration (OpenAI-compatible)ent indexing
- **OpenAI API** - LLM integration
- **Uvicorn** - ASGI server

### Frontend
- **Next.js** - React framework
- **React** - UI library
- **KaTeX** - Mathematical formula rendering
- **CSS** - Styling

## 🔑 Key Concepts

### Vectorless Approach
Unlike traditional RAG systems that use vector embeddings:
- **Reduces complexity**: No need for embedding models or vector databases
- **Faster setup**: Immediate indexing without model training
- **Lower overhead**: Minimal computational and storage requirements
- **Page-aware**: Maintains document structure and page boundaries

### Document Processing Flow
1. User uploads a PDF
2. PageIndex analyzes document structure and creates page-level indices
3. Pages are cached locally for fast retrieval
4. When a query arrives, relevant pages are retrieved
5. Retrieved pages + query are sent to LLM for context-aware responses

## 📝 Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# DeepSeek Configuration
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com  # Optional, defaults to this
DEEPSEEK_MODEL=deepseek-chat  # Optional, defaults to this

# PageIndex Configuration
PAGEINDEX_API_KEY=your_pageindex_api_key

# Optional: Logging
LOG_LEVEL=INFO
```

## 🧪 Development

### Code Organization
- **Backend**: Clean separation of concerns with services layer (`PageIndexService`, `LLMService`, `RAGService`)
- **Frontend**: Next.js app directory structure for better organization
- **Caching**: Local JSON cache for document metadata and indices

## 🛠️ Troubleshooting

**Issue: DeepSeek API errors**
- Verify `DEEPSEEK_API_KEY` is set correctly
- Check API quota and rate limits
- Ensure API key has appropriate permissions
- Verify `DEEPSEEK_BASE_URL` is accessible

**Issue: PageIndex errors**
- Verify `PAGEINDEX_API_KEY` is set correctly
- Ensure API key has document processing
**Issue: OpenAI API errors**
- Verify `OPENAI_API_KEY` is set correctly
- Check API quota and rate limits
- Ensure API key has appropriate permissions

**Issue: PDF upload fails**
- Check file size limits
- Verify PDF is valid and not corrupted
- Check `backend/uploads/` directory permissions

## 🚀 Production Deployment

For production use:
1. Set `allow_origins` in FastAPI CORS configuration to specific domains
2. Use persistent database instead of in-memory cache
3. Implement authentication/authorization
4. Add request validation and rate limiting
5. Use environment-specific configurations
6. Implement proper error handling and logging
7. Set up monitoring and alerting

## 📄 License

[Specify your license here]

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

For issues, questions, or suggestions, please open an issue in the repository.

---

**Built with ❤️ as a RAG POC using PageIndex for document indexing**
