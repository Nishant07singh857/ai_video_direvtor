import React from 'react';

export const ColorWheels: React.FC = () => {
  return (
    <div className="flex flex-col space-y-4 p-4 bg-gray-900 rounded-lg">
      <h3 className="text-lg font-semibold text-white">Color Wheels & Match</h3>
      <div className="flex space-x-4">
        {/* Shadows */}
        <div className="flex flex-col items-center">
          <div className="w-24 h-24 rounded-full border-2 border-gray-600 flex items-center justify-center bg-gray-800 relative cursor-crosshair">
            {/* Color wheel gradient placeholder */}
            <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-blue-500/20 via-transparent to-red-500/20 mix-blend-overlay pointer-events-none"></div>
            {/* Control point */}
            <div className="absolute w-3 h-3 bg-white rounded-full shadow border border-gray-400 top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2"></div>
          </div>
          <span className="text-xs text-gray-400 mt-2">Shadows</span>
        </div>
        
        {/* Midtones */}
        <div className="flex flex-col items-center">
          <div className="w-24 h-24 rounded-full border-2 border-gray-600 flex items-center justify-center bg-gray-800 relative cursor-crosshair">
            <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-blue-500/20 via-transparent to-red-500/20 mix-blend-overlay pointer-events-none"></div>
            <div className="absolute w-3 h-3 bg-white rounded-full shadow border border-gray-400 top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2"></div>
          </div>
          <span className="text-xs text-gray-400 mt-2">Midtones</span>
        </div>

        {/* Highlights */}
        <div className="flex flex-col items-center">
          <div className="w-24 h-24 rounded-full border-2 border-gray-600 flex items-center justify-center bg-gray-800 relative cursor-crosshair">
            <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-blue-500/20 via-transparent to-red-500/20 mix-blend-overlay pointer-events-none"></div>
            <div className="absolute w-3 h-3 bg-white rounded-full shadow border border-gray-400 top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2"></div>
          </div>
          <span className="text-xs text-gray-400 mt-2">Highlights</span>
        </div>
      </div>
    </div>
  );
};
