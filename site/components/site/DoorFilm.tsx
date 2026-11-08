"use client";

import { useState } from "react";

// The launch film. NEXT_PUBLIC_DOOR_VIDEO_ID overrides the YouTube ID; the default is a stand-in for testing
// playback until the real film is up. Nothing loads from YouTube until someone presses play, and then only from
// youtube-nocookie.com.
const VIDEO_ID = process.env.NEXT_PUBLIC_DOOR_VIDEO_ID?.trim() || "ih2xubMaZWI";

export function DoorFilm() {
  const [playing, setPlaying] = useState(false);
  const ready = /^[\w-]{11}$/.test(VIDEO_ID);

  return (
    <section className="gw-film" aria-labelledby="film-title">
      <h2 id="film-title">Watch the film</h2>
      <div className="gw-film-frame">
        {ready && playing ? (
          <iframe
            src={`https://www.youtube-nocookie.com/embed/${VIDEO_ID}?autoplay=1&rel=0`}
            title="Guildward film"
            allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
            allowFullScreen
            referrerPolicy="strict-origin-when-cross-origin"
          />
        ) : (
          <div className="gw-film-poster">
            <span className="gw-film-door" aria-hidden="true" />
            {ready ? (
              <button type="button" className="gw-film-play" onClick={() => setPlaying(true)}>
                <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" focusable="false">
                  <path d="M8 5v14l11-7z" fill="currentColor" />
                </svg>
                Play
                <span className="gw-film-note">Plays from YouTube</span>
              </button>
            ) : (
              <p className="gw-film-soon">Coming soon</p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
