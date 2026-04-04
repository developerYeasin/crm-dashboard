import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { format, isToday, isYesterday } from 'date-fns';
import MessageActions from './MessageActions';

export default function ChatMessage({ message, isUser,userName,onCopy,onFeedback,showTimestamp = true }) {
  const [showFullTime, setShowFullTime] = useState(false);

  const formatMessageDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    if (isToday(date)) return format(date, 'HH:mm');
    if (isYesterday(date)) return `Yesterday ${format(date, 'HH:mm')}`;
    return format(date, 'MMM d, HH:mm');
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex gap-4 max-w-[90%] ${isUser ? 'flex-row-reverse' : ''}`}>
        {/* Avatar */}
        {!isUser && (
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white font-bold shrink-0 shadow-sm">
            AI
          </div>
        )}
        {isUser && (
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gray-600 to-gray-800 flex items-center justify-center text-white font-medium shrink-0 shadow-sm">
            {userName?.charAt(0)?.toUpperCase() || 'U'}
          </div>
        )}

        {/* Message bubble */}
        <div className="flex flex-col group">
          <div
            className={`rounded-2xl px-5 py-3 group ${
              isUser
                ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-br-md'
                : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-bl-md border border-gray-200 dark:border-gray-700 shadow-sm'
            }`}
          >
            {isUser ? (
              <div className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</div>
            ) : (
              <div className="prose prose-sm dark:prose-invert max-w-none prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-code:text-pink-600 dark:prose-code:text-pink-400 prose-code:before:content-none prose-code:after:content-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content}
                </ReactMarkdown>
              </div>
            )}
          </div>

          {/* Message meta & actions */}
          {showTimestamp && (
            <div className={`flex items-center gap-3 mt-1.5 ${isUser ? 'justify-end' : 'justify-start'}`}>
              <span
                className="text-xs text-gray-400 dark:text-gray-500 cursor-help"
                title={showFullTime ? '' : formatMessageDate(message.created_at)}
                onMouseEnter={() => setShowFullTime(true)}
                onMouseLeave={() => setShowFullTime(false)}
              >
                {showFullTime
                  ? new Date(message.created_at).toLocaleString()
                  : formatMessageDate(message.created_at)
                }
              </span>

              {!isUser && (
                <MessageActions
                  message={message}
                  onCopy={onCopy}
                  onFeedback={onFeedback}
                />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}