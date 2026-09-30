import React, { useState } from 'react';

export interface TranscriptWord {
  id: string;
  text: string;
  start: number;
  end: number;
  isFiller?: boolean;
  isSilence?: boolean;
}

export interface TranscriptPanelProps {
  words: TranscriptWord[];
  onDeleteSegment: (start: number, end: number) => void;
  onRemoveFillers: () => void;
  onRemoveSilences: () => void;
}

export const TranscriptPanel: React.FC<TranscriptPanelProps> = ({
  words,
  onDeleteSegment,
  onRemoveFillers,
  onRemoveSilences
}) => {
  const [selectedWordIds, setSelectedWordIds] = useState<Set<string>>(new Set());

  const handleWordClick = (wordId: string, event: React.MouseEvent) => {
    const newSelection = new Set(selectedWordIds);
    // Simple toggle logic. Can be extended to range selection with Shift key.
    if (newSelection.has(wordId)) {
      newSelection.delete(wordId);
    } else {
      newSelection.add(wordId);
    }
    setSelectedWordIds(newSelection);
  };

  const handleDeleteSelected = () => {
    if (selectedWordIds.size === 0) return;
    
    const selectedWords = words.filter(w => selectedWordIds.has(w.id));
    if (selectedWords.length > 0) {
      // Provide the continuous range of min start to max end,
      // or this could be implemented as multiple segment deletions.
      const minStart = Math.min(...selectedWords.map(w => w.start));
      const maxEnd = Math.max(...selectedWords.map(w => w.end));
      onDeleteSegment(minStart, maxEnd);
      setSelectedWordIds(new Set()); // Clear selection after delete
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white p-4">
      <div className="flex justify-between items-center mb-4 border-b border-gray-700 pb-2">
        <h2 className="text-xl font-bold">Transcript</h2>
        <div className="flex space-x-2">
          <button 
            onClick={onRemoveFillers}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium transition-colors"
          >
            Remove Fillers
          </button>
          <button 
            onClick={onRemoveSilences}
            className="px-3 py-1.5 bg-green-600 hover:bg-green-700 rounded text-sm font-medium transition-colors"
          >
            Remove Silences
          </button>
          <button 
            onClick={handleDeleteSelected}
            disabled={selectedWordIds.size === 0}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
              selectedWordIds.size > 0 
                ? 'bg-red-600 hover:bg-red-700' 
                : 'bg-gray-700 text-gray-400 cursor-not-allowed'
            }`}
          >
            Delete Selected
          </button>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto bg-gray-800 p-6 rounded-lg border border-gray-700 shadow-inner">
        <div className="leading-loose text-lg">
          {words.length === 0 ? (
            <div className="text-gray-500 text-center mt-10">No transcript available.</div>
          ) : (
            words.map((word) => {
              const isSelected = selectedWordIds.has(word.id);
              let wordClass = "cursor-pointer inline-block mx-0.5 px-1 rounded transition-colors ";
              
              if (isSelected) {
                wordClass += "bg-blue-500 text-white";
              } else if (word.isFiller) {
                wordClass += "bg-yellow-900/50 text-yellow-400 underline decoration-yellow-500 decoration-dotted";
              } else if (word.isSilence) {
                wordClass += "text-gray-500 italic opacity-50";
              } else {
                wordClass += "hover:bg-gray-700";
              }

              return (
                <span
                  key={word.id}
                  className={wordClass}
                  onClick={(e) => handleWordClick(word.id, e)}
                  title={`[${word.start.toFixed(2)}s - ${word.end.toFixed(2)}s]`}
                >
                  {word.isSilence ? '[silence]' : word.text}
                </span>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
