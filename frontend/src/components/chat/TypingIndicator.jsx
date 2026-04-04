export default function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex gap-4 max-w-[90%]">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white font-bold shrink-0 shadow-sm">
          AI
        </div>
        <div className="rounded-2xl rounded-bl-md px-5 py-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex gap-1.5">
            <span
              className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: '0ms' }}
            ></span>
            <span
              className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: '150ms' }}
            ></span>
            <span
              className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: '300ms' }}
            ></span>
          </div>
        </div>
      </div>
    </div>
  );
}