import { useState } from 'react';
import { FiAlertTriangle, FiCheck, FiX, FiInfo } from 'react-icons/fi';

/**
 * ApprovalDialog - Modal for user to approve or deny agent actions.
 *
 * @param {Object} props
 * @param {Object} props.approval - Pending approval data
 * @param {Function} props.onApprove - Callback(comment) when approved
 * @param {Function} props.onDeny - Callback(comment) when denied
 */
export default function ApprovalDialog({ approval, onApprove, onDeny }) {
  const [comment, setComment] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  if (!approval) return null;

  const { tool_name, arguments: args, risk_level, message } = approval;

  const getRiskColor = (risk) => {
    switch (risk) {
      case 'high': return 'text-red-600 bg-red-100 border-red-300 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800';
      case 'medium': return 'text-yellow-600 bg-yellow-100 border-yellow-300 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800';
      case 'low': return 'text-green-600 bg-green-100 border-green-300 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800';
      default: return 'text-gray-600 bg-gray-100 border-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600';
    }
  };

  const handleApprove = async () => {
    setIsProcessing(true);
    try {
      await onApprove(comment);
      setComment('');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDeny = async () => {
    setIsProcessing(true);
    try {
      await onDeny(comment);
      setComment('');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-lg w-full border border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${getRiskColor(risk_level)}`}>
              <FiAlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Approval Required
              </h3>
              <span className={`inline-block mt-1 px-2 py-0.5 text-xs font-medium rounded-full border ${getRiskColor(risk_level)}`}>
                {risk_level.toUpperCase()} RISK
              </span>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-4">
          <p className="text-gray-700 dark:text-gray-300">
            {message || `The agent wants to use the tool: ${tool_name}`}
          </p>

          {/* Tool info */}
          <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="text-sm font-medium text-gray-900 dark:text-white mb-2">
              Tool: <span className="font-monial bg-gray-200 dark:bg-gray-700 px-2 py-0.5 rounded">{tool_name}</span>
            </div>
            {Object.keys(args).length > 0 && (
              <div>
                <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Arguments:</div>
                <pre className="text-xs bg-gray-900 dark:bg-gray-950 text-gray-100 p-3 rounded-lg overflow-x-auto">
                  {JSON.stringify(args, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {/* Optional comment */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Add a comment (optional)
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Why are you approving or denying this action?"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              rows={2}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
          <button
            onClick={handleDeny}
            disabled={isProcessing}
            className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-red-300 dark:border-red-700 text-red-700 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <FiX className="w-4 h-4" />
            Deny
          </button>
          <button
            onClick={handleApprove}
            disabled={isProcessing}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <FiCheck className="w-4 h-4" />
            {isProcessing ? 'Processing...' : 'Approve'}
          </button>
        </div>
      </div>
    </div>
  );
}
