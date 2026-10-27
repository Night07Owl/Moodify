/**
 * Moodify - AI-Integrated Web Player Logic
 * - Real-time HTML5 Audio Playback (Scrubber, Volume, Shuffle, Repeat)
 * - Moodify AI DJ & Natural Language Emotion Detection
 * - Moodify AI Song Studio Modal
 * - Instant AJAX Favorite Toggling
 */

document.addEventListener('DOMContentLoaded', () => {
  initMoodifyPlayer();
  initFavoriteButtons();
  initAiDj();
  initAiStudioModal();
  initSearchKeyboardShortcut();
});

/* ==========================================================================
   1. Moodify Bottom Audio Player Controller
   ========================================================================== */
function initMoodifyPlayer() {
  const audio = new Audio();
  audio.preload = 'none';

  const playBtn = document.getElementById('spPlayToggle');
  const playIcon = playBtn ? playBtn.querySelector('i') : null;
  const prevBtn = document.getElementById('spPrevBtn');
  const nextBtn = document.getElementById('spNextBtn');
  const shuffleBtn = document.getElementById('spShuffleBtn');
  const repeatBtn = document.getElementById('spRepeatBtn');

  const scrubberTrack = document.getElementById('spScrubberTrack');
  const scrubberFill = document.getElementById('spScrubberFill');
  const curTimeEl = document.getElementById('spCurrentTime');
  const durTimeEl = document.getElementById('spDuration');
  const volumeSlider = document.getElementById('spVolumeSlider');

  const playerImg = document.getElementById('spPlayerImg');
  const playerTitle = document.getElementById('spPlayerTitle');
  const playerArtist = document.getElementById('spPlayerArtist');
  const playerFavBtn = document.getElementById('spPlayerFavBtn');
  const jumpToAiDjBtn = document.getElementById('jumpToAiDjBtn');

  let currentSongIndex = 0;
  let playlist = [];
  let isShuffle = false;
  let isRepeat = false;

  // Scan current page for playable songs
  window.scanPageSongs = function() {
    const cards = document.querySelectorAll('[data-song-id]');
    playlist = [];
    cards.forEach((card, idx) => {
      playlist.push({
        id: card.dataset.songId,
        title: card.dataset.songTitle,
        artist: card.dataset.songArtist,
        coverUrl: card.dataset.songCover,
        audioUrl: card.dataset.songAudio,
        index: idx
      });
    });
  };
  window.scanPageSongs();

  let currentTrackId = null;

  function formatTime(seconds) {
    if (isNaN(seconds)) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  // Helper to sync all play trigger icons on the page
  function updatePagePlayIcons(isPlaying) {
    document.querySelectorAll('.sp-play-trigger').forEach(btn => {
      const card = btn.closest('[data-song-id]') || btn;
      const icon = btn.querySelector('i');
      if (!icon) return;

      if (isPlaying && card && String(card.dataset.songId) === String(currentTrackId)) {
        icon.className = 'fa-solid fa-pause';
      } else {
        icon.className = 'fa-solid fa-play';
      }
    });
  }

  // Load and play a track
  window.loadAndPlayTrack = function(track, startAudio = true) {
    if (!track) return;
    currentTrackId = String(track.id);

    // Update bottom player UI
    if (playerImg) playerImg.src = track.coverUrl || 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=100&auto=format&fit=crop&q=80';
    if (playerTitle) {
      playerTitle.textContent = track.title || 'Unknown Track';
      playerTitle.href = `/song/${track.id}/`;
    }
    if (playerArtist) playerArtist.textContent = track.artist || 'Unknown Artist';
    
    if (playerFavBtn) {
      playerFavBtn.dataset.songId = track.id;
      playerFavBtn.dataset.url = `/song/${track.id}/favorite/`;
      const isCardFav = document.querySelector(`.fav-toggle-btn[data-song-id="${track.id}"]`)?.classList.contains('favorited');
      if (isCardFav) {
        playerFavBtn.classList.add('favorited');
        playerFavBtn.querySelector('i').className = 'fa-solid fa-heart';
      } else {
        playerFavBtn.classList.remove('favorited');
        playerFavBtn.querySelector('i').className = 'fa-regular fa-heart';
      }
    }

    // Play preview audio
    if (track.audioUrl) {
      audio.src = track.audioUrl;
      audio.load();
      if (startAudio) {
        const playPromise = audio.play();
        if (playPromise !== undefined) {
          playPromise.catch(e => {
            console.warn('Playback error or blocked by autoplay policy:', e);
            updatePagePlayIcons(false);
          });
        }
      }
    }
  };

  // Play button toggle on bottom player
  if (playBtn) {
    playBtn.addEventListener('click', () => {
      if (!audio.src && playlist.length > 0) {
        loadAndPlayTrack(playlist[0], true);
        return;
      }
      if (audio.paused) {
        audio.play().catch(e => console.warn('Play error:', e));
      } else {
        audio.pause();
      }
    });
  }

  // Next & Previous buttons
  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      window.scanPageSongs();
      if (playlist.length === 0) return;
      if (isShuffle) {
        currentSongIndex = Math.floor(Math.random() * playlist.length);
      } else {
        currentSongIndex = (currentSongIndex + 1) % playlist.length;
      }
      loadAndPlayTrack(playlist[currentSongIndex], true);
    });
  }

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      window.scanPageSongs();
      if (playlist.length === 0) return;
      currentSongIndex = (currentSongIndex - 1 + playlist.length) % playlist.length;
      loadAndPlayTrack(playlist[currentSongIndex], true);
    });
  }

  if (shuffleBtn) {
    shuffleBtn.addEventListener('click', () => {
      isShuffle = !isShuffle;
      shuffleBtn.classList.toggle('active', isShuffle);
    });
  }

  if (repeatBtn) {
    repeatBtn.addEventListener('click', () => {
      isRepeat = !isRepeat;
      repeatBtn.classList.toggle('active', isRepeat);
    });
  }

  // Audio playback state events
  audio.addEventListener('play', () => {
    if (playIcon) playIcon.className = 'fa-solid fa-pause';
    updatePagePlayIcons(true);
  });

  audio.addEventListener('pause', () => {
    if (playIcon) playIcon.className = 'fa-solid fa-play';
    updatePagePlayIcons(false);
  });

  audio.addEventListener('error', (e) => {
    console.error('Audio stream playback error:', audio.error);
    if (playIcon) playIcon.className = 'fa-solid fa-play';
    updatePagePlayIcons(false);
  });

  audio.addEventListener('timeupdate', () => {
    if (audio.duration) {
      const pct = (audio.currentTime / audio.duration) * 100;
      if (scrubberFill) scrubberFill.style.width = `${pct}%`;
      if (curTimeEl) curTimeEl.textContent = formatTime(audio.currentTime);
      if (durTimeEl) durTimeEl.textContent = formatTime(audio.duration);
    }
  });

  audio.addEventListener('ended', () => {
    updatePagePlayIcons(false);
    if (isRepeat) {
      audio.currentTime = 0;
      audio.play();
    } else if (nextBtn) {
      nextBtn.click();
    }
  });

  // Scrubber seeking
  if (scrubberTrack) {
    scrubberTrack.addEventListener('click', (e) => {
      if (!audio.duration) return;
      const rect = scrubberTrack.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const pct = Math.max(0, Math.min(1, clickX / rect.width));
      audio.currentTime = pct * audio.duration;
    });
  }

  // Volume slider
  if (volumeSlider) {
    volumeSlider.value = audio.volume;
    volumeSlider.addEventListener('input', (e) => {
      audio.volume = parseFloat(e.target.value);
    });
  }

  // Jump to AI DJ button
  if (jumpToAiDjBtn) {
    jumpToAiDjBtn.addEventListener('click', () => {
      const djSec = document.getElementById('aiDjSection');
      const djInput = document.getElementById('aiDjInput');
      if (djSec) {
        djSec.scrollIntoView({ behavior: 'smooth', block: 'center' });
        if (djInput) setTimeout(() => djInput.focus(), 400);
      } else {
        window.location.href = '/#aiDjSection';
      }
    });
  }

  // Hook all song card play triggers
  document.querySelectorAll('.sp-play-trigger').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const card = btn.closest('[data-song-id]') || btn;
      const trackId = String(card.dataset.songId);

      // If clicking play trigger for currently playing track, toggle pause/play!
      if (currentTrackId === trackId) {
        if (!audio.paused) {
          audio.pause();
        } else {
          audio.play().catch(err => console.warn('Play error:', err));
        }
        return;
      }

      const track = {
        id: card.dataset.songId,
        title: card.dataset.songTitle,
        artist: card.dataset.songArtist,
        coverUrl: card.dataset.songCover,
        audioUrl: card.dataset.songAudio,
      };
      loadAndPlayTrack(track, true);
    });
  });

  // Preload first song into player bar if available without autoplay
  if (playlist.length > 0 && playerTitle && playerTitle.textContent === 'Select a song') {
    loadAndPlayTrack(playlist[0], false);
  }
}

