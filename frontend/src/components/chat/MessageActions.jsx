import { FiCopy, FiThumbsUp, FiThumbsDown } from 'react-icons/fi';

export default function MessageActions({ message, onCopy, onFeedback }) {
  const handleCopy = () => {
    if (onCopy) {
      onCopy(message.content);
    } else {
      navigator.clipboard.writeText(message.content);
    }
  };

  return (
    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
      <button
        onClick={handleCopy}
        className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        title="Copy message"
      >
        <FiCopy className="w-3 h-3" />
      </button>
      <button
        onClick={() => onFeedback?.(message.id, 'up')}
        className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-green-600"
        title="Good response"
      >
        <FiThumbsUp className="w-3 h-3" />
      </button>
      <button
        onClick={() => onFeedback?.(message.id, 'down')}
        className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-red-600"
        title="Poor response"
      >
        <FiThumbsDown className="w-3 h-3" />
      </button>
    </div>
  );
}