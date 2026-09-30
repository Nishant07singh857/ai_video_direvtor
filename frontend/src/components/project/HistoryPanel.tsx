import React from 'react';

interface HistoryItem {
  id: string;
  type: 'autosave' | 'version';
  timestamp: string;
  label: string;
}

const DUMMY_HISTORY: HistoryItem[] = [
  { id: '1', type: 'autosave', timestamp: '10:00 AM', label: 'Autosave 1' },
  { id: '2', type: 'version', timestamp: '09:30 AM', label: 'V1 - Rough Cut' },
];

export const HistoryPanel: React.FC = () => {
  const handleRestore = (id: string) => {
    console.log(`Restoring history item: ${id}`);
  };

  return (
    <div className="flex flex-col h-full bg-neutral-900 text-neutral-300 p-4 w-64 border-l border-neutral-800 text-sm">
      <h2 className="text-white font-semibold mb-4 uppercase tracking-wider text-xs">History & Versions</h2>
      <div className="flex flex-col gap-2 overflow-y-auto">
        {DUMMY_HISTORY.map((item) => (
          <div key={item.id} className="bg-neutral-800 p-3 rounded flex flex-col gap-2 border border-neutral-700 hover:border-neutral-600 transition-colors">
            <div className="flex justify-between items-start">
              <span className="font-medium text-neutral-200">{item.label}</span>
              <span className="text-xs text-neutral-500 bg-neutral-900 px-1.5 py-0.5 rounded">{item.type}</span>
            </div>
            <div className="text-xs text-neutral-400">{item.timestamp}</div>
            <button
              onClick={() => handleRestore(item.id)}
              className="mt-1 bg-neutral-700 hover:bg-neutral-600 text-white py-1 px-2 rounded text-xs transition-colors"
            >
              Restore
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
