from django.apps import AppConfig


class MusicConfig(AppConfig):
    name = 'music'

    def ready(self):
        # Register signals for automatic MongoDB synchronization
        try:
            import music.signals  # noqa
        except Exception as e:
            print(f"[MusicConfig] Signals setup note: {e}")
