"""
Moodify AI Service
Provides intelligent mood detection, emotional analysis, personalized AI DJ commentary,
and AI song recommendation generation.

Supports:
1. Out-of-the-box instant Semantic & Emotional NLP Reasoning (zero API keys needed).
2. Google Gemini API (if GEMINI_API_KEY is configured in environment or settings).
"""

import os
import re
import json
import random
from django.conf import settings

# Curated high-aesthetic album covers categorized by mood
MOOD_ARTWORKS = {
    'happy': [
        'https://images.unsplash.com/photo-1518609878373-06d740f60d8b?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=600&auto=format&fit=crop&q=80',
    ],
    'chill': [
        'https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=600&auto=format&fit=crop&q=80',
    ],
    'energetic': [
        'https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1511192336575-5a79af67a629?w=600&auto=format&fit=crop&q=80',
    ],
    'romantic': [
        'https://images.unsplash.com/photo-1518199266791-5375a83190b7?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1516589178581-6cd7833ae3b2?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1519741497674-611481863552?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1515934751635-c81c6bc9a2d8?w=600&auto=format&fit=crop&q=80',
    ],
    'focus': [
        'https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1507842229452-788107567702?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=600&auto=format&fit=crop&q=80',
    ],
    'sad': [
        'https://images.unsplash.com/photo-1515694346937-94d85e41e6f0?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1499209974431-9dddcece7f88?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1475922150372-e054ad2c4277?w=600&auto=format&fit=crop&q=80',
    ],
}

# Reliable CC0 / Royalty-Free audio preview streams
AUDIO_PREVIEWS = [
    'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3',
    'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3',
    'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3',
    'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3',
    'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3',
    'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3',
    'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3',
    'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-10.mp3',
]

