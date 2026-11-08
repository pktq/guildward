"use client";

import { useState } from "react";

// "The Door", the launch film. Set NEXT_PUBLIC_DOOR_VIDEO_ID to its YouTube ID once it's published; until then the
// section shows the poster without a play button. Nothing loads from YouTube until someone presses play, and then
// only from youtube-nocookie.com.
const VIDEO_ID = process.env.NEXT_PUBLIC_DOOR_VIDEO_ID?.trim() || "";

export function DoorFilm() {
  const [playing, setPlaying] = useState(false);
  const ready = /^[\w-]{11}$/.test(VIDEO_ID);

  return (
    <section className="gw-film" aria-labelledby="film-title">
      <div className="gw-film-head">
        <h2 id="film-title">The Door</h2>
        <p>
          A closed bedroom door feels safe. A three-minute film about the gaps around it, where sextortion gets in, and
          the one only a parent can close.
        </p>
      </div>
      <div className="gw-film-frame">
        {ready && playing ? (
          <iframe
            src={`https://www.youtube-nocookie.com/embed/${VIDEO_ID}?autoplay=1&rel=0`}
            title="The Door, a film by Guildward"
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
                Play the film
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
