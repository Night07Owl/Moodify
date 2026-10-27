from .models import Mood

def moods_processor(request):
    """
    Context processor that makes all mood categories available to every template
    in the Moodify platform (e.g. for header nav, quick mood pills, sidebar).
    """
    try:
        moods = Mood.objects.all().order_by('order', 'name')
    except Exception:
        # Handles scenario during initial migrations before table exists
        moods = []
    return {
        'all_moods': moods
    }