# Comprehensive Emotional & Situational Taxonomy
MOOD_KEYWORDS = {
    'happy': {
        'weight': 1.0,
        'keywords': [
            'happy', 'joy', 'smile', 'cheerful', 'uplifting', 'good', 'great', 'sunshine', 'fun',
            'excited', 'blessed', 'celebrate', 'celebration', 'dance', 'laugh', 'delight',
            'optimistic', 'euphoric', 'weekend', 'bright', 'grateful', 'vibrant', 'summer'
        ],
        'default_energy': 80,
        'dj_comments': [
            "You've got that radiant sunshine energy! Let's amplify these good vibes with upbeat rhythms.",
            "Euphoric and lighthearted! Tuning your frequencies to high-tempo dopamine-boosting beats.",
            "Life is feeling good right now! Here is a curated selection to keep you smiling.",
        ]
    },
    'chill': {
        'weight': 1.0,
        'keywords': [
            'chill', 'relax', 'calm', 'peaceful', 'serene', 'unwind', 'mellow', 'laid back',
            'lofi', 'coffee', 'cozy', 'evening', 'breeze', 'smooth', 'rest', 'lazy',
            'easygoing', 'downtime', 'couch', 'tea', 'sunset', 'soft', 'slow'
        ],
        'default_energy': 40,
        'dj_comments': [
            "Time to take a deep breath and decompress. Dialing into calm frequencies and warm lo-fi tones.",
            "Soft textures and mellow vibrations ahead. Sink back and let the tension fade away.",
            "Pure acoustic serenity. Here's your gentle soundscape for effortless relaxation.",
        ]
    },
    'energetic': {
        'weight': 1.0,
        'keywords': [
            'energetic', 'hype', 'workout', 'gym', 'run', 'running', 'pump', 'pumped',
            'power', 'beast', 'fast', 'intense', 'hard', 'rush', 'adrenaline', 'party',
            'dancefloor', 'club', 'explosive', 'drive', 'speed', 'unstoppable', 'hyped'
        ],
        'default_energy': 95,
        'dj_comments': [
            "Maximum voltage detected! Turning the intensity up to 11 with driving basslines and high BPM.",
            "Ready to conquer the session! Here's your high-octane soundtrack for unstoppable momentum.",
            "High adrenaline, heavy drops, and relentless energy. Let's get moving!",
        ]
    },
    'romantic': {
        'weight': 1.0,
        'keywords': [
            'romantic', 'love', 'date', 'candle', 'crush', 'intimate', 'sweetheart', 'heart',
            'passion', 'kiss', 'lovers', 'dinner', 'together', 'sweet', 'warmth', 'affection',
            'soulmate', 'serenade', 'holding hands', 'butterflies', 'darling'
        ],
        'default_energy': 55,
        'dj_comments': [
            "Love is in the air. Tuning in lush harmonies and romantic serenades for that intimate warmth.",
            "Velvet chords and heartfelt melodies. Perfect for a cozy candlelight moment.",
            "Deep affection and tender rhythms. Here are sweet soundtracks crafted for romance.",
        ]
    },
    'focus': {
        'weight': 1.0,
        'keywords': [
            'focus', 'study', 'studying', 'code', 'coding', 'work', 'working', 'exam',
            'homework', 'read', 'reading', 'deep work', 'binaural', 'concentration', 'productive',
            'deadline', 'library', 'office', 'algorithm', 'flow state', 'brain', 'night owl'
        ],
        'default_energy': 50,
        'dj_comments': [
            "Entering deep flow state. Eliminating cognitive clutter with steady, distraction-free rhythms.",
            "Laser focus mode engaged! Minimalist cadences to lock your brain into the task at hand.",
            "Flowing beats engineered for mental clarity, uninterrupted studying, and creative breakthroughs.",
        ]
    },
    'sad': {
        'weight': 1.0,
        'keywords': [
            'sad', 'heartbroken', 'heartbreak', 'heartbreaking', 'cry', 'crying', 'lonely', 'alone', 'hurt', 'depressed',
            'melancholy', 'tears', 'miss', 'missing', 'loss', 'grief', 'pain', 'broken',
            'gloomy', 'rain', 'rainy', 'exhausted', 'exhausting', 'tired', 'down', 'nostalgic', 'regret'
        ],
        'default_energy': 30,
        'dj_comments': [
            "I hear you. Sometimes we need music that understands the heavy moments and lets us heal.",
            "Cathartic acoustic strings and gentle melancholy to accompany your quiet thoughts.",
            "Soft comforting melodies. It's okay to feel deeply—let the music hold space for you.",
        ]
    }
}

