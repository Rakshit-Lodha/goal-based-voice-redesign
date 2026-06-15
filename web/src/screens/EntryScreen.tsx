/**
 * Entry screen — Paytm Money post-KYC dashboard with a premium Maya
 * hero card at the top. Tapping the card calls onStart() which mounts
 * the voice agent conversation surface.
 *
 * Pure decoration apart from the Maya card click target.
 */
export default function EntryScreen({ onStart }: { onStart: () => void }) {
  return (
    <div className="entry-root">
      <div className="entry-scroll">
        <div className="topbar">
          <div className="logo">₹</div>
          <div className="search">Search Stocks, F&amp;O or MF</div>
          <div className="avatar">HI</div>
        </div>

        <button className="maya-hero" onClick={onStart} aria-label="Open Maya Wealth Desk">
          <h2>Plan your first move with Maya</h2>
          <p>Your personal wealth expert is ready and will help you make your first move!</p>
          <span className="gold-cta">Start Now</span>
        </button>

        <div className="ticker">
          <span><b>NIFTY</b>23,622.90 <span className="up">+461.30 (1.99%)</span></span>
          <span><b>SENSEX</b>75,527.95 <span className="up">+1,695</span></span>
          <span className="caret">⌄</span>
        </div>

        <div className="section">
          <h3>Invest and Trade</h3>
          <a href="#" onClick={(e) => e.preventDefault()}>View All</a>
        </div>
        <div className="tiles">
          <div className="tile">Stocks <span>📈</span></div>
          <div className="tile">F&amp;O <span>📊</span></div>
          <div className="tile">Mutual Funds <span>💰</span></div>
          <div className="tile">MTF <span>⚡</span></div>
        </div>

        <div className="section">
          <h3>Portfolio Overview</h3>
          <a href="#" onClick={(e) => e.preventDefault()}>Hide 👁</a>
        </div>
        <div className="panel">
          <div className="tabs">
            <span className="active">All</span>
            <span>Stocks</span>
            <span>Mutual Funds</span>
            <span>NPS</span>
          </div>
          <div className="empty">
            <div>
              <h4>Start Investing!</h4>
              <p>You're missing out on additional gains across multiple investment products</p>
              <span className="cta">Invest Now ›</span>
            </div>
            <div className="coins" />
          </div>
          <div className="funds">
            <span>Available Funds: <strong>₹0.00</strong> · running low</span>
            <a href="#" onClick={(e) => e.preventDefault()}>₹ Add Funds</a>
          </div>
        </div>
      </div>

      <nav className="nav">
        <div className="nav-item active"><i /><span>Home</span></div>
        <div className="nav-item"><i /><span>Watchlist</span></div>
        <div className="nav-item"><i /><span>Portfolio</span></div>
        <div className="nav-item"><i /><span>Orders</span></div>
        <div className="nav-item"><i /><span>Funds</span></div>
      </nav>

      <style>{`
        .entry-root {
          position: absolute;
          inset: 0;
          color: var(--ivory);
          font-family: var(--font-body);
        }
        .entry-scroll {
          height: 100%;
          padding: 18px 16px 86px;
          overflow-y: auto;
        }

        .topbar {
          display: grid;
          grid-template-columns: 36px 1fr 40px;
          gap: 10px;
          align-items: center;
        }
        .logo {
          width: 36px; height: 36px;
          display: grid; place-items: center;
          border-radius: 8px;
          background: linear-gradient(180deg, #e9f5ff, #b9def5);
          color: #0067bd;
          font-weight: 800;
          font-size: 18px;
        }
        .search {
          height: 40px;
          padding: 0 16px;
          display: flex; align-items: center;
          border: 1px solid var(--ivory-hairline);
          border-radius: 20px;
          background: rgba(255,255,255,0.02);
          color: var(--ivory-soft);
          font-size: 14px;
        }
        .avatar {
          width: 40px; height: 40px;
          display: grid; place-items: center;
          border-radius: 50%;
          background: #11203a;
          color: #4ec9ff;
          border: 1px solid rgba(78,201,255,0.3);
          font-weight: 700;
          font-size: 13px;
        }

        .maya-hero {
          display: block;
          width: 100%;
          margin: 16px 0 0;
          position: relative;
          padding: 20px;
          border-radius: 18px;
          overflow: hidden;
          color: var(--ivory);
          text-align: left;
          background:
            radial-gradient(circle at 78% 30%, rgba(225, 197, 137, 0.22), transparent 36%),
            radial-gradient(circle at 90% 80%, rgba(122, 167, 212, 0.14), transparent 38%),
            linear-gradient(145deg, #221c10 0%, #131820 60%, #07090d 100%);
          border: 1px solid rgba(201, 169, 97, 0.32);
          cursor: pointer;
          transition: transform var(--dur-fast) var(--ease-out),
                      box-shadow var(--dur-fast) var(--ease-out);
        }
        .maya-hero:hover {
          transform: translateY(-1px);
          box-shadow: 0 12px 24px rgba(0,0,0,0.35);
        }
        .maya-hero::before {
          content: "";
          position: absolute;
          right: -40px; top: 20px;
          width: 150px; height: 150px;
          border-radius: 50%;
          background: radial-gradient(circle at 36% 30%,
            #fff5d1 0 6%,
            var(--champagne-soft) 26%,
            #6f8f9d 56%,
            #182d3e 78%);
          box-shadow: 0 0 40px rgba(201, 169, 97, 0.35);
          opacity: 0.9;
        }
        .maya-hero h2 {
          margin: 0;
          max-width: 230px;
          font-size: 24px;
          line-height: 1.15;
          font-weight: 600;
          position: relative;
          font-family: var(--font-display);
        }
        .maya-hero p {
          margin: 10px 0 16px;
          max-width: 220px;
          color: var(--ivory-soft);
          font-size: 12px;
          line-height: 1.5;
          position: relative;
        }
        .maya-hero .gold-cta {
          position: relative;
          height: 40px;
          padding: 0 20px;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          border-radius: 20px;
          color: #1a1408;
          background: linear-gradient(135deg, var(--champagne-soft), var(--champagne));
          font-weight: 700;
          font-size: 13px;
          letter-spacing: 0.01em;
          box-shadow: 0 6px 16px rgba(201, 169, 97, 0.25);
        }
        .maya-hero .gold-cta::after { content: "›"; font-size: 16px; }

        .ticker {
          margin-top: 16px;
          display: flex;
          gap: 18px;
          align-items: center;
          font-size: 13px;
          color: var(--ivory-soft);
        }
        .ticker b { color: var(--ivory); font-weight: 700; margin-right: 6px; }
        .up { color: var(--green-soft); }
        .ticker .caret { margin-left: auto; color: var(--ivory-soft); }

        .section {
          margin-top: 22px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .section h3 { margin: 0; font-size: 17px; font-weight: 700; }
        .section a {
          color: #4ec9ff;
          font-size: 13px;
          text-decoration: none;
        }

        .tiles {
          margin-top: 12px;
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 8px;
        }
        .tile {
          padding: 12px 10px;
          min-height: 72px;
          border: 1px solid var(--ivory-hairline);
          border-radius: 12px;
          background: var(--navy-soft);
          font-size: 13px;
          font-weight: 700;
          position: relative;
          overflow: hidden;
        }
        .tile span {
          position: absolute;
          right: 6px; bottom: 6px;
          font-size: 14px;
          opacity: 0.85;
        }

        .panel {
          margin-top: 12px;
          border: 1px solid var(--ivory-hairline);
          border-radius: 14px;
          background: var(--navy-soft);
          overflow: hidden;
        }
        .tabs {
          display: flex;
          gap: 22px;
          padding: 14px 16px;
          font-size: 14px;
          color: var(--ivory-soft);
          border-bottom: 1px solid var(--ivory-hairline);
        }
        .tabs .active { color: var(--ivory); position: relative; }
        .tabs .active::after {
          content: "";
          position: absolute;
          left: 0; right: 0; bottom: -15px;
          height: 2px;
          background: #4ec9ff;
        }
        .empty {
          padding: 16px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .empty h4 { margin: 0 0 6px; font-size: 16px; }
        .empty p {
          margin: 0;
          color: var(--ivory-soft);
          font-size: 12px;
          max-width: 200px;
          line-height: 1.4;
        }
        .cta {
          margin-top: 12px;
          height: 36px;
          padding: 0 16px;
          display: inline-flex;
          align-items: center;
          border-radius: 18px;
          background: linear-gradient(135deg, #4ec9ff, #0078d7);
          color: #fff;
          font-weight: 700;
          font-size: 13px;
        }
        .coins {
          width: 100px;
          height: 70px;
          background:
            radial-gradient(circle at 30% 60%, #ffbf46 12px, transparent 13px),
            radial-gradient(circle at 60% 50%, #ffbf46 14px, transparent 15px),
            radial-gradient(circle at 85% 40%, #ffbf46 16px, transparent 17px);
          opacity: 0.7;
        }
        .funds {
          padding: 10px 16px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          background: rgba(201, 119, 42, 0.16);
          font-size: 13px;
          color: #f2c89a;
        }
        .funds strong { color: var(--ivory); margin-left: 6px; }
        .funds a {
          color: #4ec9ff;
          text-decoration: none;
          font-weight: 700;
        }

        .nav {
          position: absolute;
          left: 0; right: 0; bottom: 0;
          height: 70px;
          display: grid;
          grid-template-columns: repeat(5, 1fr);
          align-items: center;
          background: rgba(15, 22, 40, 0.96);
          border-top: 1px solid var(--ivory-hairline);
          color: var(--ivory-soft);
          font-size: 10px;
        }
        .nav-item {
          display: grid;
          justify-items: center;
          gap: 4px;
        }
        .nav-item i {
          width: 18px;
          height: 18px;
          border-radius: 4px;
          border: 1.5px solid currentColor;
        }
        .nav .active { color: #4ec9ff; }
      `}</style>
    </div>
  );
}
