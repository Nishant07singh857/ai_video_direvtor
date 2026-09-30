'use client';

import { useState, useRef } from 'react';
import { Upload, FileText, X, Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import { Button } from '@/components/Button';
import { Card, CardContent } from '@/components/Card';
import { mediaApi } from '@/lib/api';
import { MediaAsset, MediaAssetListResponse } from '@/types';
import { cn } from '@/lib/utils';

interface MediaUploadProps {
  projectId: string;
  onMediaUploaded?: (media: MediaAsset) => void;
}

export function MediaUpload({ projectId, onMediaUploaded }: MediaUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      // Validate file type
      const validTypes = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska', 'video/webm'];
      const validExtensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm'];
      
      const ext = '.' + selectedFile.name.split('.').pop()?.toLowerCase();
      if (!validExtensions.includes(ext)) {
        setError(`Invalid file type. Supported: ${validExtensions.join(', ')}`);
        return;
      }
      
      setFile(selectedFile);
      setError('');
      setSuccess(false);
      setProgress(0);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setUploading(true);
    setError('');
    setProgress(0);
    
    try {
      const response = await mediaApi.upload(projectId, file, setProgress);
      setSuccess(true);
      setProgress(100);
      if (onMediaUploaded) {
        onMediaUploaded(response.data);
      }
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed');
      setProgress(0);
    } finally {
      setUploading(false);
    }
  };

  const removeFile = () => {
    setFile(null);
    setError('');
    setSuccess(false);
    setProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Card className="w-full">
      <CardContent className="pt-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Upload Media</h3>
        
        {!file && !success ? (
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept=".mp4,.mov,.avi,.mkv,.webm"
              onChange={handleFileSelect}
              className="hidden"
              disabled={uploading}
              aria-label="Upload media file input"
            />
            <div
              className={cn(
                'border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer',
                uploading ? 'border-gray-300 bg-gray-50' : 'border-gray-300 hover:border-primary-500 hover:bg-primary-50 focus:outline-none focus:ring-2 focus:ring-primary-500'
              )}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  fileInputRef.current?.click();
                }
              }}
              role="button"
              tabIndex={0}
              aria-label="Upload media file"
              aria-disabled={uploading}
            >
              <Upload className="mx-auto h-12 w-12 text-gray-400" aria-hidden="true" />
              <p className="mt-4 text-gray-600">
                Click to upload or drag and drop
              </p>
              <p className="mt-1 text-sm text-gray-500">
                MP4, MOV, AVI, MKV, WebM (max 5GB)
              </p>
            </div>
          </>
        ) : file && !success ? (
          <div className="space-y-4">
            <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
              <FileText className="h-10 w-10 text-primary-600" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">{file.name}</p>
                <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={removeFile}
                disabled={uploading}
              >
                <X className="h-5 w-5 text-gray-400" />
              </Button>
            </div>
            
            {uploading && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Uploading...</span>
                  <span className="font-medium text-primary-600">{progress}%</span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary-600 transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                {progress === 100 && (
                  <p className="text-sm text-green-600">Upload complete!</p>
                )}
              </div>
            )}
            
            {error && (
              <div className="flex items-center gap-2 text-sm text-red-600">
                <AlertCircle className="h-4 w-4" />
                <span>{error}</span>
              </div>
            )}
            
            {!uploading && !error && (
              <Button onClick={handleUpload} className="w-full" disabled={progress === 100}>
                <Upload className="mr-2 h-4 w-4" />
                Upload
              </Button>
            )}
          </div>
        ) : success ? (
          <div className="flex items-center gap-3 p-4 bg-green-50 rounded-lg">
            <CheckCircle className="h-8 w-8 text-green-600" />
            <div>
              <p className="font-medium text-green-800">Upload Successful!</p>
              <p className="text-sm text-green-600">Media is being processed</p>
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

interface MediaListProps {
  projectId: string;
  mediaAssets: MediaAsset[];
  onRefresh?: () => void;
}

export function MediaList({ projectId, mediaAssets, onRefresh }: MediaListProps) {
  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      uploading: 'bg-blue-100 text-blue-800',
      uploaded: 'bg-yellow-100 text-yellow-800',
      processing: 'bg-purple-100 text-purple-800',
      ready: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready': return <CheckCircle className="h-4 w-4" />;
      case 'processing': return <Loader2 className="h-4 w-4 animate-spin" />;
      case 'failed': return <AlertCircle className="h-4 w-4" />;
      default: return <Loader2 className="h-4 w-4" />;
    }
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return 'Unknown';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (mediaAssets.length === 0) {
    return (
      <div className="text-center py-12">
        <Upload className="mx-auto h-12 w-12 text-gray-300" />
        <h3 className="mt-4 text-lg font-medium text-gray-900">No media uploaded yet</h3>
        <p className="mt-2 text-gray-500">Upload your first video to get started</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Project Media ({mediaAssets.length})</h3>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {mediaAssets.map((media) => (
          <Card key={media.id} className="overflow-hidden">
            <div className="aspect-video bg-gray-100 relative">
              {media.status === 'ready' && media.width && media.height ? (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-200">
                  <FileText className="h-12 w-12 text-gray-400" />
                </div>
              ) : media.status === 'processing' ? (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
                  <Loader2 className="h-8 w-8 text-primary-600 animate-spin" />
                </div>
              ) : media.status === 'failed' ? (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
                  <AlertCircle className="h-8 w-8 text-red-500" />
                </div>
              ) : (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
                  <Upload className="h-8 w-8 text-gray-400" />
                </div>
              )}
              <div className="absolute top-2 right-2">
                <span className={cn('px-2 py-1 text-xs font-medium rounded-full', getStatusColor(media.status))}>
                  {getStatusIcon(media.status)}
                  {media.status.charAt(0).toUpperCase() + media.status.slice(1)}
                </span>
              </div>
            </div>
            <CardContent className="p-4">
              <h4 className="font-medium text-gray-900 truncate">{media.original_filename}</h4>
              <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-gray-500">
                {media.duration && (
                  <span className="flex items-center gap-1">
                    <Loader2 className="h-3.5 w-3.5" />
                    {formatDuration(media.duration)}
                  </span>
                )}
                {media.width && media.height && (
                  <span>{media.width}×{media.height}</span>
                )}
                {media.video_codec && (
                  <span className="px-2 py-0.5 text-xs bg-gray-100 rounded">{media.video_codec}</span>
                )}
              </div>
              <p className="mt-2 text-xs text-gray-400">
                {formatFileSize(media.file_size)} • {new Date(media.created_at).toLocaleDateString()}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function formatFileSize(bytes: number) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