# Song Idea Templates for AI Song Generator
AI_SONG_CREATIONS = {
    'happy': [
        ('Solar Flare Reverie', 'The Sunburst Trio', 'Indie Pop', 'Uplifting guitar riffs drenched in golden hour warmth.'),
        ('Golden Hour Bounce', 'Neon Horizon', 'Synthpop', 'Bouncy synth basslines and shimmering optimism.'),
        ('Dopamine Bloom', 'Aura Echo', 'Nu-Disco', 'Infectious groove designed to spark spontaneous dancing.'),
        ('Saturday Morning High', 'Cloud 9 Collective', 'Acoustic Pop', 'Gentle acoustic strumming with cheerful whistle hooks.')
    ],
    'chill': [
        ('Midnight Rain Lo-Fi', 'Coffee & Cassettes', 'Lo-Fi Beats', 'Mellow vinyl crackles paired with hypnotic jazz chords.'),
        ('Drifting on Lavender Waves', 'Kyoto Drift', 'Ambient Chill', 'Ethereal synth pads that feel like weightless floating.'),
        ('Cedar & Cinnamon', 'Velvet Coast', 'Indie Acoustic', 'Warm wooden acoustic guitar melodies for quiet afternoons.'),
        ('Afternoon Haze', 'Soma Chillout', 'Downtempo', 'Subtle sub-bass and brushed percussion for deep relaxation.')
    ],
    'energetic': [
        ('Overdrive Protocol', 'CyberVolt', 'Electropunk', 'Blistering 140 BPM synth hooks and earth-shaking 808s.'),
        ('Neon Blitzkrieg', 'Hyperdrive', 'Synthwave / Bass', 'Pumping kick drums engineered for max PRs in the gym.'),
        ('Apex Predator', 'Titanium Pulse', 'Electro House', 'Aggressive drops, vocal chops, and unrelenting rhythm.'),
        ('Velocity Zero', 'Rave Runners', 'Drum & Bass', 'Rapid-fire breakbeats and roaring reese basslines.')
    ],
    'romantic': [
        ('Velvet Starlight Serenade', 'Luna & The Echoes', 'R&B / Neo-Soul', 'Silky rhodes piano chords with sultry vocal melodies.'),
        ('Slow Dance in the Rain', 'Julian & Amara', 'Acoustic Soul', 'Tender fingerpicking accompanied by gentle cello accompaniment.'),
        ('Echoes of Your Voice', 'Amour Noir', 'Dream Pop', 'Shimmering reverb-soaked guitars whispering sweet devotions.'),
        ('Chasing Midnight Lanterns', 'The Rendezvous', 'Indie Romance', 'Warm harmonium and sweet vocal harmonies.')
    ],
    'focus': [
        ('Quantum Flow State', 'Synapse Lab', 'Binaural Ambient', 'Steady 60 BPM alpha wave frequencies for locked-in cognition.'),
        ('Terminal Monolith', 'Kernel Pulse', 'IDM / Minimal', 'Polyrhythmic clicks and glitch-free synthesizer arpeggios.'),
        ('Deep Study Algorithm', 'The Neuro Architect', 'Ambient Electronica', 'Distraction-free ambient washes that fade into the background.'),
        ('Library at 3 AM', 'Paper & Ivory', 'Modern Classical', 'Minimalist piano notes spaced with thoughtful resonance.')
    ],
    'sad': [
        ('Pieces of Forgotten Skies', 'Alistair Grey', 'Acoustic Melancholy', 'Bare piano chords layered with distant cello mournfulness.'),
        ('Echoes of What We Were', 'Hollow River', 'Indie Folk', 'Fragile vocal delivery over a lonesome fingerpicked parlor guitar.'),
        ('Raindrops Against the Glass', 'Solitude Choir', 'Cinematic Ambient', 'A solemn, cathartic progression for processing heartbreak.'),
        ('Ghost Town Boulevard', 'The Silent Hours', 'Slowcore', 'Reverberant guitars echoing through empty streets.')
    ]
}


