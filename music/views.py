from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.db.models import Q, Count
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

import os
import json
from datetime import datetime
from django.conf import settings
from .models import Mood, Song, Favorite, FAQ, ErrorCode, SupportTicket
from . import ai_assistant
from . import mongo_service
from .itunes_service import search_itunes_track


def get_user_favorite_ids(request):
    """
    Returns the set of song IDs favorited by the visitor.
    Supports anonymous guest users seamlessly via Django session storage,
    as well as registered users if an authenticated session exists.
    """
    fav_ids = set()
    if request.user.is_authenticated:
        fav_ids.update(Favorite.objects.filter(user=request.user).values_list('song_id', flat=True))
    session_favs = request.session.get('favorite_song_ids', [])
    fav_ids.update(session_favs)
    return fav_ids


def home(request):
    """
    Main discovery feed of Moodify.
    Supports:
    - Filtering by mood category (?mood=happy / ?mood=chill etc.)
    - Searching across titles, artists, albums, and moods (?q=search_term)
    - Sorting by newest, title, or popularity
    - Highlighting saved favorites for guests and users alike
    """
    selected_mood_slug = request.GET.get('mood', '').strip()
    search_query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'newest')

    songs = Song.objects.select_related('mood').all()
    selected_mood = None

    if selected_mood_slug:
        selected_mood = get_object_or_404(Mood, slug=selected_mood_slug)
        songs = songs.filter(mood=selected_mood)

    if search_query:
        songs = songs.filter(
            Q(title__icontains=search_query) |
            Q(artist__icontains=search_query) |
            Q(album__icontains=search_query) |
            Q(genre__icontains=search_query) |
            Q(mood__name__icontains=search_query)
        )

    # Sorting options
    if sort_by == 'title':
        songs = songs.order_by('title')
    elif sort_by == 'artist':
        songs = songs.order_by('artist')
    elif sort_by == 'oldest':
        songs = songs.order_by('created_at')
    else:
        # Default: featured first, then newest
        songs = songs.order_by('-is_featured', '-created_at')

    # Get set of song IDs favorited by current visitor
    user_favorite_ids = get_user_favorite_ids(request)

    # Featured track highlight (when no search or mood filter applied)
    featured_song = None
    if not selected_mood_slug and not search_query:
        featured_song = Song.objects.select_related('mood').filter(is_featured=True).first()

    context = {
        'songs': songs,
        'selected_mood': selected_mood,
        'selected_mood_slug': selected_mood_slug,
        'search_query': search_query,
        'sort_by': sort_by,
        'user_favorite_ids': user_favorite_ids,
        'featured_song': featured_song,
        'total_songs_count': songs.count(),
    }
    return render(request, 'music/home.html', context)


def mood_detail(request, slug):
    """
    Dedicated mood category page showcasing all songs associated with that specific mood.
    """
    mood = get_object_or_404(Mood, slug=slug)
    search_query = request.GET.get('q', '').strip()
    
    songs = mood.songs.all()
    if search_query:
        songs = songs.filter(
            Q(title__icontains=search_query) |
            Q(artist__icontains=search_query) |
            Q(album__icontains=search_query)
        )

    user_favorite_ids = get_user_favorite_ids(request)

    context = {
        'mood': mood,
        'songs': songs,
        'search_query': search_query,
        'user_favorite_ids': user_favorite_ids,
    }
    return render(request, 'music/mood_detail.html', context)


def song_detail(request, song_id):
    """
    Single song detail view displaying high-res cover art, full descriptions,
    audio preview player, and recommendations from the same mood.
    """
    song = get_object_or_404(Song.objects.select_related('mood'), id=song_id)
    user_favorite_ids = get_user_favorite_ids(request)
    is_favorited = song.id in user_favorite_ids

    # Similar recommendations from the same mood (excluding current song)
    similar_songs = Song.objects.filter(mood=song.mood).exclude(id=song.id)[:4]

    context = {
        'song': song,
        'is_favorited': is_favorited,
        'similar_songs': similar_songs,
        'user_favorite_ids': user_favorite_ids,
    }
    return render(request, 'music/song_detail.html', context)


