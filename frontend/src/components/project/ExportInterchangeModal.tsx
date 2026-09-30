import React, { useState, useEffect } from 'react';
import { useFocusTrap } from '@/lib/useFocusTrap';

interface ExportInterchangeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onExport: (format: string) => void;
}

export const ExportInterchangeModal: React.FC<ExportInterchangeModalProps> = ({
  isOpen,
  onClose,
  onExport
}) => {
  const [format, setFormat] = useState('xml');
  const modalRef = useFocusTrap(isOpen);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-70" onClick={onClose}>
      <div 
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="interchange-modal-title"
        className="bg-neutral-900 border border-neutral-700 rounded-lg shadow-xl w-96 p-6 text-neutral-200"
        onClick={e => e.stopPropagation()}
      >
        <h2 id="interchange-modal-title" className="text-xl font-semibold text-white mb-4">Export Interchange</h2>
        
        <div className="mb-6">
          <label className="block text-sm font-medium mb-2" htmlFor="format-select">
            Format
          </label>
          <select
            id="format-select"
            value={format}
            onChange={(e) => setFormat(e.target.value)}
            className="w-full bg-neutral-800 border border-neutral-700 rounded p-2 text-sm text-white focus:outline-none focus:border-blue-500"
          >
            <option value="xml">FCPXML (.xml)</option>
            <option value="aaf">AAF (.aaf)</option>
            <option value="edl">EDL (.edl)</option>
          </select>
        </div>

        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded text-sm bg-neutral-800 hover:bg-neutral-700 text-neutral-300 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onExport(format)}
            className="px-4 py-2 rounded text-sm bg-blue-600 hover:bg-blue-500 text-white font-medium transition-colors"
          >
            Export
          </button>
        </div>
      </div>
    </div>
  );
};
