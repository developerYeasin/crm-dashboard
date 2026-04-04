-- ============================================
-- Autonomous Agent Framework Database Schema
-- MySQL compatible
-- ============================================

-- Table: agent_sessions
-- Tracks multi-step agent execution sessions
CREATE TABLE IF NOT EXISTS agent_sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    conversation_id INT NULL,
    title VARCHAR(255) NOT NULL,
    status ENUM('running', 'completed', 'failed', 'awaiting_approval') DEFAULT 'running',
    final_result TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    INDEX idx_user_status (user_id, status),
    INDEX idx_created (created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (conversation_id) REFERENCES ai_conversations(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table: agent_steps
-- Each thought → action → observation cycle
CREATE TABLE IF NOT EXISTS agent_steps (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT NOT NULL,
    step_number INT NOT NULL,
    thought TEXT NULL,
    action_name VARCHAR(100) NULL,
    action_args JSON NULL,
    observation TEXT NULL,
    observation_error TEXT NULL,
    execution_time_ms INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES agent_sessions(id) ON DELETE CASCADE,
    UNIQUE KEY uniq_session_step (session_id, step_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table: tool_calls
-- Audit log of every tool invocation
CREATE TABLE IF NOT EXISTS tool_calls (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT NOT NULL,
    step_id INT NULL,
    tool_name VARCHAR(100) NOT NULL,
    arguments JSON NOT NULL,
    result JSON NULL,
    result_text TEXT NULL,
    error TEXT NULL,
    requires_approval BOOLEAN DEFAULT FALSE,
    approval_status ENUM('pending', 'approved', 'denied', 'timeout', 'skipped') DEFAULT 'pending',
    approved_by INT NULL,
    approved_at TIMESTAMP NULL,
    executed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES agent_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (step_id) REFERENCES agent_steps(id) ON DELETE SET NULL,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_session_tool (session_id, tool_name),
    INDEX idx_approval (approval_status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table: approval_queue
-- Queue of actions awaiting human approval
CREATE TABLE IF NOT EXISTS approval_queue (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT NOT NULL,
    step_id INT NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    arguments JSON NOT NULL,
    risk_level ENUM('low', 'medium', 'high') DEFAULT 'medium',
    message TEXT NULL,
    status ENUM('pending', 'approved', 'denied', 'timeout') DEFAULT 'pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    responded_at TIMESTAMP NULL,
    responded_by INT NULL,
    FOREIGN KEY (session_id) REFERENCES agent_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (step_id) REFERENCES agent_steps(id) ON DELETE CASCADE,
    FOREIGN KEY (responded_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_pending (status, requested_at),
    INDEX idx_session (session_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table: agent_long_term_memory
-- Long-term memories with embeddings for semantic search
CREATE TABLE IF NOT EXISTS agent_long_term_memory (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    session_id INT NULL,
    memory_type ENUM('fact', 'preference', 'skill', 'error', 'success') DEFAULT 'fact',
    content TEXT NOT NULL,
    embedding LONGBLOB NULL,
    importance FLOAT DEFAULT 1.0,
    access_count INT DEFAULT 0,
    last_accessed TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES agent_sessions(id) ON DELETE SET NULL,
    INDEX idx_user_type (user_id, memory_type),
    INDEX idx_importance (importance DESC),
    INDEX idx_last_accessed (last_accessed),
    FULLTEXT INDEX idx_content (content)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table: agent_templates
-- Pre-defined agent personalities/skills
CREATE TABLE IF NOT EXISTS agent_templates (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NULL,
    system_prompt TEXT NOT NULL,
    allowed_tools JSON NOT NULL,
    config JSON NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert default templates
INSERT IGNORE INTO agent_templates (name, description, system_prompt, allowed_tools, config, is_active) VALUES
('system_admin', 'General system administration assistant',
 'You are a system administrator assistant. You can execute shell commands, query databases, read files, and check system metrics. Always be cautious and explain what you are doing before you do it. For read-only operations, proceed without approval. For writes or system changes, users will need to approve.',
 '["get_system_metrics", "list_directory", "read_file", "execute_shell_command", "query_database"]',
 '{"max_steps": 20, "temperature": 0.7}',
 TRUE),

('coder', 'Software development helper',
 'You are a software development assistant. You can read and write code files, search the codebase, and run tests. Always make backups before modifying files and explain your changes clearly.',
 '["list_directory", "read_file", "write_file", "execute_shell_command", "search_knowledge_base"]',
 '{"max_steps": 30, "temperature": 0.8}',
 TRUE),

('analyst', 'Data analyst for system queries',
 'You are a data analyst focused on system insights. You can query the database to generate reports, analyze trends, and answer questions. Read-only access only - no data modifications.',
 '["query_database", "get_system_metrics", "search_knowledge_base"]',
 '{"max_steps": 15, "temperature": 0.5}',
 TRUE);
