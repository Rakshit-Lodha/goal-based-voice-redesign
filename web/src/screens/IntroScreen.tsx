import { useState } from "react";

/**
 * The pre-call intro surface. Shown after the user taps the Maya hero in
 * EntryScreen and before the WebRTC call starts. Sets the expectation for
 * the conversation: ten minutes, one call, an actionable plan.
 *
 * Orb sits above (rendered by Conversation). This component contributes
 * the headline, lede, and the two CTAs at the bottom.
 */
export default function IntroScreen({
  onStart,
  dialing,
}: {
  onStart: () => void;
  dialing: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <section className="intro">
      <div className="intro-copy">
        <h1>
          Meet Maya,<br />your private<br />wealth advisor.
        </h1>
        {expanded ? (
          <ul className="intro-points">
            <li>Speak naturally — Maya guides you stage by stage.</li>
            <li>We pull your real holdings via MF Central and Account Aggregator.</li>
            <li>You leave with a personalised plan PDF.</li>
          </ul>
        ) : (
          <p>Ten minutes. One conversation.<br />A plan you can act on today.</p>
        )}
      </div>

      <div className="intro-ctas">
        <button
          type="button"
          className="intro-primary"
          onClick={onStart}
          disabled={dialing}
        >
          {dialing ? "Connecting..." : "Start with Maya"}
        </button>
        <button
          type="button"
          className="intro-secondary"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? "Got it" : "How does this work?"}
        </button>
      </div>

      <style>{`
        .intro {
          position: absolute;
          inset: 0;
          padding: 0 28px 36px;
          display: flex;
          flex-direction: column;
          justify-content: flex-end;
          align-items: center;
          text-align: center;
          color: var(--ivory);
          pointer-events: none;
        }
        .intro-copy {
          margin-bottom: 56px;
          pointer-events: auto;
        }
        .intro h1 {
          margin: 0;
          font-family: var(--font-display);
          font-weight: 400;
          font-size: 34px;
          line-height: 1.08;
          letter-spacing: -0.01em;
          color: var(--ivory);
        }
        .intro p {
          margin: 18px 0 0;
          color: var(--ivory-soft);
          font-size: 14px;
          line-height: 1.55;
        }
        .intro-points {
          margin: 22px 0 0;
          padding: 0;
          list-style: none;
          display: grid;
          gap: 10px;
          color: var(--ivory-soft);
          font-size: 13px;
          line-height: 1.5;
          text-align: left;
        }
        .intro-points li {
          position: relative;
          padding-left: 18px;
        }
        .intro-points li::before {
          content: "·";
          position: absolute;
          left: 4px;
          top: -2px;
          color: var(--champagne);
          font-size: 20px;
          line-height: 1;
        }
        .intro-ctas {
          width: 100%;
          display: grid;
          gap: 12px;
          pointer-events: auto;
        }
        .intro-primary {
          height: 56px;
          border: none;
          border-radius: 999px;
          background: var(--champagne);
          color: #1a1408;
          font-family: var(--font-body);
          font-size: 16px;
          font-weight: 600;
          letter-spacing: 0.01em;
          cursor: pointer;
          transition: transform var(--dur-fast) var(--ease-out),
                      opacity var(--dur-fast) var(--ease-out);
        }
        .intro-primary:hover:not(:disabled) { transform: translateY(-1px); }
        .intro-primary:disabled { opacity: 0.6; cursor: progress; }
        .intro-secondary {
          height: 52px;
          border: 1px solid rgba(232, 222, 196, 0.22);
          border-radius: 999px;
          background: transparent;
          color: var(--ivory);
          font-family: var(--font-body);
          font-size: 14px;
          font-weight: 500;
          cursor: pointer;
          transition: background var(--dur-fast) var(--ease-out);
        }
        .intro-secondary:hover { background: rgba(232, 222, 196, 0.06); }
      `}</style>
    </section>
  );
}
