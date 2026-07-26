import type { ReactNode } from "react";

/**
 * Centred phone-sized viewport for the affluent redesign.
 *
 * Desktop: a 390×844 rounded rectangle, hairline border, soft shadow, centred
 * on the navy-soft body background. Mobile (≤480px): full-bleed — the frame
 * collapses to the real viewport, no chrome.
 *
 * A clean rounded rectangle keeps the product demo focused on the experience.
 * A full device mockup (notch/bezel) competes with the orb visually and reads
 * kitsch at interview-premium register.
 */
export default function PhoneFrame({ children }: { children?: ReactNode }) {
  return (
    <div className="phone-stage">
      <div className="phone-frame">{children}</div>

      <style>{`
        .phone-stage {
          position: fixed;
          inset: 0;
          display: grid;
          place-items: center;
        }

        .phone-frame {
          position: relative;
          width: var(--phone-w);
          height: var(--phone-h);
          max-height: 100dvh;
          border-radius: var(--phone-radius);
          background:
            radial-gradient(120% 60% at 50% 0%, rgba(88, 214, 177, 0.08), transparent 60%),
            var(--navy);
          box-shadow:
            0 1px 0 0 rgba(245, 237, 219, 0.04) inset,
            0 40px 80px -20px rgba(0, 0, 0, 0.6),
            0 0 0 1px var(--ivory-hairline);
          overflow: hidden;
          isolation: isolate;
        }

        @media (max-width: 480px) {
          .phone-stage { place-items: stretch; }
          .phone-frame {
            width: 100vw;
            height: 100dvh;
            border-radius: 0;
            box-shadow: none;
          }
        }
      `}</style>
    </div>
  );
}
