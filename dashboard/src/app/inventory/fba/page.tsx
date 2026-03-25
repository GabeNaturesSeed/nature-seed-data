'use client';

export default function FbaPage() {
  return (
    <div>
      <div className="flex items-baseline justify-between mb-8">
        <h1 className="text-2xl font-display font-bold text-brand-neutral">FBA Inventory</h1>
      </div>

      <div className="bg-surface-lowest rounded-xl shadow-ambient">
        <div className="p-8 text-center">
          <p className="text-lg text-brand-neutral/50 mb-2">FBA Inventory View</p>
          <p className="text-sm text-brand-neutral/40">
            FBA inventory data will appear here once the Amazon FBA sync is configured.
            This view will show inbound shipments, FBA stock levels, and restock recommendations.
          </p>
        </div>
      </div>
    </div>
  );
}