@csrf_exempt
@require_POST
def toggle_favorite(request, song_id):
    """
    Toggles favorite status for a song.
    Works seamlessly for guest visitors without login via session storage,
    and syncs to database if user is logged in.
    """
    song = get_object_or_404(Song, id=song_id)
    session_favs = set(request.session.get('favorite_song_ids', []))

    if request.user.is_authenticated:
        fav_obj = Favorite.objects.filter(user=request.user, song=song).first()
        if fav_obj:
            fav_obj.delete()
            is_favorited = False
            session_favs.discard(song.id)
            action_msg = f"Removed '{song.title}' from your Liked Songs."
        else:
            Favorite.objects.create(user=request.user, song=song)
            is_favorited = True
            session_favs.add(song.id)
            action_msg = f"Added '{song.title}' to your Liked Songs!"
    else:
        if song.id in session_favs:
            session_favs.remove(song.id)
            is_favorited = False
            action_msg = f"Removed '{song.title}' from your Liked Songs."
        else:
            session_favs.add(song.id)
            is_favorited = True
            action_msg = f"Added '{song.title}' to your Liked Songs!"

    request.session['favorite_song_ids'] = list(session_favs)
    request.session.modified = True

    # Detect AJAX / Fetch request
    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or 
        request.content_type == 'application/json' or
        request.GET.get('format') == 'json' or
        'application/json' in request.headers.get('accept', '')
    )

    if is_ajax:
        return JsonResponse({
            'status': 'success',
            'song_id': song.id,
            'is_favorited': is_favorited,
            'favorite_count': song.favorite_count + (1 if (is_favorited and not request.user.is_authenticated) else 0),
            'message': action_msg
        })

    messages.success(request, action_msg)
    return redirect(request.META.get('HTTP_REFERER', 'home'))


def favorites_list(request):
    """
    Displays all songs the visitor has saved to their Liked Songs.
    No login or signup required — works seamlessly via session storage and database.
    Includes filtering by mood and search within favorites.
    """
    mood_slug = request.GET.get('mood', '').strip()
    search_query = request.GET.get('q', '').strip()

    fav_ids = get_user_favorite_ids(request)
    songs_query = Song.objects.filter(id__in=fav_ids).select_related('mood')

    if mood_slug:
        songs_query = songs_query.filter(mood__slug=mood_slug)

    if search_query:
        songs_query = songs_query.filter(
            Q(title__icontains=search_query) |
            Q(artist__icontains=search_query) |
            Q(album__icontains=search_query)
        )

    songs = list(songs_query)
    user_favorite_ids = set([s.id for s in songs])

    context = {
        'songs': songs,
        'mood_slug': mood_slug,
        'search_query': search_query,
        'user_favorite_ids': user_favorite_ids,
        'total_favorites': len(songs),
    }
    return render(request, 'music/favorites.html', context)


# ============================================================================
# USER AUTHENTICATION (MongoDB Users Collection)
# ============================================================================

