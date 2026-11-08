import Link from "next/link";

export function Footer() {
  return (
    <footer className="gw-footer">
      <div className="gw-tile gw-tile-statement">
        <p className="gw-tile-lead">Built for kids on Discord, and for the people who look out for them.</p>
        <p className="gw-tile-legal">
          Guildward is not affiliated with Discord. Detection rules are kept private so abusers can&rsquo;t phrase
          around them.
        </p>
      </div>
      <nav className="gw-tile gw-tile-nav" aria-label="Footer">
        <ul>
          <li>
            <Link href="/">Home</Link>
          </li>
          <li>
            <Link href="/parents">For parents</Link>
          </li>
          <li>
            <Link href="/stats">Stats</Link>
          </li>
          <li>
            <Link href="/dashboard">Dashboard</Link>
          </li>
          <li>
            <Link href="/#install">Install</Link>
          </li>
          <li>
            <Link href="/#questions">Questions</Link>
          </li>
        </ul>
      </nav>
      <div className="gw-tile gw-tile-help">
        <p>Need to talk to someone now?</p>
        <p className="gw-tile-big">
          <a href="https://childhelplineinternational.org/helplines/" rel="noopener">
            Find a child helpline
          </a>
        </p>
        <p>Free helplines, country by country. In danger: call your local emergency number.</p>
      </div>
      <div className="gw-tile gw-tile-code">
        <p>Running a server with Guard?</p>
        <Link className="gw-tile-big" href="/dashboard">
          Open the dashboard
        </Link>
      </div>
      <div className="gw-tile gw-tile-word" aria-hidden="true">
        guildward
      </div>
      <Link className="gw-tile gw-tile-go" href="/#install">
        <span>Add Guildward to Discord</span>
        <svg viewBox="0 0 48 48" width="56" height="56" aria-hidden="true" focusable="false">
          <path d="M10 38 38 10M16 10h22v22" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="square" />
        </svg>
      </Link>
    </footer>
  );
}