/* ==========================================================================
   2. Moodify AI DJ & Emotion Detection Engine
   ========================================================================== */
function initAiDj() {
  const form = document.getElementById('aiDjForm');
  const input = document.getElementById('aiDjInput');
  const submitBtn = document.getElementById('aiDjSubmitBtn');
  const resultBox = document.getElementById('aiDjResultBox');
  const vibeTitle = document.getElementById('aiDjVibeTitle');
  const confidenceBadge = document.getElementById('aiDjConfidenceBadge');
  const energyBadge = document.getElementById('aiDjEnergyBadge');
  const commentary = document.getElementById('aiDjCommentary');
  const playMixBtn = document.getElementById('aiPlayMixBtn');
  const closeResultBtn = document.getElementById('closeAiDjResultBtn');
  const chips = document.querySelectorAll('.ai-chip-btn');

  let lastAiSongs = [];

  async function queryAiDj(promptText) {
    if (!promptText || !promptText.trim()) return;

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Analyzing vibe...</span>';
    }

    try {
      const csrftoken = getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value;
      const response = await fetch('/ai/dj/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken,
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({ prompt: promptText })
      });

      if (response.ok) {
        const data = await response.json();
        lastAiSongs = data.songs || [];

        // Update AI DJ result card
        if (vibeTitle) vibeTitle.textContent = `${data.vibe_title} (${data.mood_name})`;
        if (confidenceBadge) confidenceBadge.textContent = `✨ ${data.confidence}% AI Match`;
        if (energyBadge) energyBadge.textContent = `⚡ Energy: ${data.energy_score}%`;
        if (commentary) commentary.textContent = `"${data.dj_commentary}"`;

        if (resultBox) {
          resultBox.style.display = 'block';
          resultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }
    } catch (err) {
      console.error('Moodify AI DJ request failed:', err);
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> <span>Ask AI DJ</span>';
      }
    }
  }

  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      queryAiDj(input ? input.value : '');
    });
  }

  // Quick Chips
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      const vibe = chip.dataset.vibe || chip.textContent;
      if (input) input.value = vibe;
      queryAiDj(vibe);
    });
  });

  // Play AI Recommendation Mix
  if (playMixBtn) {
    playMixBtn.addEventListener('click', () => {
      if (lastAiSongs.length > 0) {
        const first = lastAiSongs[0];
        window.loadAndPlayTrack({
          id: first.id,
          title: first.title,
          artist: first.artist,
          coverUrl: first.cover_image_url,
          audioUrl: first.audio_preview_url
        }, true);
      }
    });
  }

  if (closeResultBtn && resultBox) {
    closeResultBtn.addEventListener('click', () => {
      resultBox.style.display = 'none';
    });
  }
}

