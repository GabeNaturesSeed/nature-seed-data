import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';
import { Providers } from './providers';
import AppShell from '@/components/layout/AppShell';

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
          <AppShell>
            {children}
          </AppShell>
        </Providers>
      </body>
    </html>
  );
}