def _try_gemini_api(prompt: str, task_type: str = 'mood_dj', mood_slug: str = None) -> dict:
    """
    Attempt to use the Gemini API via google-genai SDK if GEMINI_API_KEY is available.
    Returns parsed dictionary or None if unavailable/fails.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', None) or os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        available_models = ['gemini-flash-lite-latest', 'gemini-flash-latest', 'gemini-2.5-flash-lite']

        if task_type == 'mood_dj':
            sys_inst = (
                "You are Moodify AI DJ, an intelligent emotional music curator. "
                "Analyze the user's feelings and respond strictly with valid JSON with keys: "
                "'mood_slug' (one of: happy, sad, chill, energetic, romantic, focus), "
                "'confidence' (integer between 70 and 99), "
                "'energy_score' (integer between 10 and 100), "
                "'vibe_title' (catchy 2-4 word theme), "
                "'dj_commentary' (2-3 sentences of empathetic, stylish AI DJ commentary directly addressing the user)."
            )
            for model_name in available_models:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=f"Analyze this feeling: {prompt}",
                        config={
                            'system_instruction': sys_inst,
                            'response_mime_type': 'application/json'
                        }
                    )
                    text = response.text or ""
                    text = re.sub(r'```json\s*', '', text)
                    text = re.sub(r'```', '', text).strip()
                    data = json.loads(text)
                    if data.get('mood_slug') in MOOD_KEYWORDS:
                        return data
                except Exception as model_err:
                    print(f"[Moodify AI] Note on {model_name}: {model_err}")
                    continue

        elif task_type == 'generate_song':
            sys_inst = (
                "You are Moodify AI Song Generator. Create a song concept matching the vibe. "
                "Respond strictly with valid JSON with keys: "
                "'title' (song title), 'artist' (famous or virtual artist name), "
                "'genre' (music genre), 'description' (poetic 1-2 sentence description), "
                "'duration' (e.g. '3:24'), 'mood_slug' (one of: happy, sad, chill, energetic, romantic, focus)."
            )
            for model_name in available_models:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=f"Create a song for: '{prompt}'. Target mood: {mood_slug or 'auto'}",
                        config={
                            'system_instruction': sys_inst,
                            'response_mime_type': 'application/json'
                        }
                    )
                    text = response.text or ""
                    text = re.sub(r'```json\s*', '', text)
                    text = re.sub(r'```', '', text).strip()
                    data = json.loads(text)
                    return data
                except Exception as model_err:
                    print(f"[Moodify AI] Note on {model_name}: {model_err}")
                    continue

    except Exception as e:
        # Graceful fallback to local reasoning engine
        print(f"[Moodify AI] Gemini API note: {e}. Falling back to instant local AI reasoning.")
        return None


def analyze_mood_prompt(prompt: str) -> dict:
    """
    Analyzes user's emotional description / text prompt.
    Returns:
    {
        'mood_slug': str,
        'confidence': int (e.g. 92),
        'energy_score': int (e.g. 75),
        'vibe_title': str,
        'dj_commentary': str,
        'matched_keywords': list[str],
    }
    """
    if not prompt or not prompt.strip():
        return {
            'mood_slug': 'chill',
            'confidence': 85,
            'energy_score': 50,
            'vibe_title': 'Serene Equilibrium',
            'dj_commentary': 'Welcome to Moodify! Let me curate an easygoing balance of smooth melodies for you.',
            'matched_keywords': []
        }

    # First attempt Gemini if configured
    gemini_result = _try_gemini_api(prompt, task_type='mood_dj')
    if gemini_result:
        return gemini_result

    # Local Intelligent Semantic NLP Reasoner
    lower_prompt = prompt.lower()
    words = re.findall(r'\b[a-z]{3,}\b', lower_prompt)
    
    scores = {m: 0.0 for m in MOOD_KEYWORDS}
    matched_by_mood = {m: [] for m in MOOD_KEYWORDS}

    for mood_slug, info in MOOD_KEYWORDS.items():
        for kw in info['keywords']:
            # Use whole word or boundary matching to avoid false substring overlaps (e.g. heart in heartbreaking)
            pattern = rf'\b{re.escape(kw)}\b'
            if re.search(pattern, lower_prompt):
                scores[mood_slug] += 3.0
                matched_by_mood[mood_slug].append(kw)
            elif ' ' in kw and kw in lower_prompt:
                scores[mood_slug] += 4.0
                matched_by_mood[mood_slug].append(kw)
            elif kw in words:
                scores[mood_slug] += 2.0
                matched_by_mood[mood_slug].append(kw)

    # Pick highest scoring mood
    best_mood = max(scores, key=scores.get)
    best_score = scores[best_mood]

    # If no specific keyword matched, use context heuristics
    if best_score == 0:
        if any(w in lower_prompt for w in ['night', 'dark', 'alone', 'quiet', 'stars']):
            best_mood = 'chill' if 'alone' not in lower_prompt else 'sad'
        elif any(w in lower_prompt for w in ['fast', 'up', 'run', 'fire', 'hot']):
            best_mood = 'energetic'
        elif any(w in lower_prompt for w in ['kiss', 'heart', 'baby', 'sweet']):
            best_mood = 'romantic'
        elif any(w in lower_prompt for w in ['test', 'project', 'computer', 'learn']):
            best_mood = 'focus'
        elif any(w in lower_prompt for w in ['sun', 'win', 'laugh', 'good']):
            best_mood = 'happy'
        else:
            best_mood = random.choice(['chill', 'happy', 'focus'])
        confidence = random.randint(78, 88)
    else:
        confidence = min(98, int(82 + (best_score * 3.5)))

    info = MOOD_KEYWORDS[best_mood]
    energy = info['default_energy'] + random.randint(-5, 5)
    energy = max(10, min(100, energy))
    
    commentary = random.choice(info['dj_comments'])
    
    vibe_titles = {
        'happy': 'Radiant Euphoria Mix',
        'chill': 'Lofi Sunset Equilibrium',
        'energetic': 'High Voltage Velocity',
        'romantic': 'Velvet Moonlight Reverie',
        'focus': 'Deep Cognition Flow',
        'sad': 'Cathartic Rain Solace'
    }

    return {
        'mood_slug': best_mood,
        'confidence': confidence,
        'energy_score': energy,
        'vibe_title': vibe_titles.get(best_mood, 'Curated Frequency'),
        'dj_commentary': commentary,
        'matched_keywords': matched_by_mood.get(best_mood, [])[:4]
    }


def generate_ai_song_concept(prompt: str = '', mood_slug: str = None) -> dict:
    """
    Generates a real famous song recommendation with authentic vocals and official album artwork.
    Integrates with the Apple iTunes Public Search API for real artist discovery.
    """
    from .itunes_service import search_itunes_tracks, FAMOUS_SONGS_BY_MOOD

    # 1. Determine target mood
    if not mood_slug or mood_slug not in MOOD_ARTWORKS:
        if prompt:
            analysis = analyze_mood_prompt(prompt)
            mood_slug = analysis['mood_slug']
        else:
            mood_slug = random.choice(list(MOOD_ARTWORKS.keys()))

    # 2. If prompt is provided, search iTunes directly for famous artist/song
    if prompt and len(prompt.strip()) >= 2:
        tracks = search_itunes_tracks(prompt.strip(), limit=3)
        if tracks:
            t = tracks[0]
            return {
                'title': t['title'],
                'artist': t['artist'],
                'genre': t.get('genre', 'Pop'),
                'description': f"Official release by {t['artist']}. Curated by Moodify AI for '{prompt}'.",
                'duration': t.get('duration', '3:30'),
                'mood_slug': mood_slug,
                'cover_image_url': t['cover_image_url'],
                'audio_preview_url': t['audio_preview_url'],
                'energy_score': MOOD_KEYWORDS.get(mood_slug, {}).get('default_energy', 50)
            }

    # 3. Otherwise pick a curated world-famous song from the mood catalog
    famous_pool = FAMOUS_SONGS_BY_MOOD.get(mood_slug, FAMOUS_SONGS_BY_MOOD['happy'])
    shuffled_pool = random.sample(famous_pool, len(famous_pool))
    for candidate in shuffled_pool:
        tracks = search_itunes_tracks(candidate['query'], limit=1)
        if tracks and tracks[0].get('audio_preview_url'):
            t = tracks[0]
            return {
                'title': t['title'],
                'artist': t['artist'],
                'genre': t.get('genre', 'Pop'),
                'description': f"Famous {mood_slug.title()} anthem by {t['artist']}. Curated by Moodify AI.",
                'duration': t.get('duration', '3:30'),
                'mood_slug': mood_slug,
                'cover_image_url': t['cover_image_url'],
                'audio_preview_url': t['audio_preview_url'],
                'energy_score': MOOD_KEYWORDS.get(mood_slug, {}).get('default_energy', 50)
            }

    # 4. Graceful offline fallback
    pool = AI_SONG_CREATIONS.get(mood_slug, AI_SONG_CREATIONS['happy'])
    title, artist, genre, desc = random.choice(pool)
    art_pool = MOOD_ARTWORKS.get(mood_slug, MOOD_ARTWORKS['happy'])
    return {
        'title': title,
        'artist': artist,
        'genre': genre,
        'description': desc,
        'duration': f"{random.randint(2, 4)}:{random.randint(10, 59):02d}",
        'mood_slug': mood_slug,
        'cover_image_url': random.choice(art_pool),
        'audio_preview_url': random.choice(AUDIO_PREVIEWS),
        'energy_score': MOOD_KEYWORDS.get(mood_slug, {}).get('default_energy', 50)
    }
