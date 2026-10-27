from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from music.models import Mood, Song, Favorite, FAQ, ErrorCode, SupportTicket
import json

class MoodifyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com', 
            password='Password123!'
        )

        # Create two test moods
        self.happy_mood = Mood.objects.create(
            name='Happy',
            tagline='Feel good vibes',
            description='Uplifting music',
            icon='smile',
            gradient='linear-gradient(135deg, #f59e0b, #ec4899)',
            accent_color='#f59e0b',
            order=1
        )

        self.chill_mood = Mood.objects.create(
            name='Chill',
            tagline='Relaxing beats',
            description='Calm sounds',
            icon='coffee',
            gradient='linear-gradient(135deg, #10b981, #06b6d4)',
            accent_color='#10b981',
            order=2
        )

        self.energetic_mood = Mood.objects.create(
            name='Energetic',
            tagline='High voltage',
            description='Workout fuel',
            icon='zap',
            gradient='linear-gradient(135deg, #ef4444, #f97316)',
            accent_color='#ef4444',
            order=3
        )

        self.romantic_mood = Mood.objects.create(
            name='Romantic',
            tagline='Love & passion',
            description='Sweet serenades',
            icon='heart',
            gradient='linear-gradient(135deg, #ec4899, #f43f5e)',
            accent_color='#ec4899',
            order=4
        )

        self.focus_mood = Mood.objects.create(
            name='Focus',
            tagline='Deep study',
            description='Binaural rhythms',
            icon='brain',
            gradient='linear-gradient(135deg, #6366f1, #8b5cf6)',
            accent_color='#6366f1',
            order=5
        )

        self.sad_mood = Mood.objects.create(
            name='Sad',
            tagline='Cathartic comfort',
            description='Acoustic solace',
            icon='cloud-rain',
            gradient='linear-gradient(135deg, #64748b, #475569)',
            accent_color='#64748b',
            order=6
        )

        # Create test songs
        self.song1 = Song.objects.create(
            title='Happy Day',
            artist='Sunshine Band',
            mood=self.happy_mood,
            duration='3:15',
            cover_image_url='https://example.com/art1.jpg',
            spotify_url='https://open.spotify.com/search/Happy%20Day',
            youtube_url='https://youtube.com/results?search_query=Happy+Day',
            audio_preview_url='https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3'
        )

        self.song2 = Song.objects.create(
            title='Chill Breeze',
            artist='Lofi Master',
            mood=self.chill_mood,
            duration='2:45',
            cover_image_url='https://example.com/art2.jpg',
            spotify_url='https://open.spotify.com/search/Chill%20Breeze',
            youtube_url='https://youtube.com/results?search_query=Chill+Breeze',
            audio_preview_url='https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3'
        )

    def test_homepage_loads(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Moodify')
        self.assertContains(response, 'Happy Day')
        self.assertContains(response, 'Chill Breeze')

    def test_mood_filter(self):
        response = self.client.get(reverse('home'), {'mood': 'chill'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chill Breeze')
        self.assertNotContains(response, 'Happy Day')

    def test_search_filter(self):
        response = self.client.get(reverse('home'), {'q': 'Sunshine'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Happy Day')
        self.assertNotContains(response, 'Chill Breeze')

    def test_mood_detail_page(self):
        response = self.client.get(reverse('mood_detail', kwargs={'slug': 'happy'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Happy Mix')
        self.assertContains(response, 'Happy Day')


    def test_song_detail_page(self):
        response = self.client.get(reverse('song_detail', kwargs={'song_id': self.song1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Happy Day')
        self.assertContains(response, 'Sunshine Band')
        self.assertContains(response, 'AI Acoustic &amp; Mood DNA')

    def test_toggle_favorite_ajax(self):
        # Test anonymous visitor toggling favorite via session
        response = self.client.post(
            reverse('toggle_favorite', kwargs={'song_id': self.song1.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['is_favorited'])
        self.assertIn(self.song1.id, self.client.session.get('favorite_song_ids', []))

        # Unfavorite the song
        response = self.client.post(
            reverse('toggle_favorite', kwargs={'song_id': self.song1.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['is_favorited'])
        self.assertNotIn(self.song1.id, self.client.session.get('favorite_song_ids', []))

    def test_favorites_page_anonymous_access(self):
        # Anonymous user can access favorites page directly with zero login required
        response = self.client.get(reverse('favorites_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Liked Songs')

        # When a song is favorited in session, it appears on the page
        session = self.client.session
        session['favorite_song_ids'] = [self.song1.id]
        session.save()
        response = self.client.get(reverse('favorites_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Happy Day')

    def test_ai_mood_dj_analysis(self):
        # Test natural language emotion query via AJAX
        response = self.client.post(
            reverse('ai_mood_dj'),
            data={'prompt': 'I am super pumped and energized for a heavy workout at the gym!'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['mood_slug'], 'energetic')
        self.assertGreaterEqual(data['confidence'], 70)
        self.assertTrue(len(data['dj_commentary']) > 0)

    def test_ai_generate_song(self):
        # No login required for AI Song Studio
        response = self.client.post(
            reverse('ai_generate_song'),
            data={
                'prompt': 'Dreamy ambient chillwave for a quiet rainy evening',
                'mood_id': self.chill_mood.id,
                'title': 'Velvet Raindrops',
                'artist': 'Cyber Lofi'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['title'], 'Velvet Raindrops')
        self.assertTrue(Song.objects.filter(title='Velvet Raindrops', is_ai_generated=True).exists())

    def test_faq_and_error_codes_page(self):
        # Create FAQ and ErrorCode
        FAQ.objects.create(question="How does MoodMusic work?", answer="It plays music.", category="General", order=1)
        ErrorCode.objects.create(code=488, name="Audio Stream Unavailable", is_site_specific=True, meaning="Stream offline", common_causes="CDN issue", troubleshooting_steps="Retry")

        response = self.client.get(reverse('faq'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "How does MoodMusic work?")
        self.assertContains(response, "488")
        self.assertContains(response, "Audio Stream Unavailable")

    def test_support_ticket_creation(self):
        response = self.client.post(
            reverse('support'),
            data={
                'user_name': 'Test Student',
                'user_email': 'student@school.edu',
                'subject': 'Stream audio bug',
                'category': 'Audio Playback Issue',
                'priority': 'High',
                'description': 'Playback stops at second 15'
            }
        )
        self.assertEqual(response.status_code, 302)
        ticket = SupportTicket.objects.filter(user_email='student@school.edu').first()
        self.assertIsNotNone(ticket)
        self.assertTrue(ticket.ticket_number.startswith('TCK-'))

    def test_health_check_json_endpoint(self):
        response = self.client.get(reverse('health_check') + '?format=json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('status', data)
        self.assertIn('components', data)
        self.assertIn('sql_database', data['components'])
        self.assertIn('mongodb', data['components'])
        self.assertIn('third_party_api', data['components'])

    def test_ai_chat_explains_error_code(self):
        ErrorCode.objects.create(code=404, name="Not Found", meaning="Resource missing", common_causes="Bad URL", troubleshooting_steps="Check address")
        response = self.client.post(
            reverse('api_chat'),
            data=json.dumps({'message': 'Explain error 404'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['error_code'], 404)
        self.assertTrue(data['can_answer'])

    def test_ai_chat_feedback_endpoint(self):
        response = self.client.post(
            reverse('api_chat_feedback'),
            data=json.dumps({
                'session_id': 'test-session',
                'message_id': 'msg-1',
                'rating': 5,
                'feedback_type': 'helpful'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

    def test_custom_error_pages(self):
        r_404 = self.client.get(reverse('test_404'))
        self.assertEqual(r_404.status_code, 404)
        self.assertContains(r_404, "Ask the Assistant", status_code=404)

        r_500 = self.client.get(reverse('test_500'))
        self.assertEqual(r_500.status_code, 500)
        self.assertContains(r_500, "Ask the Assistant", status_code=500)

