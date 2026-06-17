/**
 * Entry screen — Aditya Birla Capital (ABCD) post-KYC home with a premium
 * Maya Wealth Desk card sitting in the white sheet above the Track grid.
 * Tapping the card calls onStart() which mounts the voice agent surface.
 *
 * Layout mirrors the ABCD app home: red hero zone (My Holdings, CashBack,
 * ABCD Coins) → white sheet (Maya entry + 4 Track tiles) → curved-scoop
 * bottom nav with My Track active.
 */
export default function EntryScreen({ onStart }: { onStart: () => void }) {
  return (
    <div className="entry-root">
      {/* RED HERO ZONE */}
      <div className="hero">
        <div className="topbar">
          <button className="holdings-pill" type="button">
            My Holdings <span className="arrow">↗</span>
          </button>
          <div className="spacer" />
          <div className="dice-icon" title="Rewards">🎲</div>
          <div className="icon-btn" title="Notifications">🔔</div>
          <div className="avatar">RL</div>
        </div>

        <div className="hero-cards">
          <div className="hero-card">
            <div className="icon">💰</div>
            <div className="value">₹0</div>
            <div className="label">CashBack</div>
            <div className="chev">›</div>
          </div>
          <div className="hero-card">
            <div className="icon">🪙</div>
            <div className="value">50</div>
            <div className="label">ABCD Coins</div>
            <div className="chev">›</div>
          </div>
        </div>
      </div>

      {/* WHITE SHEET */}
      <div className="sheet">
        <button
          className="maya-card"
          onClick={onStart}
          aria-label="Open Maya Wealth Desk"
          type="button"
        >
          <span className="badge">Wealth Desk</span>
          <h2>Plan your first move with Maya</h2>
          <p>Your private wealth expert is ready — voice-led goal planning in minutes.</p>
          <div className="orb" />
          <div className="card-arrow">›</div>
        </button>

        <div className="tracks">
          <div className="track">
            <div className="title">Portfolio Track <span className="chev-circle">›</span></div>
            <div className="art">💼</div>
            <div className="foot">
              <div className="row"><span>🔒</span><span>₹XX,XXX</span></div>
              <div className="row"><span>⊕</span><span>Link account</span></div>
            </div>
            <div className="eye">⊘</div>
          </div>
          <div className="track">
            <div className="title">Credit Track <span className="chev-circle">›</span></div>
            <div className="art">📊</div>
            <div className="foot">Check your score &amp; trends</div>
          </div>
          <div className="track">
            <div className="title">Vehicle Track <span className="chev-circle">›</span></div>
            <div className="art">🚗</div>
          </div>
          <div className="track">
            <div className="title">Spend Track <span className="chev-circle">›</span></div>
            <div className="art">🧮</div>
          </div>
        </div>
      </div>

      {/* CURVED-SCOOP BOTTOM NAV */}
      <nav className="nav">
        <svg className="nav-bg" viewBox="0 -22 390 108" preserveAspectRatio="none">
          <path d="M 0 30 L 140 30 Q 195 -28 250 30 L 390 30 L 390 86 L 0 86 Z" fill="#FFFFFF" />
          <path
            d="M 0 30 L 140 30 Q 195 -28 250 30 L 390 30"
            stroke="var(--champagne)"
            strokeWidth="1.6"
            fill="none"
            strokeLinecap="round"
          />
        </svg>
        <div className="nav-items">
          <div className="nav-item">
            <div className="ic">💵</div>
            <span>Invest</span>
          </div>
          <div className="nav-item">
            <div className="ic">
              <div className="abcd-grid"><span>a</span><span>b</span><span>c</span><span>d</span></div>
            </div>
            <span>Home</span>
          </div>
          <div className="nav-item active">
            <div className="badge">📈</div>
            <span>My Track</span>
          </div>
          <div className="nav-item">
            <div className="ic">🤝</div>
            <span>Loans</span>
          </div>
          <div className="nav-item">
            <div className="ic">🛡</div>
            <span>Insure</span>
          </div>
        </div>
      </nav>

      <style>{`
        .entry-root {
          position: absolute;
          inset: 0;
          color: var(--ivory);
          font-family: var(--font-body);
          overflow: hidden;
        }

        /* ===== RED HERO ===== */
        .hero {
          position: absolute;
          left: 0; right: 0; top: 0;
          padding: 14px 20px 0;
          background: linear-gradient(180deg, #D9232E 0%, var(--navy) 100%);
          height: 232px;
        }
        .topbar {
          margin-top: 10px;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .holdings-pill {
          display: inline-flex; align-items: center; gap: 8px;
          height: 36px; padding: 0 14px;
          background: var(--champagne);
          color: var(--ink);
          border-radius: 8px 8px 18px 8px;
          font-weight: 800; font-size: 14px;
          border: none;
          cursor: pointer;
          font-family: inherit;
        }
        .holdings-pill .arrow {
          color: var(--navy);
          font-weight: 900;
        }
        .spacer { flex: 1; }
        .icon-btn {
          width: 36px; height: 36px;
          display: grid; place-items: center;
          border-radius: 50%;
          background: rgba(255,255,255,0.16);
          color: var(--ivory);
          font-size: 16px;
        }
        .avatar {
          width: 36px; height: 36px;
          display: grid; place-items: center;
          border-radius: 50%;
          background: #FFFFFF;
          color: var(--navy);
          font-weight: 800; font-size: 12px;
          letter-spacing: 0.04em;
        }
        .dice-icon {
          width: 36px; height: 36px;
          display: grid; place-items: center;
          border-radius: 8px;
          background: #FFFFFF;
          font-size: 18px;
        }

        .hero-cards {
          margin-top: 16px;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }
        .hero-card {
          position: relative;
          height: 124px;
          padding: 12px 14px 10px;
          border-radius: 18px;
          background: rgba(255,255,255,0.12);
          border: 1px solid rgba(255,255,255,0.18);
          overflow: hidden;
        }
        .hero-card .icon { font-size: 28px; line-height: 1; }
        .hero-card .value {
          position: absolute;
          left: 14px; bottom: 32px;
          font-size: 26px; font-weight: 800;
          color: var(--ivory);
          letter-spacing: -0.01em;
        }
        .hero-card .label {
          position: absolute;
          left: 14px; bottom: 10px;
          font-size: 14px; font-weight: 600;
          color: var(--ivory);
        }
        .hero-card .chev {
          position: absolute;
          right: 12px; top: 50%;
          transform: translateY(-50%);
          font-size: 18px;
          color: rgba(255,255,255,0.85);
        }

        /* ===== WHITE SHEET ===== */
        .sheet {
          position: absolute;
          left: 0; right: 0; bottom: 0;
          top: 224px;
          background: #F6F7FA;
          border-radius: 24px 24px 0 0;
          padding: 10px 16px 100px;
          overflow-y: auto;
        }
        .sheet::before {
          content: "";
          display: block;
          width: 60px; height: 4px;
          border-radius: 2px;
          background: #C9CED6;
          margin: 4px auto 12px;
        }

        .maya-card {
          display: block;
          width: 100%;
          position: relative;
          margin-bottom: 14px;
          padding: 16px 18px;
          border-radius: 16px;
          background:
            radial-gradient(circle at 92% 30%, rgba(255,233,163,0.55), transparent 42%),
            linear-gradient(135deg, #1A0508 0%, #3a1a04 60%, #1A0508 100%);
          border: 1px solid var(--champagne);
          color: var(--ivory);
          text-align: left;
          overflow: hidden;
          cursor: pointer;
          min-height: 92px;
          font-family: inherit;
          transition: transform var(--dur-fast) var(--ease-out),
                      box-shadow var(--dur-fast) var(--ease-out);
        }
        .maya-card:hover {
          transform: translateY(-1px);
          box-shadow: 0 12px 24px rgba(0,0,0,0.35);
        }
        .maya-card .badge {
          display: inline-block;
          padding: 3px 8px;
          background: var(--champagne);
          color: var(--ink);
          font-size: 10px;
          font-weight: 800;
          letter-spacing: 0.06em;
          border-radius: 4px;
          text-transform: uppercase;
        }
        .maya-card h2 {
          margin: 8px 0 4px;
          font-size: 17px;
          font-weight: 700;
          letter-spacing: -0.01em;
          max-width: 220px;
          font-family: var(--font-display);
        }
        .maya-card p {
          margin: 0;
          font-size: 12px;
          color: rgba(255,245,230,0.78);
          line-height: 1.4;
          max-width: 220px;
        }
        .maya-card .orb {
          position: absolute;
          right: -10px; top: 50%;
          transform: translateY(-50%);
          width: 88px; height: 88px;
          border-radius: 50%;
          background: radial-gradient(circle at 35% 30%,
            #fff5d1 0 12%,
            var(--champagne-soft) 36%,
            #C2362E 70%,
            #5C0810 100%);
          box-shadow: 0 0 24px rgba(255,199,44,0.45);
        }
        .maya-card .card-arrow {
          position: absolute;
          right: 16px; bottom: 16px;
          width: 28px; height: 28px;
          display: grid; place-items: center;
          border-radius: 50%;
          background: var(--champagne);
          color: var(--ink);
          font-weight: 900;
          font-size: 14px;
        }

        .tracks {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }
        .track {
          position: relative;
          height: 156px;
          padding: 14px;
          background: #FFFFFF;
          color: var(--ink);
          border-radius: 14px;
          box-shadow: 0 1px 0 rgba(0,0,0,0.04);
          overflow: hidden;
        }
        .track .title {
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: 15px;
          font-weight: 800;
          color: var(--ink);
        }
        .track .chev-circle {
          width: 22px; height: 22px;
          display: grid; place-items: center;
          border-radius: 50%;
          border: 1px solid #D0D5DD;
          font-size: 11px;
          color: #6E7480;
        }
        .track .art {
          position: absolute;
          left: 12px; right: 12px;
          top: 44px;
          height: 70px;
          display: grid;
          place-items: center;
          font-size: 42px;
        }
        .track .foot {
          position: absolute;
          left: 14px; right: 14px; bottom: 12px;
          font-size: 11px;
          color: #6E7480;
          line-height: 1.35;
        }
        .track .foot .row { display: flex; align-items: center; gap: 6px; }
        .track .foot .row + .row { margin-top: 2px; }
        .track .eye {
          position: absolute;
          right: 14px; bottom: 14px;
          color: #B3B9C3;
        }

        /* ===== CURVED BOTTOM NAV ===== */
        .nav {
          position: absolute;
          left: 0; right: 0; bottom: 0;
          height: 86px;
          z-index: 5;
          overflow: visible;
        }
        .nav-bg {
          position: absolute;
          left: 0; right: 0; top: -22px;
          width: 100%; height: 108px;
          overflow: visible;
          pointer-events: none;
        }
        .nav-items {
          position: relative;
          z-index: 1;
          height: 100%;
          display: grid;
          grid-template-columns: repeat(5, 1fr);
          align-items: end;
          padding-bottom: 12px;
        }
        .nav-item {
          display: grid;
          justify-items: center;
          gap: 4px;
          font-size: 10px;
          color: #6E7480;
          font-weight: 600;
        }
        .nav-item .ic {
          width: 22px; height: 22px;
          display: grid; place-items: center;
          font-size: 16px;
        }
        .nav-item.active { color: var(--navy); }
        .nav-item.active .badge {
          width: 44px; height: 44px;
          border-radius: 50%;
          background: #FFFFFF;
          border: 2px solid var(--navy);
          display: grid; place-items: center;
          margin-top: -28px;
          margin-bottom: 4px;
          color: var(--navy);
          font-size: 20px;
          font-weight: 800;
          box-shadow: 0 4px 10px rgba(184,24,31,0.18);
        }
        .abcd-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          grid-template-rows: 1fr 1fr;
          width: 14px; height: 14px;
          gap: 1px;
          font-size: 7px;
          font-weight: 900;
          color: var(--ink);
          line-height: 1;
        }
        .abcd-grid span { display: grid; place-items: center; }
      `}</style>
    </div>
  );
}
