import { EVScene3D } from "./EVScene3D";

export function BackgroundBackdrop() {
  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
      {/* Interactive 3D EV + charger scene */}
      <EVScene3D />
      {/* Ambient gradient glows */}
      <div className="absolute -top-32 right-1/4 w-[600px] h-[600px] bg-amber-500/10 rounded-full blur-[140px]" />
      <div className="absolute bottom-10 left-10 w-[600px] h-[600px] bg-sky-900/15 rounded-full blur-[140px]" />
    </div>
  );
}
