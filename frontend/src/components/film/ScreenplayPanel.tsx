import React from 'react';

export interface DialogueLine {
  id: string;
  character: string;
  text: string;
  linkedTakeId?: string;
}

export interface Scene {
  id: string;
  heading: string;
  dialogue: DialogueLine[];
}

interface ScreenplayPanelProps {
  scenes: Scene[];
  onLinkTake: (dialogueId: string) => void;
}

export const ScreenplayPanel: React.FC<ScreenplayPanelProps> = ({
  scenes,
  onLinkTake,
}) => {
  return (
    <div className="flex flex-col h-full w-64 bg-neutral-900 border-l border-neutral-800 text-neutral-200 overflow-hidden">
      <div className="p-3 border-b border-neutral-800 bg-neutral-900 sticky top-0 z-10">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-neutral-400">Screenplay</h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {scenes.map((scene) => (
          <div key={scene.id} className="space-y-4">
            <h3 className="text-sm font-bold text-neutral-100 bg-neutral-800 p-1.5 rounded uppercase">
              {scene.heading}
            </h3>
            
            <div className="space-y-3 pl-2">
              {scene.dialogue.map((line) => (
                <div key={line.id} className="flex flex-col group">
                  <span className="text-xs font-semibold text-neutral-400 uppercase text-center w-full block mb-1">
                    {line.character}
                  </span>
                  <p className="text-sm text-neutral-200 text-center w-full px-4 mb-2">
                    "{line.text}"
                  </p>
                  
                  <div className="flex justify-center">
                    {line.linkedTakeId ? (
                      <span className="text-xs bg-green-900/50 text-green-400 px-2 py-1 rounded border border-green-800/50">
                        Take Linked ({line.linkedTakeId.substring(0, 4)})
                      </span>
                    ) : (
                      <button
                        onClick={() => onLinkTake(line.id)}
                        className="text-xs bg-neutral-800 hover:bg-neutral-700 text-neutral-300 px-2 py-1 rounded border border-neutral-700 transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                      >
                        Link Active Take
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
        {scenes.length === 0 && (
          <div className="text-sm text-neutral-500 text-center mt-10">
            No screenplay loaded.
          </div>
        )}
      </div>
    </div>
  );
};
