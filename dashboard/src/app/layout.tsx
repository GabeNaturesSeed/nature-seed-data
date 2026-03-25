import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';
import { Providers } from './providers';
import Sidebar from '@/components/layout/Sidebar';

export const metadata: Metadata = {
  title: "Nature's Seed - Operations Dashboard",
  description: 'Ecommerce operations dashboard for Nature\'s Seed',
};

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <html lang="en" className="light">
      <body>
        <Providers>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 p-8 bg-surface overflow-x-hidden">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
