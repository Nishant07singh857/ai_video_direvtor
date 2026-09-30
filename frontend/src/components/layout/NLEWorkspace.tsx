import React, { ReactNode } from 'react';

interface NLEWorkspaceProps {
  sidebarLeft?: ReactNode;
  monitor?: ReactNode;
  sidebarRight?: ReactNode;
  timeline?: ReactNode;
}

export function NLEWorkspace({
  sidebarLeft,
  monitor,
  sidebarRight,
  timeline,
}: NLEWorkspaceProps) {
  return (
    <div className="h-screen w-screen bg-nle-bg text-nle-text flex flex-col overflow-hidden">
      {/* Top Section - 3 columns */}
      <div className="flex-1 grid grid-cols-[20%_1fr_20%] min-h-0">
        
        {/* Left Panel - Media Bin */}
        <div className="bg-nle-panel border-r border-nle-border flex flex-col overflow-hidden">
          <div className="h-8 border-b border-nle-border bg-nle-panelLight flex items-center px-3 text-nle-xs font-semibold tracking-wider text-nle-textMuted uppercase">
            Project
          </div>
          <div className="flex-1 overflow-auto p-2">
            {sidebarLeft || <div className="text-nle-textMuted text-center mt-10">Empty Bin</div>}
          </div>
        </div>

        {/* Center Panel - Video Monitor */}
        <div className="bg-nle-bg flex flex-col overflow-hidden">
           <div className="h-8 border-b border-nle-border bg-nle-panelLight flex items-center px-3 text-nle-xs font-semibold tracking-wider text-nle-textMuted uppercase justify-center">
            Program
          </div>
          <div className="flex-1 p-2 flex items-center justify-center relative">
            {monitor || <div className="text-nle-textMuted">No Media</div>}
          </div>
        </div>

        {/* Right Panel - Inspector */}
        <div className="bg-nle-panel border-l border-nle-border flex flex-col overflow-hidden">
          <div className="h-8 border-b border-nle-border bg-nle-panelLight flex items-center px-3 text-nle-xs font-semibold tracking-wider text-nle-textMuted uppercase">
            Inspector
          </div>
          <div className="flex-1 overflow-auto p-2">
            {sidebarRight || <div className="text-nle-textMuted text-center mt-10">No Selection</div>}
          </div>
        </div>

      </div>

      {/* Bottom Section - Timeline */}
      <div className="h-[40%] bg-nle-panel border-t border-nle-border flex flex-col overflow-hidden min-h-[300px]">
        <div className="h-8 border-b border-nle-border bg-nle-panelLight flex items-center px-3 text-nle-xs font-semibold tracking-wider text-nle-textMuted uppercase">
          Timeline
        </div>
        <div className="flex-1 overflow-hidden relative">
          {timeline || <div className="text-nle-textMuted flex items-center justify-center h-full">Empty Timeline</div>}
        </div>
      </div>
    </div>
  );
}