def signup_view(request):
    """
    User registration view.
    Stores account credentials in MongoDB 'users' collection, records login activity,
    and logs in to establish session.
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not username or not email or not password:
            messages.error(request, "Please fill in all required fields.")
        elif len(username) < 3:
            messages.error(request, "Username must be at least 3 characters long.")
        elif password != confirm_password:
            messages.error(request, "Passwords do not match. Please try again.")
        elif len(password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
        else:
            success, result = mongo_service.create_mongo_user(username, email, password)
            if success:
                from django.contrib.auth.models import User
                django_user, _ = User.objects.get_or_create(username=username.lower(), defaults={'email': email.lower()})
                django_user.set_password(password)
                django_user.save()
                login(request, django_user)
                messages.success(request, f"Welcome to Moodify, {username}! Your account has been registered and saved to MongoDB.")
                return redirect('home')
            else:
                messages.error(request, result)

    return render(request, 'music/signup.html')


def login_view(request):
    """
    User authentication view.
    Validates credentials against MongoDB 'users' collection, updates last_login,
    records login activity in 'login_history', and establishes session.
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username_or_email = request.POST.get('username_or_email', '').strip()
        password = request.POST.get('password', '')

        client_ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', '127.0.0.1')
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')

        if not username_or_email or not password:
            messages.error(request, "Please enter your username/email and password.")
        else:
            mongo_user = mongo_service.authenticate_mongo_user(username_or_email, password)
            if mongo_user:
                from django.contrib.auth.models import User
                u_name = mongo_user.get('username', username_or_email).lower()
                u_email = mongo_user.get('email', '')
                django_user, _ = User.objects.get_or_create(username=u_name, defaults={'email': u_email})
                login(request, django_user)

                mongo_service.record_login_activity(
                    username=u_name,
                    email=u_email,
                    success=True,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    details="Successful password authentication via MongoDB"
                )

                messages.success(request, f"Welcome back, {mongo_user.get('display_name', u_name)}!")
                next_url = request.GET.get('next') or request.POST.get('next') or 'home'
                return redirect(next_url)
            else:
                from django.contrib.auth import authenticate as django_auth
                django_user = django_auth(request, username=username_or_email.lower(), password=password)
                if django_user is not None:
                    login(request, django_user)
                    mongo_service.sync_user_to_mongo(django_user, raw_password=password)
                    mongo_service.record_login_activity(
                        username=django_user.username,
                        email=django_user.email,
                        success=True,
                        ip_address=client_ip,
                        user_agent=user_agent,
                        details="Successful authentication (auto-synced to MongoDB)"
                    )
                    messages.success(request, f"Welcome back, {django_user.username}!")
                    next_url = request.GET.get('next') or request.POST.get('next') or 'home'
                    return redirect(next_url)
                else:
                    mongo_service.record_login_activity(
                        username=username_or_email,
                        email='',
                        success=False,
                        ip_address=client_ip,
                        user_agent=user_agent,
                        details="Failed login attempt - invalid credentials"
                    )
                    messages.error(request, "Invalid username/email or password. Please try again.")

    return render(request, 'music/login.html')


def logout_view(request):
    """
    Logs out the user and clears session.
    """
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('home')


@csrf_exempt
@require_POST
def ai_mood_dj(request):
    """
    AI Mood DJ endpoint:
    Analyzes natural language prompts (e.g. 'exhausted after finals', 'hyped for gym session')
    and returns detected mood, confidence percentage, energy level, DJ commentary,
    and a curated list of matching songs.
    No login required.
    """
    from .ai_service import analyze_mood_prompt
    
    prompt = request.POST.get('prompt', '').strip()
    if not prompt:
        # Check JSON body if posted via fetch JSON
        try:
            import json
            body = json.loads(request.body)
            prompt = body.get('prompt', '').strip()
        except Exception:
            prompt = ''

    analysis = analyze_mood_prompt(prompt)
    mood = Mood.objects.filter(slug=analysis['mood_slug']).first()
    if not mood:
        mood = Mood.objects.first()

    # Fetch matching songs from database
    matching_songs = Song.objects.filter(mood=mood).order_by('-is_featured', '-created_at')[:8]
    
    songs_data = []
    for s in matching_songs:
        songs_data.append({
            'id': s.id,
            'title': s.title,
            'artist': s.artist,
            'cover_image_url': s.cover_image_url,
            'audio_preview_url': s.audio_preview_url,
            'duration': s.duration,
            'mood_name': mood.name,
            'detail_url': f"/song/{s.id}/"
        })

    response_payload = {
        'success': True,
        'prompt': prompt,
        'mood_slug': mood.slug,
        'mood_name': mood.name,
        'mood_gradient': mood.gradient,
        'mood_accent': mood.accent_color,
        'confidence': analysis.get('confidence', 90),
        'energy_score': analysis.get('energy_score', 50),
        'vibe_title': analysis.get('vibe_title', f"{mood.name} Vibe"),
        'dj_commentary': analysis.get('dj_commentary', f"Here is your personalized {mood.name} curation!"),
        'matched_keywords': analysis.get('matched_keywords', []),
        'songs': songs_data,
        'total_found': len(songs_data)
    }

    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or 
        request.content_type == 'application/json' or
        'application/json' in request.headers.get('accept', '')
    )

    if is_ajax:
        return JsonResponse(response_payload)

    # Standard form POST fallback: redirect to mood with flash message
    messages.success(request, f"✨ Moodify AI DJ tuned your frequency to {mood.name}: {analysis.get('dj_commentary')}")
    return redirect(f"/#ai-dj-results?mood={mood.slug}")


