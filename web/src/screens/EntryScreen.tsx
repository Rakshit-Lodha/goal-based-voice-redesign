/**
 * A neutral, standalone landing page for the planning demo.
 *
 * This deliberately avoids imitating an existing finance super-app: the page
 * gives the voice-planning experience its own brand, hierarchy, and entry point.
 */
import type { MemoryLoadState } from "../memory";
import type { MemoryMode } from "../pcClient";

type EntryScreenProps = {
  routeMode: MemoryMode;
  memoryState: MemoryLoadState;
  onStart: () => void;
  onStartOver: () => void;
  onEmergency?: () => void;
};

export default function EntryScreen({
  routeMode,
  memoryState,
  onStart,
  onStartOver,
  onEmergency = () => undefined,
}: EntryScreenProps) {
  const simulator = routeMode === "simulator";
  const loading = routeMode === "resume" && memoryState.status === "loading";
  const memory = memoryState.status === "available" ? memoryState.memory : null;
  const unavailable = routeMode === "resume" && memoryState.status === "unavailable";
  const headline = memory?.completed_plan
    ? "Review or update your wealth plan"
    : memory?.headline;

  return (
    <main className="entry-root">
      <div className="entry-scroll">
        <header className="entry-header">
          <div className="entry-brand" aria-label="Northstar Wealth">
            <span className="entry-brand-mark">N</span>
            <span>Northstar</span>
          </div>
          <button className="entry-profile" type="button" aria-label="Open profile">
            RL
          </button>
        </header>

        <section className="entry-welcome">
          <p className="entry-eyebrow">Good morning, Rakshit</p>
          <h1>Build a plan for the life you want.</h1>
          <p className="entry-lede">
            Turn your goals, investments, and monthly cash flow into one clear plan.
          </p>
        </section>

        <div className="planner-card-wrap">
          <button
            className={`planner-card${loading ? " planner-card-loading" : ""}`}
            onClick={onStart}
            aria-label={
              simulator
                ? "Start financial decision simulator with Maya"
                : memory
                  ? "Resume planning with Maya"
                  : "Start planning with Maya"
            }
            disabled={loading}
            type="button"
          >
            <span className="planner-kicker">
              <span className="planner-status" />
              {loading
                ? "Checking saved plan"
                : memory
                  ? "Maya remembers"
                  : simulator
                    ? "Your financial picture is ready"
                  : unavailable
                    ? "No previous plan found"
                    : "Maya is ready"}
            </span>
            <strong>
              {loading
                ? "Loading your last conversation"
                : memory
                  ? `Welcome back, ${memory.user_name}`
                  : simulator
                    ? "Rehearse a decision before you make it"
                  : "Start your guided wealth plan"}
            </strong>
            {memory && <span className="planner-memory-headline">{headline}</span>}
            <span className="planner-copy">
              {loading
                ? "Bringing back your latest planning checkpoint."
                : memory
                  ? memory.summary
                  : simulator
                    ? "Plan a traditional goal or ask Maya to simulate a major life change."
                  : "A private, voice-led conversation. About fifteen minutes."}
            </span>
            <span className="planner-action">
              {memory ? "Resume planning" : simulator ? "Start simulating" : "Start planning"}
              <span aria-hidden="true">→</span>
            </span>
            <span className="planner-orbit planner-orbit-one" />
            <span className="planner-orbit planner-orbit-two" />
          </button>
          {memory && (
            <button
              className="planner-start-over"
              onClick={onStartOver}
              type="button"
            >
              Start over with a fresh plan
            </button>
          )}
          {simulator && (
            <button
              className="planner-emergency"
              onClick={onEmergency}
              type="button"
              aria-label="Start emergency planning with Maya"
            >
              <span className="planner-emergency-icon" aria-hidden="true">!</span>
              <span>
                <b>Emergency</b>
                <small>Rework my existing plan now</small>
              </span>
              <span className="planner-emergency-arrow" aria-hidden="true">→</span>
            </button>
          )}
        </div>

        <section className="entry-section" aria-labelledby="overview-heading">
          <div className="section-heading">
            <h2 id="overview-heading">Your overview</h2>
            <button type="button">View details</button>
          </div>
          <div className="overview-card">
            <div>
              <span className="overview-label">
                {simulator ? "Demo financial profile" : "Linked portfolio"}
              </span>
              <strong>
                {simulator ? "Investments and cash flow ready" : "Connect your investments"}
              </strong>
            </div>
            <span className="overview-icon" aria-hidden="true">↗</span>
          </div>
        </section>

        <section className="entry-section" aria-labelledby="goals-heading">
          <div className="section-heading">
            <h2 id="goals-heading">Plan around your goals</h2>
            <span>Explore</span>
          </div>
          <div className="goal-grid">
            <article className="goal-card goal-card-sage">
              <span className="goal-icon" aria-hidden="true">⌂</span>
              <strong>Home</strong>
              <p>Map the deposit, timeline, and monthly investment.</p>
            </article>
            <article className="goal-card goal-card-sand">
              <span className="goal-icon" aria-hidden="true">◎</span>
              <strong>Retirement</strong>
              <p>Build long-term independence one phase at a time.</p>
            </article>
          </div>
        </section>
      </div>

      <nav className="entry-nav" aria-label="Primary navigation">
        <button className="entry-nav-item active" type="button">
          <span aria-hidden="true">⌂</span>
          Home
        </button>
        <button className="entry-nav-item" type="button">
          <span aria-hidden="true">◫</span>
          Portfolio
        </button>
        <button className="entry-nav-planner" onClick={onStart} type="button">
          <span aria-hidden="true">✦</span>
          Plan
        </button>
        <button className="entry-nav-item" type="button">
          <span aria-hidden="true">◎</span>
          Goals
        </button>
        <button className="entry-nav-item" type="button">
          <span aria-hidden="true">○</span>
          Profile
        </button>
      </nav>

      <style>{`
        .entry-root {
          position: absolute;
          inset: 0;
          color: #13283b;
          background:
            radial-gradient(circle at 94% 2%, rgba(88, 214, 177, 0.18), transparent 28%),
            linear-gradient(180deg, #f7fbfa 0%, #eef4f2 100%);
          font-family: var(--font-body);
          overflow: hidden;
        }
        .entry-scroll {
          position: absolute;
          inset: 0;
          padding: 0 22px 104px;
          overflow-x: hidden;
          overflow-y: auto;
          overscroll-behavior: contain;
        }

        .entry-header {
          height: 78px;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .entry-brand {
          display: flex;
          align-items: center;
          gap: 9px;
          color: #0b2033;
          font-size: 16px;
          font-weight: 700;
          letter-spacing: -0.01em;
        }
        .entry-brand-mark {
          width: 30px;
          height: 30px;
          display: grid;
          place-items: center;
          border-radius: 10px 10px 10px 3px;
          color: #0b2033;
          background: #58d6b1;
          font-family: var(--font-display);
          font-size: 18px;
          font-weight: 600;
        }
        .entry-profile {
          width: 38px;
          height: 38px;
          display: grid;
          place-items: center;
          border: 1px solid #d7e2df;
          border-radius: 50%;
          color: #345064;
          background: rgba(255, 255, 255, 0.78);
          font-size: 12px;
          font-weight: 700;
        }

        .entry-welcome {
          padding: 16px 0 24px;
        }
        .entry-eyebrow {
          margin: 0 0 8px;
          color: #4d6b70;
          font-size: 12px;
          font-weight: 700;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }
        .entry-welcome h1 {
          max-width: 320px;
          color: #0b2033;
          font-family: var(--font-display);
          font-size: 37px;
          font-weight: 500;
          line-height: 1.05;
          letter-spacing: -0.035em;
        }
        .entry-lede {
          max-width: 320px;
          margin: 13px 0 0;
          color: #5e7381;
          font-size: 14px;
          line-height: 1.5;
        }

        .planner-card {
          position: relative;
          width: 100%;
          min-height: 220px;
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          padding: 22px;
          border: 0;
          border-radius: 26px;
          color: #f4fbf8;
          background:
            radial-gradient(circle at 92% 86%, rgba(88, 214, 177, 0.2), transparent 34%),
            linear-gradient(145deg, #102f43 0%, #071a2a 100%);
          box-shadow: 0 20px 44px rgba(13, 44, 60, 0.18);
          overflow: hidden;
          text-align: left;
          transition: transform var(--dur-fast) var(--ease-out),
                      box-shadow var(--dur-fast) var(--ease-out);
        }
        .planner-card-wrap {
          display: grid;
          gap: 10px;
        }
        .planner-emergency {
          width: 100%;
          display: grid;
          grid-template-columns: auto 1fr auto;
          gap: 12px;
          align-items: center;
          padding: 14px 16px;
          border: 1px solid rgba(177, 74, 42, 0.2);
          border-radius: 18px;
          color: #6f2e22;
          background: linear-gradient(135deg, #fff4ef 0%, #fbe5db 100%);
          box-shadow: 0 10px 24px rgba(111, 46, 34, 0.08);
          text-align: left;
        }
        .planner-emergency:hover {
          transform: translateY(-1px);
        }
        .planner-emergency-icon {
          width: 34px;
          height: 34px;
          display: grid;
          place-items: center;
          border-radius: 50%;
          color: #fff8f4;
          background: #b14a2a;
          font-family: var(--font-display);
          font-size: 20px;
          font-weight: 700;
        }
        .planner-emergency b,
        .planner-emergency small {
          display: block;
        }
        .planner-emergency b {
          font-size: 13px;
        }
        .planner-emergency small {
          margin-top: 2px;
          color: #8a5b50;
          font-size: 11px;
        }
        .planner-emergency-arrow {
          font-size: 18px;
        }
        .planner-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 24px 52px rgba(13, 44, 60, 0.24);
        }
        .planner-kicker {
          display: flex;
          align-items: center;
          gap: 8px;
          color: #9debd3;
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.09em;
          text-transform: uppercase;
        }
        .planner-status {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          background: #58d6b1;
          box-shadow: 0 0 0 5px rgba(88, 214, 177, 0.1);
        }
        .planner-card strong {
          max-width: 250px;
          margin-top: 22px;
          font-family: var(--font-display);
          font-size: 27px;
          font-weight: 500;
          line-height: 1.08;
          letter-spacing: -0.025em;
        }
        .planner-memory-headline {
          max-width: 260px;
          margin-top: 8px;
          color: #b9f5e3;
          font-size: 14px;
          font-weight: 700;
          line-height: 1.3;
          overflow-wrap: anywhere;
        }
        .planner-copy {
          max-width: 245px;
          margin-top: 10px;
          color: rgba(237, 249, 245, 0.7);
          font-size: 12px;
          line-height: 1.5;
          overflow-wrap: anywhere;
        }
        .planner-action {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-top: 20px;
          color: #9debd3;
          font-size: 13px;
          font-weight: 700;
        }
        .planner-action span {
          width: 26px;
          height: 26px;
          display: grid;
          place-items: center;
          border-radius: 50%;
          color: #0b2033;
          background: #58d6b1;
        }
        .planner-orbit {
          position: absolute;
          border: 1px solid rgba(157, 235, 211, 0.17);
          border-radius: 50%;
          pointer-events: none;
        }
        .planner-orbit-one {
          width: 126px;
          height: 126px;
          right: -42px;
          top: -20px;
        }
        .planner-orbit-two {
          width: 72px;
          height: 72px;
          right: -7px;
          top: 7px;
          background: radial-gradient(circle at 38% 34%, #b9f5e3 0 7%, #58d6b1 32%, #168b79 74%, #0e4c50 100%);
          box-shadow: 0 0 44px rgba(88, 214, 177, 0.24);
        }
        .planner-card:disabled {
          cursor: wait;
        }
        .planner-card-loading .planner-status {
          animation: memory-pulse 1.1s ease-in-out infinite alternate;
        }
        .planner-start-over {
          justify-self: start;
          padding: 7px 4px;
          color: #45646a;
          font-size: 12px;
          font-weight: 700;
          text-decoration: underline;
          text-underline-offset: 3px;
        }
        .planner-start-over:focus-visible {
          outline: 2px solid #168b79;
          outline-offset: 3px;
          border-radius: 4px;
        }
        @keyframes memory-pulse {
          from { opacity: 0.45; }
          to { opacity: 1; }
        }

        .entry-section {
          margin-top: 26px;
        }
        .section-heading {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 12px;
        }
        .section-heading h2 {
          color: #183044;
          font-size: 16px;
          font-weight: 700;
        }
        .section-heading button,
        .section-heading > span {
          color: #52716f;
          font-size: 11px;
          font-weight: 600;
        }
        .overview-card {
          display: flex;
          align-items: center;
          justify-content: space-between;
          min-height: 76px;
          padding: 17px 18px;
          border: 1px solid #dce7e3;
          border-radius: 18px;
          background: rgba(255, 255, 255, 0.74);
        }
        .overview-card > div {
          display: grid;
          gap: 4px;
        }
        .overview-label {
          color: #71858e;
          font-size: 10px;
          font-weight: 700;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }
        .overview-card strong {
          color: #183044;
          font-size: 14px;
          font-weight: 650;
        }
        .overview-icon {
          width: 34px;
          height: 34px;
          display: grid;
          place-items: center;
          border-radius: 50%;
          color: #17354a;
          background: #dff6ef;
        }

        .goal-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }
        .goal-card {
          min-height: 146px;
          padding: 16px;
          border-radius: 19px;
          color: #173044;
        }
        .goal-card-sage { background: #dceee8; }
        .goal-card-sand { background: #eee8dc; }
        .goal-icon {
          width: 34px;
          height: 34px;
          display: grid;
          place-items: center;
          margin-bottom: 18px;
          border-radius: 11px;
          background: rgba(255, 255, 255, 0.6);
          font-size: 18px;
        }
        .goal-card strong {
          display: block;
          font-size: 14px;
        }
        .goal-card p {
          margin: 6px 0 0;
          color: #667a80;
          font-size: 10px;
          line-height: 1.45;
        }

        .entry-nav {
          position: absolute;
          left: 0;
          right: 0;
          bottom: 0;
          height: 82px;
          display: grid;
          grid-template-columns: repeat(5, 1fr);
          align-items: center;
          padding: 8px 10px max(8px, env(safe-area-inset-bottom));
          border-top: 1px solid rgba(22, 50, 64, 0.09);
          background: rgba(249, 252, 251, 0.95);
          backdrop-filter: blur(18px);
          z-index: 4;
        }
        .entry-nav-item,
        .entry-nav-planner {
          display: grid;
          justify-items: center;
          gap: 5px;
          color: #75878f;
          font-size: 9px;
          font-weight: 600;
        }
        .entry-nav-item > span {
          font-size: 18px;
          line-height: 1;
        }
        .entry-nav-item.active { color: #12344a; }
        .entry-nav-planner {
          align-self: start;
          margin-top: -24px;
          color: #16394a;
        }
        .entry-nav-planner > span {
          width: 48px;
          height: 48px;
          display: grid;
          place-items: center;
          border: 5px solid #f4f8f7;
          border-radius: 17px;
          color: #0a2738;
          background: #58d6b1;
          box-shadow: 0 8px 18px rgba(37, 132, 112, 0.24);
          font-size: 19px;
        }

        @media (max-height: 760px) {
          .entry-welcome { padding-top: 4px; }
          .entry-welcome h1 { font-size: 32px; }
          .planner-card { min-height: 196px; }
        }
      `}</style>
    </main>
  );
}
