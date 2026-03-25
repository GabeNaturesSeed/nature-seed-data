'use client';

import { useJsonData } from '@/hooks/useJsonData';
import { NotesData } from '@/lib/types';
import { Skeleton } from '@heroui/react';

export default function NotesPage() {
  const { data, loading } = useJsonData<NotesData>('notes');

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48 rounded-xl" />
        <Skeleton className="h-96 rounded-xl" />
      </div>
    );
  }

  if (!data) return <p className="text-brand-neutral/50">Notes data unavailable</p>;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-6 md:mb-8">
        <h1 className="text-xl md:text-2xl font-display font-bold text-brand-neutral">Notes &amp; Commentary</h1>
        <span className="text-[10px] md:text-xs text-brand-neutral/50">As of {data.as_of}</span>
      </div>

      <div className="bg-surface-lowest rounded-xl shadow-ambient">
        <div className="p-6 sm:p-8">
          <div
            className="prose prose-sm max-w-none
              [&_h1]:text-brand-primary [&_h1]:text-xl [&_h1]:font-display [&_h1]:font-bold [&_h1]:mb-3 [&_h1]:mt-5
              [&_h2]:text-brand-primary [&_h2]:text-lg [&_h2]:font-display [&_h2]:font-semibold [&_h2]:mb-3 [&_h2]:mt-5
              [&_h3]:text-brand-primary [&_h3]:text-base [&_h3]:font-semibold [&_h3]:mb-2 [&_h3]:mt-4
              [&_p]:text-sm [&_p]:mb-3 [&_p]:leading-relaxed [&_p]:text-brand-neutral
              [&_ul]:text-sm [&_ul]:mb-3 [&_ul]:ml-5 [&_ul]:list-disc
              [&_ol]:text-sm [&_ol]:mb-3 [&_ol]:ml-5 [&_ol]:list-decimal
              [&_li]:mb-1
              [&_strong]:font-semibold
              [&_hr]:my-6 [&_hr]:border-brand-outline/20"
            dangerouslySetInnerHTML={{ __html: data.html }}
          />
        </div>
      </div>
    </div>
  );
}
