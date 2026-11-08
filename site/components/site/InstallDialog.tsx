"use client";

import { useState } from "react";
import { ShieldMark } from "./ShieldMark";
import { REPO_URL, type InstallLinks } from "./install";

type Where = "kid" | "server";
type Mode = "checks" | "guard";

const COPY = {
  kid: "On a kid's own account. The checks then work in DMs, group chats and every server, and every answer is visible only to them.",
  checks: "In a server, checks only: members can run Guildward's checks there. The bot reads nothing in the server.",
  guard:
    "In a server, full Guard: alerts in a private mod channel, the audit and the dashboard. It asks only for the permissions its actions use.",
};

export function InstallDialog({ links }: { links: InstallLinks | null }) {
  const [where, setWhere] = useState<Where>("kid");
  const [mode, setMode] = useState<Mode>("guard");
  const key = where === "kid" ? "kid" : mode;
  const href = links?.[key];

  return (
    <div className="gw-dialog dc-light" data-ui="" role="group" aria-labelledby="install-dialog-title">
      <p className="gw-dialog-head">
        <ShieldMark size={22} />
        <span id="install-dialog-title">Add Guildward</span>
      </p>
      <fieldset className="gw-seg">
        <legend>Where does it go?</legend>
        <label>
          <input type="radio" name="install-where" checked={where === "kid"} onChange={() => setWhere("kid")} />
          <span>My account</span>
        </label>
        <label>
          <input type="radio" name="install-where" checked={where === "server"} onChange={() => setWhere("server")} />
          <span>A server I run</span>
        </label>
      </fieldset>
      {where === "server" && (
        <fieldset className="gw-seg">
          <legend>How much should it do?</legend>
          <label>
            <input type="radio" name="install-mode" checked={mode === "checks"} onChange={() => setMode("checks")} />
            <span>Checks only</span>
          </label>
          <label>
            <input type="radio" name="install-mode" checked={mode === "guard"} onChange={() => setMode("guard")} />
            <span>Full Guard</span>
          </label>
        </fieldset>
      )}
      <p className="gw-dialog-copy" aria-live="polite">
        {COPY[key]}
      </p>
      {href ? (
        <a className="gw-btn gw-btn-ink gw-dialog-go" href={href} rel="noopener">
          Open Discord to add it
        </a>
      ) : (
        <>
          <a className="gw-btn gw-btn-ink gw-dialog-go" href={`${REPO_URL}#set-up-the-discord-app`} rel="noopener">
            Set up your own copy
          </a>
          <p className="gw-dialog-fine">
            The public install link isn&rsquo;t switched on yet. Until it is, you can run Guildward from the source on
            GitHub.
          </p>
        </>
      )}
    </div>
  );
}
