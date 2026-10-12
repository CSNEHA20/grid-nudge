"use client";

import { useEffect, useRef } from "react";

/**
 * Interactive 3D hero background: a photoreal EV + charger image that
 * tilts in perspective with the pointer, floats gently, and pulses on click.
 * Pure CSS 3D transforms, no extra dependencies.
 */
export function EVScene3D() {
  const stageRef = useRef<HTMLDivElement>(null);
  const glowRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stage = stageRef.current;
    const glow = glowRef.current;
    if (!stage || !glow) return;

    const reduce =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let tx = 0.5;
    let ty = 0.5;
    let cx = 0.5;
    let cy = 0.5;
    let pulse = 0;
    let raf = 0;
    let running = true;
    const start = performance.now();

    const onMove = (e: PointerEvent) => {
      tx = e.clientX / Math.max(window.innerWidth, 1);
      ty = e.clientY / Math.max(window.innerHeight, 1);
    };
    const onDown = () => {
      pulse = 1;
    };
    const onVis = () => {
      running = !document.hidden;
      if (running) {
        cancelAnimationFrame(raf);
        raf = requestAnimationFrame(tick);
      }
    };

    const tick = (now: number) => {
      if (!running) return;
      const t = (now - start) / 1000;
      cx += (tx - cx) * 0.06;
      cy += (ty - cy) * 0.06;
      pulse *= 0.93;
      const idle = reduce ? 0 : 1;
      const ry = (cx - 0.5) * -14 + Math.sin(t * 0.4) * 2.5 * idle;
      const rx = (cy - 0.5) * 8 + Math.cos(t * 0.3) * 1.2 * idle;
      const floatY = Math.sin(t * 0.8) * 6 * idle;
      const scale = 1.02 + pulse * 0.035;
      stage.style.transform = `perspective(1400px) rotateY(${ry.toFixed(2)}deg) rotateX(${rx.toFixed(
        2
      )}deg) translate3d(${((cx - 0.5) * -24).toFixed(1)}px, ${floatY.toFixed(1)}px, 0) scale(${scale.toFixed(4)})`;
      glow.style.opacity = String(0.55 + pulse * 0.45);
      glow.style.transform = `translate3d(${((cx - 0.5) * 60).toFixed(1)}px, ${((cy - 0.5) * 30).toFixed(1)}px, 0)`;
      raf = requestAnimationFrame(tick);
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerdown", onDown, { passive: true });
    document.addEventListener("visibilitychange", onVis);
    raf = requestAnimationFrame(tick);

    return () => {
      running = false;
      cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerdown", onDown);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, []);

  return (
    <div aria-hidden="true" className="absolute inset-0 overflow-hidden">
      {/* cyan energy glow behind the car */}
      <div
        ref={glowRef}
        className="absolute left-1/2 top-1/2 h-[70vh] w-[80vw] -translate-x-1/2 -translate-y-1/2 rounded-full"
        style={{
          background:
            "radial-gradient(ellipse at center, rgba(34,211,238,0.22) 0%, rgba(14,165,233,0.08) 45%, transparent 70%)",
          filter: "blur(30px)",
        }}
      />
      <div
        ref={stageRef}
        className="absolute inset-0 will-change-transform"
        style={{
          backgroundImage: "url(/ev-hero.jpg)",
          backgroundSize: "cover",
          backgroundPosition: "center 55%",
          backgroundRepeat: "no-repeat",
          mixBlendMode: "screen",
          opacity: 0.95,
          WebkitMaskImage:
            "radial-gradient(ellipse 75% 70% at 50% 52%, #000 55%, transparent 100%)",
          maskImage:
            "radial-gradient(ellipse 75% 70% at 50% 52%, #000 55%, transparent 100%)",
        }}
      />
    </div>
  );
}