@csrf_exempt
@require_POST
def ai_generate_song(request):
    """
    AI Song Studio:
    Generates an original song recommendation matched to user's vibe prompt,
    assigns curated artwork, duration, and audio preview, and saves it to the library.
    No login required.
    """
    from .ai_service import generate_ai_song_concept
    
    prompt = request.POST.get('prompt', '').strip()
    mood_id = request.POST.get('mood_id')
    
    target_mood = None
    if mood_id:
        target_mood = Mood.objects.filter(id=mood_id).first()

    song_concept = generate_ai_song_concept(
        prompt=prompt, 
        mood_slug=target_mood.slug if target_mood else None
    )

    # Resolve final mood
    if not target_mood:
        target_mood = Mood.objects.filter(slug=song_concept['mood_slug']).first() or Mood.objects.first()

    custom_title = request.POST.get('title', '').strip()
    custom_artist = request.POST.get('artist', '').strip()

    cover_url = song_concept['cover_image_url']
    audio_url = song_concept['audio_preview_url']
    genre = song_concept.get('genre', 'Pop')
    duration = song_concept.get('duration', '3:30')

    # If user provided a specific title or artist, search iTunes for real track
    if custom_title or custom_artist:
        from .itunes_service import fetch_itunes_track
        query = f"{custom_artist} {custom_title}".strip()
        itunes_info = fetch_itunes_track(query)
        if itunes_info:
            custom_title = itunes_info['title']
            custom_artist = itunes_info['artist']
            cover_url = itunes_info['cover_image_url']
            audio_url = itunes_info['audio_preview_url'] or audio_url
            genre = itunes_info['genre']
            duration = itunes_info['duration']
    else:
        custom_title = song_concept['title']
        custom_artist = song_concept['artist']

    # Create the AI song in database
    new_song = Song.objects.create(
        title=custom_title,
        artist=custom_artist,
        mood=target_mood,
        genre=genre,
        duration=duration,
        cover_image_url=cover_url,
        audio_preview_url=audio_url,
        description=song_concept.get('description', f"Curated by Moodify AI for vibe: '{prompt}'."),
        is_ai_generated=True,
        ai_prompt=prompt,
        energy_score=song_concept.get('energy_score', 50)
    )

    # Cache audio stream locally to ensure 100% reliable browser playback with audio/mp4 MIME type
    if audio_url and audio_url.startswith('http'):
        try:
            from pathlib import Path
            import urllib.request
            from django.conf import settings
            media_dir = Path(settings.MEDIA_ROOT) / 'audio_previews'
            media_dir.mkdir(parents=True, exist_ok=True)
            local_file = media_dir / f"{new_song.id}.m4a"
            req = urllib.request.Request(audio_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                local_file.write_bytes(resp.read())
            new_song.audio_preview_url = f"/media/audio_previews/{new_song.id}.m4a"
            new_song.save(update_fields=['audio_preview_url'])
        except Exception:
            pass

    messages.success(request, f"✨ Moodify AI added '{new_song.title}' by {new_song.artist} in {target_mood.name}!")
    
    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or 
        request.content_type == 'application/json' or
        'application/json' in request.headers.get('accept', '')
    )
    if is_ajax:
        return JsonResponse({
            'success': True,
            'song_id': new_song.id,
            'title': new_song.title,
            'artist': new_song.artist,
            'mood': target_mood.name,
            'cover_image_url': new_song.cover_image_url,
            'detail_url': f"/song/{new_song.id}/"
        })

    return redirect('song_detail', song_id=new_song.id)


# ============================================================================
# FINAL ASSESSMENT VIEWS: FAQ, Support, Health Check, AI Assistant, Custom Errors
# ============================================================================

