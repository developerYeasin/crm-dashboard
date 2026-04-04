import { useRef, useEffect } from 'react';
import { FiSend, FiX } from 'react-icons/fi';

export default function ChatInput({
  value,
  onChange,
  onSend,
  disabled = false,
  placeholder = "Type your message...",
  inputRef: externalInputRef
}) {
  const textareaRef = useRef(null);

  // Forward ref to parent if provided
  useEffect(() => {
    if (externalInputRef && textareaRef.current) {
      externalInputRef.current = textareaRef.current;
    }
  }, [externalInputRef]);

  // Auto-resize textarea based on content
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 200) + 'px';
    }
  }, [value]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!value.trim() || disabled) return;
    onSend(value.trim());
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        rows={1}
        className="w-full px-4 py-3 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-2xl text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none resize-none overflow-hidden transition-shadow"
        style={{ minHeight: '48px' }}
        disabled={disabled}
      />
      <div className="absolute right-2 bottom-2 flex items-center gap-2">
        {value.trim() && (
          <button
            type="button"
            onClick={() => onChange('')}
            className="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500 transition-colors"
          >
            <FiX className="w-4 h-4" />
          </button>
        )}
        <button
          type="submit"
          disabled={!value.trim() || disabled}
          className="p-2 rounded-xl bg-primary-500 hover:bg-primary-600 disabled:bg-gray-300 dark:disabled:bg-gray-600 text-white transition-colors shadow-sm disabled:cursor-not-allowed"
        >
          <FiSend className="w-4 h-4" />
        </button>
      </div>
    </form>
  );
}