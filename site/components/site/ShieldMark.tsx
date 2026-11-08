/** The Guildward shield (same outline as the dashboard's mark), split in two tones. */
export function ShieldMark({ size = 28, className }: { size?: number; className?: string }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M12 2l8.5 3.4v6.1c0 5.2-3.5 9.5-8.5 11.3-5-1.8-8.5-6.1-8.5-11.3V5.4L12 2z"
        fill="var(--gw-shield, #74aee3)"
      />
      <path d="M12 2v20.8c5-1.8 8.5-6.1 8.5-11.3V5.4L12 2z" fill="var(--gw-shield-2, #2d6aa5)" />
    </svg>
  );
}
