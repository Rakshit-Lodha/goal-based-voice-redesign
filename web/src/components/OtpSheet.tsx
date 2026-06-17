import type { FormEvent } from "react";

export type OtpRequest = {
  request_id: string;
  provider: string;
};

export default function OtpSheet({
  otp,
  value,
  error,
  submitting,
  onChange,
  onSubmit,
}: {
  otp: OtpRequest | null;
  value: string;
  error: string | null;
  submitting: boolean;
  onChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
}) {
  if (!otp) return null;

  const isAa = otp.provider.toLowerCase().includes("account aggregator");

  return (
    <form className={`otp-sheet${isAa ? " otp-sheet-aa" : ""}`} onSubmit={onSubmit}>
      <div className="otp-grabber" />
      {isAa ? <AaHeader /> : <MfCentralHeader />}

      <label className="otp-label" htmlFor="otp-input">
        OTP sent to your registered mobile
      </label>
      <input
        id="otp-input"
        value={value}
        onChange={(event) => onChange(event.target.value.replace(/\D/g, "").slice(0, 6))}
        inputMode="numeric"
        autoComplete="one-time-code"
        autoFocus
        placeholder="1234"
        aria-label={`${otp.provider} OTP`}
      />
      <div className="otp-help">Demo OTP is 1234</div>
      {error && <div className="otp-error">{error}</div>}
      <button type="submit" disabled={submitting || value.length === 0}>
        {submitting ? "Verifying..." : "Authenticate with OTP"}
      </button>
      {isAa && <div className="aa-footer">powered by <strong>RBI-regulated AA</strong> · Finvu</div>}

      <style>{`
        .otp-sheet {
          position: absolute;
          left: 16px;
          right: 16px;
          bottom: 0;
          z-index: 7;
          padding: 30px 26px 32px;
          border-radius: 28px 28px 0 0;
          background: var(--cream);
          color: var(--ink);
          box-shadow: 0 -30px 60px -20px rgba(0, 0, 0, 0.42);
          animation: otp-rise var(--dur-med) var(--ease-out) both;
        }
        .otp-sheet-aa {
          background: #ffffff;
        }
        .otp-grabber {
          width: 36px;
          height: 4px;
          margin: -10px auto 18px;
          border-radius: 999px;
          background: #d5c9b0;
        }
        .otp-sheet-aa .otp-grabber {
          background: #dddddd;
        }
        .otp-logo-row {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 16px;
        }
        .otp-logo {
          width: 40px;
          height: 40px;
          border-radius: 12px;
          display: grid;
          place-items: center;
          flex: 0 0 auto;
          background: linear-gradient(135deg, #7a4fb8 0%, #5a2fa0 100%);
          color: white;
          font-family: var(--font-display);
          font-size: 24px;
          font-weight: 600;
        }
        .otp-provider {
          color: var(--ink);
          font-family: var(--font-display);
          font-size: 22px;
          line-height: 1;
        }
        .otp-provider small {
          display: block;
          margin-top: 6px;
          color: var(--ink-soft);
          font-family: var(--font-body);
          font-size: 11px;
          letter-spacing: 0.1em;
          text-transform: uppercase;
        }
        .otp-sheet h2 {
          margin: 0;
          color: var(--ink);
          font-family: var(--font-display);
          font-size: 28px;
          font-weight: 400;
          line-height: 1.18;
        }
        .otp-sheet h2 em {
          color: var(--champagne);
          font-style: normal;
        }
        .otp-sheet-aa h2 {
          text-align: center;
          font-size: 30px;
          line-height: 1.12;
        }
        .otp-copy {
          margin: 12px 0 0;
          color: var(--ink-soft);
          font-size: 13px;
          line-height: 1.5;
        }
        .otp-sheet-aa .otp-copy {
          text-align: center;
        }
        .otp-trust {
          margin: 18px 0 0;
          padding: 0;
          list-style: none;
        }
        .otp-trust li {
          position: relative;
          margin-bottom: 10px;
          padding-left: 28px;
          color: var(--ink-soft);
          font-size: 14px;
          line-height: 1.4;
        }
        .otp-trust li::before {
          content: "";
          position: absolute;
          left: 0;
          top: 4px;
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: var(--green);
          background-image: linear-gradient(135deg, transparent 40%, rgba(255, 255, 255, 0.42) 60%);
        }
        .otp-label {
          display: block;
          margin: 20px 0 8px;
          color: var(--ink-soft);
          font-size: 10px;
          letter-spacing: 0.16em;
          text-align: center;
          text-transform: uppercase;
        }
        .otp-sheet input {
          width: 100%;
          height: 54px;
          border: 1px solid var(--cream-deep);
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.5);
          color: var(--ink);
          font-family: var(--font-display);
          font-size: 26px;
          letter-spacing: 0.2em;
          text-align: center;
          outline: none;
        }
        .otp-sheet input:focus {
          border-color: var(--champagne);
          box-shadow: 0 0 0 3px rgba(201, 169, 97, 0.18);
        }
        .otp-help {
          margin-top: 8px;
          color: var(--ink-soft);
          font-size: 11px;
          text-align: center;
        }
        .otp-error {
          margin-top: 10px;
          color: var(--amber);
          font-size: 12px;
          line-height: 1.4;
          text-align: center;
        }
        .otp-sheet button {
          width: 100%;
          height: 56px;
          margin-top: 18px;
          border-radius: 999px;
          background: var(--champagne);
          color: #1a1610;
          font-size: 16px;
          font-weight: 600;
          letter-spacing: 0.02em;
        }
        .otp-sheet-aa button {
          background: var(--ink);
          color: var(--cream);
        }
        .otp-sheet button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .aa-footer {
          margin-top: 14px;
          color: var(--ink-soft);
          font-size: 10px;
          letter-spacing: 0.1em;
          text-align: center;
          text-transform: uppercase;
        }
        .aa-footer strong {
          color: var(--ink);
          font-weight: 500;
        }
        @keyframes otp-rise {
          from { transform: translateY(120%); }
          to { transform: translateY(0); }
        }
      `}</style>
    </form>
  );
}

function MfCentralHeader() {
  return (
    <>
      <div className="otp-logo-row">
        <div className="otp-logo">m</div>
        <div className="otp-provider">MF Central<small>Portfolio · read-only</small></div>
      </div>
      <h2>Fetching for: <em>Personal Finance Management</em></h2>
      <ul className="otp-trust">
        <li>End-to-end encrypted, OTP-verified by you.</li>
        <li>One-time consent · valid for this session only.</li>
        <li>We never store your OTP or login.</li>
      </ul>
    </>
  );
}

function AaHeader() {
  return (
    <>
      <h2>let's verify your<br />mobile number</h2>
      <p className="otp-copy">
        to securely fetch the bank accounts linked to this number via <u>Account Aggregator</u>
      </p>
    </>
  );
}
