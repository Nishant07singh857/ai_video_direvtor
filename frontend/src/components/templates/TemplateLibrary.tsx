import React, { useState } from 'react';

export interface Template {
  id: string;
  name: string;
  description: string;
  thumbnailUrl?: string;
}

const MOCK_TEMPLATES: Template[] = [
  { id: '1', name: 'Fast Paced Vlog', description: 'Quick cuts and high energy.' },
  { id: '2', name: 'Cinematic Montage', description: 'Smooth transitions with dramatic music.' },
  { id: '3', name: 'TikTok Trend', description: 'Optimized for short form viral content.' },
  { id: '4', name: 'Gaming Highlights', description: 'Action-packed compilation style.' },
];

export const TemplateLibrary: React.FC = () => {
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setUploadedFiles(Array.from(e.target.files));
    }
  };

  const handleApply = () => {
    if (selectedTemplate && uploadedFiles.length > 0) {
      console.log('Applying template:', selectedTemplate, 'to files:', uploadedFiles);
      // Trigger API or parent handler
    }
  };

  return (
    <div className="flex flex-col h-full w-full bg-neutral-900 text-neutral-200 p-6">
      <h2 className="text-2xl font-semibold mb-6">Template Library</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {MOCK_TEMPLATES.map((template) => (
          <div
            key={template.id}
            className={`flex flex-col p-4 rounded-lg cursor-pointer border-2 transition-colors ${
              selectedTemplate === template.id
                ? 'border-blue-500 bg-neutral-800'
                : 'border-neutral-700 bg-neutral-800/50 hover:bg-neutral-800 hover:border-neutral-600'
            }`}
            onClick={() => setSelectedTemplate(template.id)}
          >
            <div className="h-32 bg-neutral-700 rounded mb-3 flex items-center justify-center text-neutral-500">
              {template.thumbnailUrl ? (
                <img src={template.thumbnailUrl} alt={template.name} className="h-full w-full object-cover rounded" />
              ) : (
                <span className="text-sm">No Preview</span>
              )}
            </div>
            <h3 className="text-lg font-medium text-neutral-100">{template.name}</h3>
            <p className="text-sm text-neutral-400 mt-1">{template.description}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-col border border-neutral-700 rounded-lg p-6 bg-neutral-800">
        <h3 className="text-lg font-medium text-neutral-100 mb-4">Upload Raw Media</h3>
        <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-neutral-600 rounded-lg cursor-pointer hover:bg-neutral-700/50 transition-colors">
          <div className="flex flex-col items-center justify-center pt-5 pb-6">
            <svg className="w-8 h-8 mb-4 text-neutral-400" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 20 16">
              <path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 13h3a3 3 0 0 0 0-6h-.025A5.56 5.56 0 0 0 16 6.5 5.5 5.5 0 0 0 5.207 5.021C5.137 5.017 5.071 5 5 5a4 4 0 0 0 0 8h2.167M10 15V6m0 0L8 8m2-2 2 2"/>
            </svg>
            <p className="mb-2 text-sm text-neutral-400"><span className="font-semibold">Click to upload</span> or drag and drop</p>
            <p className="text-xs text-neutral-500">MP4, MOV, or WEBM</p>
          </div>
          <input type="file" className="hidden" multiple accept="video/*" onChange={handleFileUpload} />
        </label>
        
        {uploadedFiles.length > 0 && (
          <div className="mt-4">
            <p className="text-sm font-medium text-neutral-300 mb-2">Selected files:</p>
            <ul className="text-sm text-neutral-400 space-y-1">
              {uploadedFiles.map((file, idx) => (
                <li key={idx} className="truncate">{file.name}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="mt-6 flex justify-end">
        <button
          className={`px-6 py-2 rounded font-medium transition-colors ${
            selectedTemplate && uploadedFiles.length > 0
              ? 'bg-blue-600 hover:bg-blue-700 text-white'
              : 'bg-neutral-700 text-neutral-500 cursor-not-allowed'
          }`}
          disabled={!selectedTemplate || uploadedFiles.length === 0}
          onClick={handleApply}
        >
          Create Project
        </button>
      </div>
    </div>
  );
};
