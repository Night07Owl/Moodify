# 🎵 MoodMusic — Final Assessment Submission
### AI-Driven Ambient Music Platform & Interactive Support Assistant

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)](https://djangoproject.com)
[![SQL Database](https://img.shields.io/badge/SQL-SQLite3-003B57?logo=sqlite&logoColor=white)](https://sqlite.org)
[![MongoDB](https://img.shields.io/badge/NoSQL-MongoDB_/_mongomock-47A248?logo=mongodb&logoColor=white)](https://mongodb.com)
[![Google Gemini](https://img.shields.io/badge/AI-Google_Gemini_Flash-8E75C2?logo=google&logoColor=white)](https://ai.google.dev)
[![Apple iTunes API](https://img.shields.io/badge/Third--Party_API-Apple_iTunes_Search-FC3C44?logo=apple&logoColor=white)](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/index.html)

---

## 📋 Assessment Submission Details

| Item | Details |
| :--- | :--- |
| **Individual Task Title** | **Moodify: AI-Driven Ambient Music Platform & Interactive Support Assistant** |
| **Live Website Link (HTTPS)** | [https://moodify-spf8.onrender.com/](https://moodify-spf8.onrender.com/) |
| **GitHub Repository Link** | [https://github.com/Night07Owl/Moodify](https://github.com/Night07Owl/Moodify) |
| **Task Sheet Reference** | [Software Development Final Assessment Sheet](https://docs.google.com/spreadsheets/d/1gac3qN_sFgbBQR7utv6N-66-C8szNq3-F6L7NQsbx78/edit?usp=sharing) |

## 🏛️ Architecture & Data Persistence Flow

```
                               ┌─────────────────────────────────────────────────────┐
                               │                    User Client                      │
                               │        (Mobile / Desktop Browser + Audio)           │
                               └──────────────────────────┬──────────────────────────┘
                                                          │ HTTP Requests
                                                          ▼
                               ┌─────────────────────────────────────────────────────┐
                               │      music.middleware.RequestLoggingMiddleware      │
                               │           (Appends to logs/requests.log)            │
                               └──────────────────────────┬──────────────────────────┘
                                                          │
                                                          ▼
                               ┌─────────────────────────────────────────────────────┐
                               │                 Django Core Router                  │
                               │             (moodify/urls.py + views.py)            │
                               └──────────────┬──────────────────┬───────────────────┘
                                              │                  │
                      ┌───────────────────────┘                  └───────────────────────┐
                      ▼                                                                  ▼
       ┌──────────────────────────────┐                                   ┌──────────────────────────────┐
       │   Relational SQL Database    │                                   │      NoSQL MongoDB Store     │
       │          (SQLite3)           │                                   │     (pymongo / mongomock)    │
       ├──────────────────────────────┤                                   ├──────────────────────────────┤
       │ • FAQs (12 entries)          │                                   │ • chat_logs                  │
       │ • ErrorCodes (8 entries)     │                                   │   (session_id, user_msg,     │
       │ • SupportTickets (SQL state) │                                   │    bot_reply, latency, IP)   │
       │ • Songs (Curated tracks)     │                                   │ • chat_feedback              │
       │ • Moods & Favorites          │                                   │   (rating, thumbs, comments) │
       └──────────────┬───────────────┘                                   └──────────────────────────────┘
                      │ Grounding Context
                      ▼
       ┌──────────────────────────────────────────────────────────────────┐
       │               MoodMusic AI Support Engine                        │
       │  • Google Gemini Flash Lite API (gemini-flash-lite-latest)       │
       │  • Grounded in SQL FAQs & Error Code Directory                   │
       │  • Automatic SQL Ticket Escalation when unanswerable             │
       │  • Deterministic Rule Matcher Fallback                           │
       └──────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
       ┌──────────────────────────────────────────────────────────────────┐
       │             Third-Party API: Apple iTunes Search                 │
       │  • Strict 5.0-Second Timeout Limit                               │
       │  • High-Res 600x600 Album Artwork & 30s Vocal Audio Previews     │
       │  • Local Curated Fallback on Network Interruption                │
       └──────────────────────────────────────────────────────────────────┘
```

---

## 🚀 One Proposed Improvement: Real-Time Collaborative Mood Rooms & Vector Embeddings

### 1. Vision & Architecture
Transform MoodMusic from a solitary listening experience into a **real-time social audio sanctuary**:
- **Collaborative Mood Rooms**: Users join ephemeral rooms based on shared emotional states (e.g., *"Late-Night Coding in Chill"* or *"Marathon Training in Energetic"*).
- **Synchronized Audio Playback**: Powered by **Django Channels** and **WebSockets** with sub-50ms clock drift synchronization, allowing multiple users across the globe to hear the exact same audio stream simultaneously.
- **AI-Powered Vector Similarity Matching**:
  - Rather than relying solely on keyword queries, track metadata and emotional text prompts will be converted into high-dimensional semantic vectors using Google's `text-embedding-004` model.
  - Stored in a vector database (such as **pgvector** or **MongoDB Atlas Vector Search**).
  - When a user types *"gentle rainy Sunday afternoon with a cup of chamomile tea"*, vector cosine similarity instantly discovers tracks that mathematically align with that precise emotional valence and energy level.

### 2. Implementation Roadmap
1. **Transport Layer**: Install `channels` and `daphne` ASGI server with a Redis channel layer backing pub/sub group broadcasting.
2. **Audio Sync Protocol**: Exchange lightweight JSON sync packets:
   ```json
   {
     "event": "TRACK_SEEK",
     "track_id": 42,
     "server_timestamp_ms": 1798361000,
     "position_seconds": 14.5,
     "playback_state": "PLAYING"
   }
   ```
3. **Smart Assistant Moderation**: The existing AI Assistant is hooked into the room's WebSocket channel to answer live queries, vote on the next track based on room mood sentiment, and automatically resolve audio playback errors.

---

## 🛠️ Local Setup & Installation Guide

### Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/Night07Owl/Moodify.git
cd Moodify
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On macOS/Linux:
source .venv/bin/activate

# Install dependencies:
pip install django google-genai python-dotenv pymongo mongomock requests
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and insert your Gemini API key:
```bash
cp .env.example .env
```
In `.env`:
```ini
SECRET_KEY=your-secure-django-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost,*
GEMINI_API_KEY=AIzaSyYourGeminiApiKeyHere
MONGODB_URI=mongodb://127.0.0.1:27017/moodmusic_db
MONGODB_NAME=moodmusic_db
```
*(Note: If a live MongoDB instance is not detected, MoodMusic automatically activates `mongomock` in-memory fallback with zero crashes).*

### 4. Run Migrations & Seed Grounding Data
```bash
python manage.py migrate
python manage.py seed_faqs_and_errors
python manage.py seed_songs
```

### 5. Launch Development Server
```bash
python manage.py runserver 127.0.0.1:8000
```
Visit `http://127.0.0.1:8000` in your browser!

---

## 🧪 Verification & Demonstration Checkpoints

### 1. Testing Core Pages (≥ 3 Pages)
- **Home / Player**: `http://127.0.0.1:8000/`
- **FAQ & Error Codes (SQL)**: `http://127.0.0.1:8000/faq/`
- **Support Ticket Center (SQL)**: `http://127.0.0.1:8000/support/`
- **Health Check & Telemetry**: `http://127.0.0.1:8000/health/`

### 2. Testing Custom 404 & 500 Pages
- Navigate to an invalid address: `http://127.0.0.1:8000/some-non-existent-page/`
- Or test the dedicated error preview routes:
  - 404 Preview: `http://127.0.0.1:8000/test-404/`
  - 500 Preview: `http://127.0.0.1:8000/test-500/`
- Click the **"Ask the Assistant"** button on either error page: observe that the AI Assistant panel instantly pops open, explains the error code, and offers actionable troubleshooting steps!

### 3. Testing Persistent Chat Assistant & Ticket Escalation
1. Click the floating **"AI Assistant"** button in the bottom right corner (present on every page).
2. Ask: *"Explain error 488"* &rarr; Assistant explains the site-specific **Audio Stream Unavailable** code with causes and fixes.
3. Ask: *"Do I need to sign up to play music?"* &rarr; Assistant answers accurately grounded in SQL FAQ #2.
4. Ask an unanswerable question or request assistance: *"I was charged twice on my credit card please help!"* &rarr; Assistant detects the question is outside the FAQ, explains politely, and provides an interactive button to **Create a Support Ticket in SQL**.
5. Once created, observe the generated Ticket ID (e.g. `TCK-XXXXXXXX`) and view it live in the **[Support Tickets Portal](/support/)**!
6. Click the 👍 or 👎 icons beneath any assistant reply: observe the real-time confirmation that feedback was persisted to MongoDB.

### 4. Testing Request Logging & Third-Party API Fallback
1. Open `logs/requests.log` to inspect real-time HTTP telemetry intercepted by `RequestLoggingMiddleware`.
2. Open `http://127.0.0.1:8000/health/` or `http://127.0.0.1:8000/health/?format=json` to view the comprehensive live health dashboard.

---

## 📱 Mobile Responsiveness Verification
The website layout, sidebar drawer, player bar, and floating AI chat widget are optimized for mobile viewports using CSS media queries (`max-width: 768px` and `max-width: 640px`):
- Navigation collapses cleanly into fluid top/bottom controls.
- The floating chat assistant adapts to a mobile drawer modal (`width: calc(100vw - 16px)`).
- Touch controls for audio playback, scrubber seeking, and FAQ accordion tabs are responsive and tap-friendly.

---

## 🔒 Confidentiality & Security
- All sensitive API keys and secrets are loaded strictly from environment variables via `.env`.
- `.gitignore` prevents `.env`, `logs/requests.log`, and `db.sqlite3` from being committed to source control.
- Cross-Site Request Forgery (CSRF) protection is enforced on all data-modifying POST endpoints.

