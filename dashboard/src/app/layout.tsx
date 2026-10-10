import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { BackgroundBackdrop } from "@/components/BackgroundBackdrop";

export const metadata: Metadata = {
  title: "GridNudge — EV Demand Flexibility Platform",
  description:
    "Safety-gated, uplift-aware EV charging persuasion & fleet peak load management system.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-navy-950 text-slate-100 antialiased selection:bg-nudge-gold/30 selection:text-nudge-yellow flex flex-col relative overflow-x-hidden">
        <BackgroundBackdrop />
        <Navbar />
        <main className="relative z-10 flex-1 px-4 sm:px-6 lg:px-8 pb-12 max-w-[1600px] w-full mx-auto">
          {children}
        </main>
      </body>
    </html>
  );
}