def faq_view(request):
    """
    Page 2: Frequently Asked Questions and Error Code Reference.
    Displays:
    - Minimum 10 FAQs stored in the SQL database.
    - Minimum 8 Error Codes (400, 401, 403, 404, 429, 500, 503, 488).
    - Category filtering & search.
    """
    search_q = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '').strip()

    faqs = FAQ.objects.all().order_by('order', 'id')
    error_codes = ErrorCode.objects.all().order_by('code')

    if selected_category and selected_category != 'All':
        faqs = faqs.filter(category=selected_category)

    if search_q:
        # 1. Exact phrase match first
        exact_faq_q = (
            Q(question__icontains=search_q) |
            Q(answer__icontains=search_q) |
            Q(category__icontains=search_q)
        )
        exact_err_q = (
            Q(code__icontains=search_q) |
            Q(name__icontains=search_q) |
            Q(meaning__icontains=search_q) |
            Q(common_causes__icontains=search_q)
        )

        # 2. Extract meaningful search tokens (ignoring conversational stop words)
        stop_words = {'how', 'to', 'the', 'a', 'an', 'in', 'on', 'do', 'i', 'can', 'is', 'what', 'for', 'of', 'and', 'or', 'my', 'me', 'it', 'tell', 'about', 'with', 'by', 'does'}
        tokens = [w for w in search_q.lower().split() if w not in stop_words]
        if not tokens:
            tokens = search_q.lower().split()

        # Match where ALL non-stop tokens are present (highest relevance)
        all_tokens_faq_q = Q()
        for token in tokens:
            all_tokens_faq_q &= (
                Q(question__icontains=token) |
                Q(answer__icontains=token) |
                Q(category__icontains=token)
            )

        # Match where ANY non-stop token is present (broader recall)
        any_tokens_faq_q = Q()
        for token in tokens:
            any_tokens_faq_q |= (
                Q(question__icontains=token) |
                Q(answer__icontains=token) |
                Q(category__icontains=token)
            )

        primary_faqs = faqs.filter(exact_faq_q | all_tokens_faq_q).distinct()
        if primary_faqs.exists():
            faqs = primary_faqs
        else:
            faqs = faqs.filter(any_tokens_faq_q).distinct()

        # Error codes matching
        any_tokens_err_q = Q()
        for token in tokens:
            any_tokens_err_q |= (
                Q(code__icontains=token) |
                Q(name__icontains=token) |
                Q(meaning__icontains=token) |
                Q(common_causes__icontains=token)
            )

        primary_errs = error_codes.filter(exact_err_q).distinct()
        if primary_errs.exists():
            error_codes = primary_errs
        else:
            error_codes = error_codes.filter(any_tokens_err_q).distinct()

    categories = FAQ.objects.values_list('category', flat=True).distinct()

    context = {
        'faqs': faqs,
        'error_codes': error_codes,
        'categories': categories,
        'selected_category': selected_category,
        'search_q': search_q,
        'faq_count': faqs.count(),
        'error_code_count': error_codes.count(),
    }
    return render(request, 'music/faq.html', context)


def support_view(request):
    """
    Page 3: Support Ticket Center.
    Stores and displays customer support tickets in the SQL database.
    Users can submit new tickets or check existing ticket status.
    """
    search_ticket = request.GET.get('ticket_number', '').strip()
    searched_ticket = None

    if search_ticket:
        searched_ticket = SupportTicket.objects.filter(ticket_number__iexact=search_ticket).first()

    if request.method == 'POST':
        user_name = request.POST.get('user_name', 'Anonymous User').strip() or 'Anonymous User'
        user_email = request.POST.get('user_email', '').strip()
        subject = request.POST.get('subject', '').strip()
        category = request.POST.get('category', 'General Issue')
        priority = request.POST.get('priority', 'Medium')
        description = request.POST.get('description', '').strip()

        if user_email and subject and description:
            ticket = SupportTicket.objects.create(
                user_name=user_name,
                user_email=user_email,
                subject=subject,
                category=category,
                priority=priority,
                description=description,
                status='Open'
            )
            # Sync ticket to MongoDB collection 'support_tickets'
            mongo_service.record_support_ticket(ticket)

            messages.success(request, f"Support Ticket {ticket.ticket_number} created successfully! Our engineering team will review it shortly.")
            return redirect(f"/support/?ticket_number={ticket.ticket_number}")
        else:
            messages.error(request, "Please fill in your email, subject, and issue description.")

    recent_tickets = SupportTicket.objects.all().order_by('-created_at')[:15]
    total_tickets = SupportTicket.objects.count()
    open_tickets = SupportTicket.objects.filter(status='Open').count()
    resolved_tickets = SupportTicket.objects.filter(status='Resolved').count()

    context = {
        'recent_tickets': recent_tickets,
        'searched_ticket': searched_ticket,
        'search_ticket_query': search_ticket,
        'total_tickets': total_tickets,
        'open_tickets': open_tickets,
        'resolved_tickets': resolved_tickets,
    }
    return render(request, 'music/support.html', context)


