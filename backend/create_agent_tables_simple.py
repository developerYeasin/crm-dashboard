#!/usr/bin/env python3
"""Simple script to create agent framework tables directly"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config import Config
from sqlalchemy import create_engine, text

# Use the same database from config
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

# Define the CREATE TABLE statements (MySQL compatible)
tables = [
    """
    CREATE TABLE IF NOT EXISTS agent_sessions (
        id INT PRIMARY KEY AUTO_INCREMENT,
        user_id INT NOT NULL,
        conversation_id INT,
        title VARCHAR(255) NOT NULL,
        status ENUM('running', 'completed', 'failed', 'awaiting_approval') DEFAULT 'running',
        final_result TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP NULL,
        INDEX idx_user_status (user_id, status),
        INDEX idx_created (created_at),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (conversation_id) REFERENCES ai_conversations(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_steps (
        id INT PRIMARY KEY AUTO_INCREMENT,
        session_id INT NOT NULL,
        step_number INT NOT NULL,
        thought TEXT,
        action_name VARCHAR(100),
        action_args JSON,
        observation TEXT,
        observation_error TEXT,
        execution_time_ms INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES agent_sessions(id) ON DELETE CASCADE,
        UNIQUE KEY uniq_session_step (session_id, step_number),
        INDEX idx_session_order (session_id, step_number)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_calls (
        id INT PRIMARY KEY AUTO_INCREMENT,
        session_id INT NOT NULL,
        step_id INT,
        tool_name VARCHAR(100) NOT NULL,
        arguments JSON NOT NULL,
        result JSON,
        result_text TEXT,
        error TEXT,
        requires_approval BOOLEAN DEFAULT FALSE,
        approval_status ENUM('pending', 'approved', 'denied', 'skipped') DEFAULT 'pending',
        approved_by INT,
        approved_at TIMESTAMP NULL,
        executed_at TIMESTAMP NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES agent_sessions(id) ON DELETE CASCADE,
        FOREIGN KEY (step_id) REFERENCES agent_steps(id) ON DELETE SET NULL,
        FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
        INDEX idx_session_tool (session_id, tool_name),
        INDEX idx_approval (approval_status, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS approval_queue (
        id INT PRIMARY KEY AUTO_INCREMENT,
        session_id INT NOT NULL,
        step_id INT NOT NULL,
        tool_name VARCHAR(100) NOT NULL,
        arguments JSON NOT NULL,
        risk_level ENUM('low', 'medium', 'high') DEFAULT 'medium',
        message TEXT,
        status ENUM('pending', 'approved', 'denied', 'timeout') DEFAULT 'pending',
        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NULL,
        responded_at TIMESTAMP NULL,
        responded_by INT,
        FOREIGN KEY (session_id) REFERENCES agent_sessions(id) ON DELETE CASCADE,
        FOREIGN KEY (step_id) REFERENCES agent_steps(id) ON DELETE CASCADE,
        FOREIGN KEY (responded_by) REFERENCES users(id) ON DELETE SET NULL,
        INDEX idx_pending (status, requested_at),
        INDEX idx_session (session_id, status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_long_term_memory (
        id INT PRIMARY KEY AUTO_INCREMENT,
        user_id INT NOT NULL,
        session_id INT,
        memory_type ENUM('fact', 'preference', 'skill', 'error', 'success') DEFAULT 'fact',
        content TEXT NOT NULL,
        embedding LONGBLOB,
        importance FLOAT DEFAULT 1.0,
        access_count INT DEFAULT 0,
        last_accessed TIMESTAMP NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (session_id) REFERENCES agent_sessions(id) ON DELETE SET NULL,
        INDEX idx_user_type (user_id, memory_type),
        INDEX idx_importance (importance DESC),
        FULLTEXT INDEX idx_content (content)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_templates (
        id INT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(100) UNIQUE NOT NULL,
        description TEXT,
        system_prompt TEXT NOT NULL,
        allowed_tools JSON,
        config JSON,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
]

print(f"Connecting to database: {Config.SQLALCHEMY_DATABASE_URI}")

with engine.connect() as conn:
    for i, stmt in enumerate(tables, 1):
        try:
            conn.execute(text(stmt))
            conn.commit()
            print(f"✓ Created table {i}/6")
        except Exception as e:
            print(f"✗ Table {i} error: {e}")

    # Insert default templates
    from agent_framework.database.models import AgentTemplate
    # Check if templates exist
    result = conn.execute(text("SELECT COUNT(*) FROM agent_templates"))
    count = result.scalar()
    if count == 0:
        templates = [
            ('system_admin', 'General system administration assistant',
             'You are a system administrator assistant...'),
            ('coder', 'Software development helper',
             'You are a software development assistant...'),
            ('analyst', 'Data analyst for system queries',
             'You are a data analyst focused on system insights...')
        ]
        for name, desc, prompt in templates:
            conn.execute(
                text("INSERT INTO agent_templates (name, description, system_prompt, allowed_tools, config, is_active) VALUES (:name, :desc, :prompt, :tools, :config, 1)"),
                {
                    'name': name,
                    'desc': desc,
                    'prompt': prompt,
                    'tools': '[]',
                    'config': '{}'
                }
            )
        conn.commit()
        print("✓ Seeded agent templates")
    else:
        print(f"ℹ {count} templates already exist")

print("\n✓ Agent framework database setup complete!")
