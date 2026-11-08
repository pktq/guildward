import type { ReactNode } from "react";
import { ShieldMark } from "./ShieldMark";

/* Small building blocks for true-size Discord fragments (dark theme). Text inside them is Guildward's real wording. */

export type Level = "green" | "yellow" | "red" | "grey" | "blue";
type Mark = "warn" | "ok" | "info" | "severe" | "bullet";

export function Dot({ level }: { level: Exclude<Level, "grey" | "blue"> }) {
  const label = { green: "Green", yellow: "Yellow", red: "Red" }[level];
  return (
    <svg className={`dc-dot dc-dot-${level}`} viewBox="0 0 16 16" role="img" aria-label={label}>
      <circle cx="8" cy="8" r="7" />
    </svg>
  );
}

function Glyph({ mark }: { mark: Mark }) {
  if (mark === "bullet")
    return (
      <span className="dc-glyph dc-glyph-bullet" aria-hidden="true">
        •
      </span>
    );
  if (mark === "severe")
    return (
      <span className="dc-glyph dc-glyph-severe" aria-label="Severe">
        !!
      </span>
    );
  const label = { warn: "Warning", ok: "Reassuring", info: "Note" }[mark];
  return (
    <svg className={`dc-glyph dc-glyph-${mark}`} viewBox="0 0 16 16" role="img" aria-label={label}>
      {mark === "warn" && (
        <>
          <path d="M8 1.5 15 14H1z" />
          <path d="M8 6v3.6M8 11.2v.6" className="dc-glyph-ink" />
        </>
      )}
      {mark === "ok" && (
        <>
          <rect x="1" y="1" width="14" height="14" rx="3" />
          <path d="m4.3 8.2 2.4 2.4 5-5" className="dc-glyph-ink" />
        </>
      )}
      {mark === "info" && (
        <>
          <rect x="1" y="1" width="14" height="14" rx="3" />
          <path d="M8 7v4.6M8 4.6v.4" className="dc-glyph-ink" />
        </>
      )}
    </svg>
  );
}

export function Reasons({ items }: { items: [Mark, ReactNode][] }) {
  return (
    <ul className="dc-reasons">
      {items.map(([m, t], i) => (
        <li key={i}>
          <Glyph mark={m} /> <span>{t}</span>
        </li>
      ))}
    </ul>
  );
}

export function Avatar({ name, color, bot }: { name: string; color?: string; bot?: boolean }) {
  if (bot)
    return (
      <span className="dc-avatar dc-avatar-bot" aria-hidden="true">
        <ShieldMark size={24} />
      </span>
    );
  return (
    <span className="dc-avatar" style={{ background: color }} aria-hidden="true">
      {name.slice(0, 1).toUpperCase()}
    </span>
  );
}

export function Message({
  name,
  color,
  time,
  bot,
  children,
  ephemeral,
  part,
}: {
  name: string;
  color?: string;
  time: string;
  bot?: boolean;
  children: ReactNode;
  ephemeral?: boolean;
  part?: string;
}) {
  return (
    <div className={`dc-msg${ephemeral ? " dc-msg-eph" : ""}`} data-part={part}>
      <Avatar name={name} color={color} bot={bot} />
      <div className="dc-msg-body">
        <p className="dc-msg-head">
          <span className="dc-name" style={bot ? undefined : { color }}>
            {name}
          </span>
          {bot && <span className="dc-apptag">APP</span>}
          <span className="dc-time">{time}</span>
        </p>
        {children}
        {ephemeral && (
          <p className="dc-eph">
            <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
              <path d="M8 3C4 3 1.5 8 1.5 8S4 13 8 13s6.5-5 6.5-5S12 3 8 3zm0 7.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5z" />
            </svg>
            Only you can see this · <span className="dc-link">Dismiss message</span>
          </p>
        )}
      </div>
    </div>
  );
}

export function Embed({
  level,
  title,
  description,
  children,
  footer,
  part,
}: {
  level: Level;
  title: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  part?: string;
}) {
  return (
    <div className={`dc-embed dc-embed-${level}`}>
      <p className="dc-embed-title" data-part={part}>
        {title}
      </p>
      {description && <div className="dc-embed-desc">{description}</div>}
      {children}
      {footer && <p className="dc-embed-foot">{footer}</p>}
    </div>
  );
}

export function Field({ name, children, part }: { name: ReactNode; children: ReactNode; part?: string }) {
  return (
    <div className="dc-field" data-part={part}>
      <p className="dc-field-name">{name}</p>
      <div className="dc-field-value">{children}</div>
    </div>
  );
}

export function Buttons({ children, part }: { children: ReactNode; part?: string }) {
  return (
    <div className="dc-buttons" data-part={part}>
      {children}
    </div>
  );
}

export function Btn({
  kind = "secondary",
  children,
}: {
  kind?: "primary" | "secondary" | "success" | "danger" | "link";
  children: ReactNode;
}) {
  return (
    <span className={`dc-btn dc-btn-${kind}`}>
      {children}
      {kind === "link" && (
        <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
          <path d="M6 3H3v10h10v-3M9 2h5v5M14 2 7 9" fill="none" stroke="currentColor" strokeWidth="1.6" />
        </svg>
      )}
    </span>
  );
}
