import React, { useState } from 'react';

interface Comment {
  id: string;
  author: string;
  timestamp: string;
  text: string;
}

export const CommentPanel: React.FC = () => {
  const [comments, setComments] = useState<Comment[]>([
    { id: '1', author: 'Director', timestamp: '00:00:15', text: 'Cut a bit earlier here.' },
    { id: '2', author: 'Editor', timestamp: '00:01:02', text: 'Color correction needed on this shot.' }
  ]);
  const [newComment, setNewComment] = useState('');

  const handleAddComment = () => {
    if (!newComment.trim()) return;
    const comment: Comment = {
      id: Date.now().toString(),
      author: 'You',
      timestamp: '00:00:00', // Hardcoded for mockup
      text: newComment
    };
    setComments([...comments, comment]);
    setNewComment('');
  };

  return (
    <div className="w-80 h-full bg-gray-900 border-l border-gray-800 flex flex-col text-gray-200">
      <div className="p-4 border-b border-gray-800">
        <h2 className="text-lg font-semibold text-gray-100">Comments</h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {comments.map((comment) => (
          <div key={comment.id} className="bg-gray-800 p-3 rounded-md border border-gray-700">
            <div className="flex justify-between items-center mb-2">
              <span className="font-medium text-sm text-gray-300">{comment.author}</span>
              <span className="text-xs text-blue-400 font-mono bg-blue-900/30 px-2 py-0.5 rounded">
                {comment.timestamp}
              </span>
            </div>
            <p className="text-sm text-gray-400">{comment.text}</p>
          </div>
        ))}
      </div>

      <div className="p-4 border-t border-gray-800 bg-gray-900">
        <textarea
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="Add a comment at current time..."
          className="w-full bg-gray-800 border border-gray-700 rounded-md p-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none h-20"
        />
        <button
          onClick={handleAddComment}
          className="mt-2 w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors text-sm"
        >
          Post Comment
        </button>
      </div>
    </div>
  );
};
