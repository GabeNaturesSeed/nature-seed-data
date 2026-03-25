'use client';

import { useState, useMemo } from 'react';
import { useJsonData } from '@/hooks/useJsonData';
import { KlaviyoData, KlaviyoCampaign } from '@/lib/types';
import { Skeleton, Button, Modal, ModalBackdrop, ModalContainer, ModalDialog, ModalHeader, ModalHeading, ModalBody, ModalCloseTrigger, Chip, useOverlayState } from '@heroui/react';

function statusColor(status: string): 'success' | 'accent' | 'default' {
  const s = status.toLowerCase();
  if (s === 'sent') return 'success';
  if (s === 'scheduled') return 'accent';
  return 'default';
}

function statusPillClass(status: string): string {
  const s = status.toLowerCase();
  if (s === 'sent') return 'bg-brand-primary/10 text-brand-primary';
  if (s === 'scheduled') return 'bg-brand-secondary/10 text-brand-secondary';
  return 'bg-surface-low text-brand-neutral/60';
}

export default function CalendarPage() {
  const { data, loading } = useJsonData<KlaviyoData>('klaviyo');
  const [viewDate, setViewDate] = useState(() => new Date(2026, 2, 1)); // March 2026
  const [selected, setSelected] = useState<KlaviyoCampaign | null>(null);
  const modalState = useOverlayState();

  const year = viewDate.getFullYear();
  const month = viewDate.getMonth();

  const campaigns = data?.campaigns ?? [];

  // Group campaigns by date
  const campaignsByDate = useMemo(() => {
    const map: Record<string, KlaviyoCampaign[]> = {};
    campaigns.forEach(c => {
      const dt = new Date(c.send_time);
      const key = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`;
      if (!map[key]) map[key] = [];
      map[key].push(c);
    });
    return map;
  }, [campaigns]);

  // Calendar grid
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const weeks: (number | null)[][] = [];
  let week: (number | null)[] = Array(firstDay).fill(null);

  for (let d = 1; d <= daysInMonth; d++) {
    week.push(d);
    if (week.length === 7) {
      weeks.push(week);
      week = [];
    }
  }
  if (week.length > 0) {
    while (week.length < 7) week.push(null);
    weeks.push(week);
  }

  const today = new Date();
  const isToday = (d: number) => today.getFullYear() === year && today.getMonth() === month && today.getDate() === d;

  const monthName = viewDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  const prevMonth = () => setViewDate(new Date(year, month - 1, 1));
  const nextMonth = () => setViewDate(new Date(year, month + 1, 1));

  const openCampaign = (c: KlaviyoCampaign) => {
    setSelected(c);
    modalState.open();
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48 rounded-xl" />
        <Skeleton className="h-[500px] rounded-xl" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-baseline justify-between mb-6 md:mb-8">
        <h1 className="text-xl md:text-2xl font-display font-bold text-brand-neutral">Content Calendar</h1>
        <span className="text-[10px] md:text-xs text-brand-neutral/50">As of {data?.as_of ?? ''}</span>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3 mb-5">
        <Button size="sm" variant="outline" onPress={prevMonth}>Prev</Button>
        <span className="text-base font-display font-semibold text-brand-primary min-w-[160px] text-center">{monthName}</span>
        <Button size="sm" variant="outline" onPress={nextMonth}>Next</Button>
      </div>

      {/* Calendar Grid */}
      <div className="bg-surface-lowest rounded-xl shadow-ambient overflow-x-auto">
        <div className="min-w-[500px]">
        {/* Day of week headers */}
        <div className="grid grid-cols-7 bg-surface-low">
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(d => (
            <div key={d} className="px-2 py-2.5 text-center text-[10px] md:text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">
              {d}
            </div>
          ))}
        </div>

        {/* Weeks */}
        {weeks.map((w, wi) => (
          <div key={wi} className="grid grid-cols-7">
            {w.map((d, di) => {
              const dateKey = d ? `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}` : '';
              const dayCampaigns = d ? (campaignsByDate[dateKey] ?? []) : [];

              return (
                <div
                  key={di}
                  className={`min-h-[80px] md:min-h-[100px] p-1.5 md:p-2 ${!d ? 'bg-surface-low' : ''} ${di < 6 ? 'border-r border-brand-outline/10' : ''} ${wi < weeks.length - 1 ? 'border-b border-brand-outline/10' : ''}`}
                >
                  {d && (
                    <>
                      <div className={`text-xs mb-1 font-medium ${isToday(d) ? 'bg-brand-primary text-white w-5 h-5 rounded-full flex items-center justify-center' : 'text-brand-neutral/50'}`}>
                        {d}
                      </div>
                      {dayCampaigns.slice(0, 3).map(c => (
                        <button
                          key={c.id}
                          onClick={() => openCampaign(c)}
                          className={`block w-full text-left text-[10px] px-1.5 py-0.5 rounded-md mb-0.5 truncate cursor-pointer ${statusPillClass(c.status)}`}
                          title={c.name}
                        >
                          {c.name}
                        </button>
                      ))}
                      {dayCampaigns.length > 3 && (
                        <span className="text-[10px] text-brand-neutral/40">+{dayCampaigns.length - 3} more</span>
                      )}
                    </>
                  )}
                </div>
              );
            })}
          </div>
        ))}
        </div>
      </div>

      {/* Campaign Detail Modal */}
      <Modal state={modalState}>
        <ModalBackdrop isDismissable />
        <ModalContainer size="sm">
          <ModalDialog>
            <ModalHeader>
              <ModalHeading className="text-brand-primary text-base font-display">{selected?.name ?? ''}</ModalHeading>
              <ModalCloseTrigger />
            </ModalHeader>
            <ModalBody>
              {selected && (
                <div className="space-y-3 text-sm pb-4">
                  <div className="flex justify-between">
                    <span className="text-brand-neutral/50">Status</span>
                    <Chip size="sm" color={statusColor(selected.status)} variant="soft">{selected.status}</Chip>
                  </div>
                  <div className="flex justify-between pt-2" style={{ borderTop: '1px solid rgba(191,201,193,0.15)' }}>
                    <span className="text-brand-neutral/50">Send Time</span>
                    <span>{new Date(selected.send_time).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</span>
                  </div>
                  {selected.subject && (
                    <div className="flex justify-between pt-2" style={{ borderTop: '1px solid rgba(191,201,193,0.15)' }}>
                      <span className="text-brand-neutral/50">Subject</span>
                      <span className="text-right max-w-[200px]">{selected.subject}</span>
                    </div>
                  )}
                  {selected.segment_name && (
                    <div className="flex justify-between pt-2" style={{ borderTop: '1px solid rgba(191,201,193,0.15)' }}>
                      <span className="text-brand-neutral/50">Segment</span>
                      <span className="text-right max-w-[200px]">{selected.segment_name}</span>
                    </div>
                  )}
                </div>
              )}
            </ModalBody>
          </ModalDialog>
        </ModalContainer>
      </Modal>
    </div>
  );
}
