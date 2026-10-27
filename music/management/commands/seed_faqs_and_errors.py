from django.core.management.base import BaseCommand
from music.models import FAQ, ErrorCode

class Command(BaseCommand):
    help = 'Seeds FAQ items and Error Code references into SQLite SQL database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding FAQ items into SQL database..."))

        faqs_data = [
            {
                "question": "What is MoodMusic and how does it work?",
                "category": "General",
                "order": 1,
                "answer": "MoodMusic is an intelligent, mood-driven music platform designed to match your emotional state with real hit songs by world-famous artists. You can browse curated mood playlists (Happy, Sad, Chill, Energetic, Romantic, Focus), generate bespoke vibes via the AI DJ, and enjoy in-browser audio previews without subscription paywalls."
            },
            {
                "question": "Do I need to create an account or sign up to listen to songs?",
                "category": "General",
                "order": 2,
                "answer": "No! MoodMusic offers frictionless public access. You can browse all moods, search tracks, play audio previews, interact with the AI Assistant, and generate AI songs immediately without logging in or providing personal credentials."
            },
            {
                "question": "How does the AI Mood DJ recommend music?",
                "category": "AI Assistant",
                "order": 3,
                "answer": "The AI DJ uses Google's latest Gemini Generative AI models combined with an iTunes Search API fallback. It analyzes the emotional intent, tempo, and genre cues of your prompt (e.g., 'calm late night coding with lo-fi beats') to calculate energy scores and curate tracks that fit your state."
            },
            {
                "question": "How can I add or generate new songs using AI?",
                "category": "AI Assistant",
                "order": 4,
                "answer": "Click the 'AI Song Studio' button in the top navigation or sidebar. Type any artist name, song title, or emotional vibe (e.g., 'Taylor Swift upbeat pop' or 'energetic EDM workout'). The Gemini AI and iTunes API will find real tracks, fetch high-resolution album artwork, download preview audio, and add it directly to your library."
            },
            {
                "question": "Can I preview and play music directly in the browser?",
                "category": "Audio & Player",
                "order": 5,
                "answer": "Yes! Every track in MoodMusic includes an integrated HTML5 audio player located at the bottom of the screen. You can play, pause, scrub through the timeline, adjust volume, and shuffle through playlist queues seamlessly."
            },
            {
                "question": "Why do audio previews play for 30-45 seconds?",
                "category": "Audio & Player",
                "order": 6,
                "answer": "To comply with international digital copyright and fair licensing agreements, web preview streams are legally licensed 30-to-45-second high-fidelity samples. For full-length streaming, every song card provides direct links to Spotify and YouTube Music."
            },
            {
                "question": "What should I do if a song fails to play or stops unexpectedly?",
                "category": "Errors & Troubleshooting",
                "order": 7,
                "answer": "First, verify that your browser has autoplay permissions enabled and that you are not in silent mode. If a specific audio preview fails to load, it may have encountered Error 488 (Audio Stream Unavailable). You can open our floating AI Chat Assistant to diagnose the track or automatically create a support ticket."
            },
            {
                "question": "What does Error Code 488 (Audio Stream Unavailable) mean?",
                "category": "Errors & Troubleshooting",
                "order": 8,
                "answer": "Error 488 is MoodMusic's site-specific error code. It indicates that the remote audio preview CDN stream or iTunes preview URL is temporarily unreachable, expired, or geographically restricted. Our system automatically attempts a cached fallback when this occurs."
            },
            {
                "question": "How does the AI Assistant help me when I encounter an error?",
                "category": "AI Assistant",
                "order": 9,
                "answer": "Our integrated AI Assistant is available on every page via the bottom-right chat widget. It has complete knowledge of our SQL FAQ repository and HTTP/site-specific error codes. If you type 'Explain 404' or describe an issue, it will diagnose the cause and offer actionable troubleshooting steps."
            },
            {
                "question": "How are support tickets created and tracked?",
                "category": "Errors & Troubleshooting",
                "order": 10,
                "answer": "If the AI Assistant cannot resolve your question, or if you request human developer support, the assistant will automatically generate a Support Ticket stored in our SQL database. You can also visit our dedicated /support/ page to submit and review existing tickets by ticket number."
            },
            {
                "question": "Where are chat conversations and user feedback stored?",
                "category": "Account & Data",
                "order": 11,
                "answer": "To provide high-performance, non-blocking telemetry, all AI chat conversations and feedback ratings (thumbs up/down and comments) are stored in a NoSQL MongoDB collection ('chat_logs' and 'chat_feedback'). Support tickets and FAQ data remain stored in the relational SQL database."
            },
            {
                "question": "Is my listening activity and feedback private?",
                "category": "Account & Data",
                "order": 12,
                "answer": "Yes. MoodMusic does not sell or share user session data. Chat interactions are pseudonymized with ephemeral session IDs to continuously improve AI response accuracy."
            }
        ]

        for item in faqs_data:
            faq, created = FAQ.objects.update_or_create(
                question=item["question"],
                defaults={
                    "category": item["category"],
                    "order": item["order"],
                    "answer": item["answer"],
                }
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  [{action}] FAQ #{faq.id}: {faq.question}")

        self.stdout.write(self.style.NOTICE("\nSeeding 8 Error Code references into SQL database..."))

        error_codes_data = [
            {
                "code": 400,
                "name": "Bad Request",
                "category": "Client Error",
                "is_site_specific": False,
                "meaning": "The server cannot or will not process the request due to something perceived to be a client error (e.g. malformed request syntax, invalid query parameters, or deceptive routing).",
                "common_causes": "Malformed JSON payload in API calls, missing required form fields, invalid song ID parameters, or corrupted browser cookies.",
                "troubleshooting_steps": "1. Verify that your query string syntax is correct.\n2. Ensure all required POST body fields are provided.\n3. Clear browser cache and local session storage.\n4. Ask the AI assistant to inspect the exact request format."
            },
            {
                "code": 401,
                "name": "Unauthorized",
                "category": "Client Error",
                "is_site_specific": False,
                "meaning": "The request requires user authentication or valid credentials that were either missing or rejected.",
                "common_causes": "Expired session token, missing Authorization header, or accessing restricted administrative endpoints without signing in.",
                "troubleshooting_steps": "1. Sign in to your account with valid administrator credentials.\n2. Verify that your session cookie has not expired.\n3. Refresh your authorization token if accessing programmatic endpoints."
            },
            {
                "code": 403,
                "name": "Forbidden",
                "category": "Client Error",
                "is_site_specific": False,
                "meaning": "The server understood the request, but refuses to authorize it. Unlike 401, re-authenticating will not make a difference because the client lacks requisite permissions.",
                "common_causes": "Cross-Site Request Forgery (CSRF) token failure, insufficient user permissions, or IP-based rate blockades.",
                "troubleshooting_steps": "1. Ensure CSRF tokens are included with all POST/PUT/DELETE requests.\n2. Check whether your account has administrative privileges.\n3. Contact support to request elevated permissions."
            },
            {
                "code": 404,
                "name": "Not Found",
                "category": "Client Error",
                "is_site_specific": False,
                "meaning": "The origin server did not find a current representation for the target resource or is not willing to disclose that one exists.",
                "common_causes": "Typo in the URL address bar, a track ID that was deleted or renamed, or an expired temporary link.",
                "troubleshooting_steps": "1. Check the URL spelling in the browser address bar.\n2. Use the search bar to find the track or mood.\n3. Click 'Ask the Assistant' on our custom 404 page for automated navigation help."
            },
            {
                "code": 429,
                "name": "Too Many Requests",
                "category": "Client Error",
                "is_site_specific": False,
                "meaning": "The user has sent too many requests in a given amount of time ('rate limiting').",
                "common_causes": "Rapid automated scraping, firing dozens of AI Song generation requests within seconds, or exceeding Google Gemini API quota limits.",
                "troubleshooting_steps": "1. Pause for 30 to 60 seconds before submitting a new AI request.\n2. Avoid rapid repetitive clicking on generation buttons.\n3. Check the /health/ dashboard to verify upstream API quota status."
            },
            {
                "code": 500,
                "name": "Internal Server Error",
                "category": "Server Error",
                "is_site_specific": False,
                "meaning": "The server encountered an unexpected condition that prevented it from fulfilling the request.",
                "common_causes": "Unhandled server exception, database deadlock, misconfigured environment variables, or unexpected third-party API response format.",
                "troubleshooting_steps": "1. Check the server terminal and `logs/requests.log` for traceback details.\n2. Ensure database migrations and `.env` keys are properly configured.\n3. Click 'Ask the Assistant' on the 500 page to automatically create a high-priority ticket."
            },
            {
                "code": 503,
                "name": "Service Unavailable",
                "category": "Server Error",
                "is_site_specific": False,
                "meaning": "The server is currently unable to handle the request due to a temporary overloading or maintenance of the server or upstream services.",
                "common_causes": "Upstream AI model maintenance, heavy network traffic, or temporary loss of internet connectivity to external music CDNs.",
                "troubleshooting_steps": "1. Retry the operation after a few seconds.\n2. Check the /health/ status page to see if external APIs are responding.\n3. MoodMusic's fallback engine will automatically attempt cached responses."
            },
            {
                "code": 488,
                "name": "Audio Stream Unavailable",
                "category": "Site-Specific",
                "is_site_specific": True,
                "meaning": "MoodMusic site-specific status code. The requested audio preview stream (.m4a / .mp3) could not be retrieved from the CDN, the sample link expired, or the media format is unsupported.",
                "common_causes": "Third-party audio CDN link expiration, regional licensing restrictions on a specific song preview, or corrupted local media cache.",
                "troubleshooting_steps": "1. Click the Spotify or YouTube Music link on the song card to listen directly.\n2. Click the 'Regenerate Audio Stream' button to pull a fresh CDN link.\n3. Ask the AI assistant to file a report for the broken track ID."
            }
        ]

        for item in error_codes_data:
            err_obj, created = ErrorCode.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "category": item["category"],
                    "is_site_specific": item["is_site_specific"],
                    "meaning": item["meaning"],
                    "common_causes": item["common_causes"],
                    "troubleshooting_steps": item["troubleshooting_steps"],
                }
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  [{action}] Error Code {err_obj.code}: {err_obj.name}")

        self.stdout.write(self.style.SUCCESS(f"\nSuccessfully seeded {len(faqs_data)} FAQs and {len(error_codes_data)} Error Codes into SQL!"))