/* ==========================================================================
   3. AI Song Studio Modal
   ========================================================================== */
function initAiStudioModal() {
  const modal = document.getElementById('aiStudioModal');
  const openBtns = document.querySelectorAll('.open-ai-studio-btn');
  const closeBtn = document.getElementById('closeAiModal');
  const form = document.getElementById('aiSongGenForm');

  if (!modal) return;

  openBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      modal.classList.add('open');
      const input = document.getElementById('aiPromptInput');
      if (input) setTimeout(() => input.focus(), 100);
    });
  });

  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      modal.classList.remove('open');
    });
  }

  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.classList.remove('open');
    }
  });

  if (form) {
    form.addEventListener('submit', () => {
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating Track with AI...';
      }
    });
  }
}

/* ==========================================================================
   4. AJAX Favorite Toggling
   ========================================================================== */
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function initFavoriteButtons() {
  const csrftoken = getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value;

  document.querySelectorAll('.fav-toggle-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();

      const songId = btn.dataset.songId;
      const url = btn.dataset.url || `/song/${songId}/favorite/`;

      try {
        btn.disabled = true;
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json'
          }
        });

        if (response.ok) {
          const data = await response.json();
          const isFavorited = data.is_favorited;

          // Sync all buttons for this song
          document.querySelectorAll(`.fav-toggle-btn[data-song-id="${songId}"]`).forEach(b => {
            const icon = b.querySelector('i');
            if (icon) {
              if (isFavorited) {
                icon.className = 'fa-solid fa-heart';
                b.classList.add('favorited');
              } else {
                icon.className = 'fa-regular fa-heart';
                b.classList.remove('favorited');
              }
            }
          });

          // Sync player favorite icon if currently playing
          const playerFavBtn = document.getElementById('spPlayerFavBtn');
          if (playerFavBtn && playerFavBtn.dataset.songId === songId) {
            if (isFavorited) {
              playerFavBtn.classList.add('favorited');
              playerFavBtn.querySelector('i').className = 'fa-solid fa-heart';
            } else {
              playerFavBtn.classList.remove('favorited');
              playerFavBtn.querySelector('i').className = 'fa-regular fa-heart';
            }
          }

          // If on Favorites page, smoothly fade card if unfavorited
          const favCard = btn.closest('.favorite-item-card');
          if (favCard && !isFavorited) {
            favCard.style.transition = 'all 0.3s ease';
            favCard.style.opacity = '0';
            favCard.style.transform = 'scale(0.95)';
            setTimeout(() => {
              favCard.remove();
              const remaining = document.querySelectorAll('.favorite-item-card').length;
              const countEl = document.getElementById('favoritesCountBadge');
              if (countEl) countEl.textContent = remaining;
              if (remaining === 0) {
                const empty = document.getElementById('favoritesEmptyState');
                if (empty) empty.style.display = 'block';
              }
            }, 300);
          }
        }
      } catch (err) {
        console.error('Favorite toggle failed:', err);
      } finally {
        btn.disabled = false;
      }
    });
  });
}

/* ==========================================================================
   5. Keyboard Shortcut
   ========================================================================== */
function initSearchKeyboardShortcut() {
  const searchInput = document.getElementById('mainSearchInput');
  if (!searchInput) return;

  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== searchInput && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
      e.preventDefault();
      searchInput.focus();
      searchInput.select();
    }
  });
}
