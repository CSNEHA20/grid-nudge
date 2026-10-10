export function BackgroundBackdrop() {
  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
      {/* Ambient gradient glows */}
      <div className="absolute -top-32 right-1/4 w-[600px] h-[600px] bg-amber-500/10 rounded-full blur-[140px]" />
      <div className="absolute top-1/3 -right-20 w-[500px] h-[500px] bg-orange-600/15 rounded-full blur-[120px]" />
      <div className="absolute bottom-10 left-10 w-[600px] h-[600px] bg-sky-900/15 rounded-full blur-[140px]" />

      {/* Horizon mountain ridges SVG */}
      <svg
        className="absolute bottom-0 left-0 right-0 w-full h-[55vh] opacity-35"
        preserveAspectRatio="none"
        viewBox="0 0 1440 450"
        fill="none"
      >
        {/* Distant ridge */}
        <path
          d="M0 280 Q320 200 680 250 T1440 210 L1440 450 L0 450 Z"
          fill="#131e30"
          opacity="0.6"
        />
        {/* Mid-distance ridge with warm highlight rim */}
        <path
          d="M0 320 Q400 240 850 300 T1440 260 L1440 450 L0 450 Z"
          fill="#101929"
          opacity="0.8"
        />
        {/* Foreground rolling ridge */}
        <path
          d="M0 360 Q280 290 600 340 T1150 320 T1440 340 L1440 450 L0 450 Z"
          fill="#0c1320"
          opacity="0.95"
        />
      </svg>
    </div>
  );
}
