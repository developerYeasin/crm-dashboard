import { FiSun, FiZap, FiMessageSquare, FiFileText, FiFilter, FiArrowRight } from 'react-icons/fi';

const SUGGESTION_PROMPTS = [
  { icon: FiSun, text: "Explain a complex concept", prompt: "Explain quantum computing in simple terms" },
  { icon: FiZap, text: "Brainstorm ideas", prompt: "Give me 10 innovative product ideas for sustainability" },
  { icon: FiMessageSquare, text: "Help me write", prompt: "Help me draft a professional email to decline a meeting" },
  { icon: FiFileText, text: "Summarize content", prompt: "Summarize the key principles of effective communication" },
  { icon: FiFilter, text: "Analyze data", prompt: "What are the main trends in AI adoption in 2024?" },
  { icon: FiArrowRight, text: "Plan a project", prompt: "Create a project plan for launching a mobile app" },
];

export default function SuggestionChips({ onSelect,className = "" }) {
  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 ${className}`}>
      {SUGGESTION_PROMPTS.map((suggestion, idx) => {
        const Icon = suggestion.icon;
        return (
          <button
            key={idx}
            onClick={() => onSelect(suggestion)}
            className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:border-primary-500 dark:hover:border-primary-500 hover:shadow-md transition-all group text-left"
          >
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 rounded-lg bg-primary-100 dark:bg-primary-900/50 flex items-center justify-center group-hover:bg-primary-200 dark:group-hover:bg-primary-800/50">
                <Icon className="w-4 h-4 text-primary-600 dark:text-primary-400" />
              </div>
              <span className="font-medium text-gray-900 dark:text-white text-sm">{suggestion.text}</span>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
              {suggestion.prompt}
            </p>
          </button>
        );
      })}
    </div>
  );
}