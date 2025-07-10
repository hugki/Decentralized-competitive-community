import './globals.css';
import type { ReactNode } from 'react';

export const metadata = {
  title: 'LLM Bench Leaderboard',
  description: 'Hourly‑updated benchmark ranking',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900">
        <header className="border-b mb-6 p-4 bg-white shadow-sm">
          <h1 className="text-xl font-semibold">LLM Bench Leaderboard</h1>
        </header>
        <main className="px-4">{children}</main>
      </body>
    </html>
  );
}