@csrf_exempt
@require_POST
def api_chat(request):
    """
    AI Assistant Endpoint.
    - Answers questions grounded in the SQL FAQ database.
    - Explains error codes (400, 401, 403, 404, 429, 500, 503, 488).
    - Can create a support ticket in SQL when unable to answer or upon request.
    - Logs chat interactions into MongoDB.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    message = data.get('message', '').strip()
    session_id = data.get('session_id', '').strip() or request.session.session_key or 'guest-session'
    user_email = data.get('email', '').strip()
    auto_create_ticket = data.get('auto_create_ticket', False)

    if not message:
        return JsonResponse({'success': False, 'error': 'Message cannot be empty'}, status=400)

    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '127.0.0.1'))
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    result = ai_assistant.process_chat_query(
        user_message=message,
        session_id=session_id,
        client_ip=client_ip,
        auto_create_ticket=bool(auto_create_ticket),
        user_email=user_email
    )

    return JsonResponse({
        'success': True,
        'session_id': session_id,
        'answer': result.get('answer', ''),
        'can_answer': result.get('can_answer', True),
        'error_code': result.get('error_code'),
        'faq_ids': result.get('faq_ids', []),
        'suggested_ticket': result.get('suggested_ticket'),
        'ticket_created': result.get('ticket_created'),
        'mongo_log_id': result.get('mongo_log_id'),
    })


@csrf_exempt
@require_POST
def api_chat_feedback(request):
    """
    Saves user rating and feedback into MongoDB.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    session_id = data.get('session_id', 'guest-session')
    message_id = data.get('message_id', '')
    rating = int(data.get('rating', 5))
    feedback_type = data.get('feedback_type', 'helpful')
    comments = data.get('comments', '')
    email = data.get('email', '')

    feedback_id = mongo_service.record_chat_feedback(
        session_id=session_id,
        message_id=message_id,
        rating=rating,
        feedback_type=feedback_type,
        comments=comments,
        user_email=email
    )

    return JsonResponse({
        'success': True,
        'feedback_id': feedback_id,
        'message': 'Thank you! Your feedback has been stored in MongoDB.'
    })


@csrf_exempt
@require_POST
def api_create_ticket(request):
    """
    Direct endpoint for creating a Support Ticket in SQL.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    subject = data.get('subject', '').strip()
    description = data.get('description', '').strip()
    user_email = data.get('user_email', '').strip()
    user_name = data.get('user_name', 'Anonymous User').strip() or 'Anonymous User'
    category = data.get('category', 'AI Assistant Inquiry')
    priority = data.get('priority', 'Medium')

    if not subject or not description or not user_email:
        return JsonResponse({'success': False, 'error': 'Subject, description, and user_email are required'}, status=400)

    ticket = SupportTicket.objects.create(
        user_name=user_name,
        user_email=user_email,
        subject=subject,
        category=category,
        priority=priority,
        description=description,
        status='Open',
        ai_generated=data.get('ai_generated', False)
    )
    # Sync ticket to MongoDB collection 'support_tickets'
    mongo_service.record_support_ticket(ticket)

    return JsonResponse({
        'success': True,
        'ticket_number': ticket.ticket_number,
        'status': ticket.status,
        'created_at': ticket.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
        'subject': ticket.subject
    })


def health_check_view(request):
    """
    System Health Check Dashboard & Endpoint.
    Fulfills assessment requirement:
    - Request logging inspection
    - Health check metrics
    - Third-party API check with timeout and fallback
    """
    import time
    from pathlib import Path

    # 1. SQL Database Health Check
    sql_start = time.perf_counter()
    sql_status = "healthy"
    sql_error = None
    try:
        faq_count = FAQ.objects.count()
        error_count = ErrorCode.objects.count()
        ticket_count = SupportTicket.objects.count()
        song_count = Song.objects.count()
        sql_latency_ms = (time.perf_counter() - sql_start) * 1000.0
    except Exception as e:
        sql_status = "unhealthy"
        sql_error = str(e)
        sql_latency_ms = (time.perf_counter() - sql_start) * 1000.0
        faq_count, error_count, ticket_count, song_count = 0, 0, 0, 0

    # 2. MongoDB Health Check (via mongo_service)
    mongo_stats = mongo_service.get_mongo_health_stats()

    # 3. Third-party API (Apple iTunes API with strict 5s timeout & fallback)
    tp_start = time.perf_counter()
    tp_status = "healthy"
    tp_fallback_used = False
    try:
        tp_res = search_itunes_track("Coldplay", limit=1, timeout=5.0)
        tp_latency_ms = (time.perf_counter() - tp_start) * 1000.0
        if not tp_res:
            tp_fallback_used = True
    except Exception as e:
        tp_status = "degraded"
        tp_fallback_used = True
        tp_latency_ms = (time.perf_counter() - tp_start) * 1000.0

    # 4. Google Gemini API status
    gemini_key = getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
    gemini_status = "configured" if gemini_key else "missing_key"

    # 5. Request Logging Inspection
    logs_file = Path(settings.BASE_DIR) / 'logs' / 'requests.log'
    total_logged_requests = 0
    recent_logs = []
    if logs_file.exists():
        try:
            with open(logs_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                total_logged_requests = len(lines)
                recent_logs = [line.strip() for line in lines[-10:]][::-1]
        except Exception:
            pass

    health_data = {
        'status': 'HEALTHY' if sql_status == 'healthy' else 'DEGRADED',
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'components': {
            'sql_database': {
                'engine': 'SQLite3 (Django ORM)',
                'status': sql_status,
                'latency_ms': round(sql_latency_ms, 2),
                'faq_records': faq_count,
                'error_code_records': error_count,
                'support_tickets': ticket_count,
                'total_songs': song_count,
                'error': sql_error,
            },
            'mongodb': mongo_stats,
            'third_party_api': {
                'name': 'Apple iTunes Search API',
                'status': tp_status,
                'timeout_seconds': 5.0,
                'fallback_enabled': True,
                'fallback_used': tp_fallback_used,
                'latency_ms': round(tp_latency_ms, 2),
            },
            'ai_service': {
                'provider': 'Google Gemini API (gemini-flash-lite-latest)',
                'status': gemini_status,
                'api_key_configured': bool(gemini_key),
                'fallback_rule_engine': 'Active',
            },
            'request_logging': {
                'middleware': 'music.middleware.RequestLoggingMiddleware',
                'log_file': 'logs/requests.log',
                'total_requests_recorded': total_logged_requests,
                'recent_logs': recent_logs,
            }
        }
    }

    if request.GET.get('format') == 'json' or 'application/json' in request.headers.get('accept', ''):
        return JsonResponse(health_data)

    return render(request, 'music/health.html', {'health': health_data})


# ============================================================================
# CUSTOM ERROR HANDLERS (404 and 500) WITH "ASK THE ASSISTANT" INTEGRATION
# ============================================================================

def custom_404_view(request, exception=None):
    """
    Custom 404 Page Not Found error handler with 'Ask the assistant' integration.
    """
    return render(request, '404.html', {'path': request.path}, status=404)


def custom_500_view(request):
    """
    Custom 500 Internal Server Error handler with 'Ask the assistant' integration.
    """
    return render(request, '500.html', {}, status=500)


def test_404_view(request):
    """
    Test route to demonstrate custom 404 template.
    """
    return render(request, '404.html', {'path': '/non-existent-page-demo/'}, status=404)


def test_500_view(request):
    """
    Test route to demonstrate custom 500 template.
    """
    return render(request, '500.html', {}, status=500)



