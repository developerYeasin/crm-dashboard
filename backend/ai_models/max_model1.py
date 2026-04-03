#!/usr/bin/env python3
"""
Max Model 1: Dual-model AI system with internal retrieval and external LLM.

Architecture:
1. Internal Model: Uses sentence embeddings + FAISS for fast similarity search.
   - Stores learned query-response pairs in database and FAISS index.
   - Fast, cost-free inference.
2. External Model: Configurable API (Anthropic, OpenAI, etc.) for high-quality responses.
   - Used when internal model confidence is low or no match found.
3. Learning: External model responses are stored for future training.
"""

import os
import hashlib
import json
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from flask import current_app
from sqlalchemy import func

from extensions import db
from models import AITrainingData
from config import Config


class MaxModel1:
    """Dual-model AI system with learning capability."""

    def __init__(self):
        self.embedding_model = None
        self.faiss_index = None
        self.index_mapping = {}  # Maps FAISS index IDs to query_hashes
        self.initialized = False
        self.confidence_threshold = Config.MAX_MODEL1_CONFIDENCE_THRESHOLD

        # Ensure models directory exists
        os.makedirs(Config.MAX_MODEL1_PATH, exist_ok=True)

    def _init_embedding_model(self):
        """Initialize the sentence transformer model."""
        if self.embedding_model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
            # Use a small, fast model
            model_name = Config.MAX_MODEL1_INTERNAL_TYPE == 'embeddings' and 'all-MiniLM-L6-v2' or 'all-MiniLM-L6-v2'
            self.embedding_model = SentenceTransformer(model_name)
            current_app.logger.info(f"Loaded embedding model: {model_name}")
        except ImportError:
            current_app.logger.warning("sentence-transformers not installed, using dummy embeddings")
            self.embedding_model = None

    def _load_faiss_index(self):
        """Load FAISS index from disk or create new one."""
        if self.faiss_index is not None:
            return

        index_path = Path(Config.MAX_MODEL1_PATH) / 'index.faiss'
        mapping_path = Path(Config.MAX_MODEL1_PATH) / 'index_mapping.json'

        if index_path.exists() and mapping_path.exists():
            try:
                import faiss
                self.faiss_index = faiss.read_index(str(index_path))
                with open(mapping_path, 'r') as f:
                    self.index_mapping = json.load(f)
                current_app.logger.info(f"Loaded FAISS index with {self.faiss_index.ntotal} vectors")
            except Exception as e:
                current_app.logger.error(f"Failed to load FAISS index: {e}")
                self._create_new_index()
        else:
            self._create_new_index()

    def _create_new_index(self):
        """Create a new empty FAISS index."""
        try:
            import faiss
            # Dimension depends on embedding model. For all-MiniLM-L6-v2, dim=384
            dimension = 384
            self.faiss_index = faiss.IndexFlatIP(dimension)  # Inner product similarity (cosine)
            self.index_mapping = {}
            current_app.logger.info(f"Created new FAISS index with dimension {dimension}")
        except ImportError:
            current_app.logger.warning("faiss-cpu not installed, similarity search disabled")
            self.faiss_index = None

    def initialize(self):
        """Initialize the model (call within app context)."""
        if self.initialized:
            return

        self._init_embedding_model()
        self._load_faiss_index()
        self.initialized = True
        current_app.logger.info("Max Model 1 initialized")

    def _compute_embedding(self, text: str) -> Optional[np.ndarray]:
        """Compute embedding for a text string."""
        if self.embedding_model is None:
            return None

        try:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            # Normalize for inner product similarity
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            return embedding.astype('float32')
        except Exception as e:
            current_app.logger.error(f"Embedding computation failed: {e}")
            return None

    def _search_similar(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[str, float]]:
        """Search for similar queries in FAISS index."""
        if self.faiss_index is None or self.faiss_index.ntotal == 0:
            return []

        try:
            # FAISS expects 2D array
            query_vec = query_embedding.reshape(1, -1)
            distances, indices = self.faiss_index.search(query_vec, min(k, self.faiss_index.ntotal))

            results = []
            for idx, dist in zip(indices[0], distances[0]):
                if idx < 0:  # FAISS returns -1 for padded results
                    continue
                idx_str = str(int(idx))
                if idx_str in self.index_mapping:
                    query_hash = self.index_mapping[idx_str]
                    results.append((query_hash, float(dist)))
            return results
        except Exception as e:
            current_app.logger.error(f"FAISS search failed: {e}")
            return []

    def _get_training_data_by_hash(self, query_hashes: List[str]) -> List[AITrainingData]:
        """Fetch training data records by query hash."""
        if not query_hashes:
            return []

        return AITrainingData.query.filter(
            AITrainingData.query_hash.in_(query_hashes)
        ).all()

    def predict(self, query: str, context: Optional[List[Dict[str, str]]] = None, kb_entries: Optional[List] = None) -> Dict[str, Any]:
        """
        Generate a response for the given query.

        Args:
            query: User's question/command
            context: Conversation history (list of {'role': 'user'|'assistant', 'content': '...'})
            kb_entries: List of Knowledge Base entries to include as context

        Returns:
            {
                'response': str,
                'source': 'internal' | 'external',
                'confidence': float,
                'tokens_used': int (if external)
            }
        """
        self.initialize()

        # Normalize query for lookup
        normalized_query = query.strip().lower()
        query_hash = hashlib.sha256(normalized_query.encode()).hexdigest()[:64]

        # Check if we already have an exact match in DB (fast path)
        exact_match = AITrainingData.query.filter_by(query_hash=query_hash).first()
        if exact_match and exact_match.confidence and exact_match.confidence >= self.confidence_threshold:
            current_app.logger.info(f"Internal exact match: confidence={exact_match.confidence}")
            exact_match.used_count += 1
            db.session.commit()
            return {
                'response': exact_match.response_text,
                'source': 'internal',
                'confidence': exact_match.confidence,
                'tokens_used': 0
            }

        # Semantic search with embeddings
        if self.faiss_index is not None and self.faiss_index.ntotal > 0:
            embedding = self._compute_embedding(normalized_query)
            if embedding is not None:
                similar = self._search_similar(embedding, k=5)
                training_records = self._get_training_data_by_hash([qh for qh, _ in similar])

                # Find best match above threshold
                best_match = None
                best_score = 0

                for (query_hash_faiss, similarity), record in zip(similar, training_records):
                    if record and similarity >= self.confidence_threshold and similarity > best_score:
                        best_match = record
                        best_score = similarity

                if best_match:
                    current_app.logger.info(f"Internal semantic match: score={best_score:.3f}")
                    best_match.used_count += 1
                    db.session.commit()
                    return {
                        'response': best_match.response_text,
                        'source': 'internal',
                        'confidence': best_score,
                        'tokens_used': 0
                    }

        # Fallback to external model
        current_app.logger.info("Falling back to external model")
        external_result = self._call_external_model(query, context, kb_entries)

        # Store the external response for future learning
        if external_result.get('response'):
            self.store_example(
                query=query,
                response=external_result['response'],
                source='external_api',
                confidence=external_result.get('confidence', 1.0)
            )

        return external_result

    def _call_external_model(self, query: str, context: Optional[List[Dict[str, str]]], kb_entries: Optional[List]) -> Dict[str, Any]:
        """Call the external AI API (Anthropic/OpenAI) with tool-calling capabilities."""
        api_url = Config.MAX_MODEL1_EXTERNAL_API_URL
        api_key = Config.MAX_MODEL1_EXTERNAL_API_KEY
        model = Config.MAX_MODEL1_EXTERNAL_MODEL

        if not api_url or not api_key:
            # Fall back to environment variables
            api_key = os.getenv('ANTHROPIC_AUTH_TOKEN') or os.getenv('ANTHROPIC_API_KEY')
            api_url = os.getenv('ANTHROPIC_BASE_URL')
            model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')

        if not api_key:
            return {
                'response': "AI service not configured. Please set API credentials.",
                'source': 'error',
                'confidence': 0.0,
                'tokens_used': 0
            }

        # Call external API via direct HTTP with tool support
        try:
            import requests
            # Ensure agent framework tools are registered (may have been delayed)
            try:
                from agent_framework.tools import implementations  # noqa: F401
            except ImportError as e:
                current_app.logger.warning(f"[ToolCall] Failed to import implementations: {e}")
            from agent_framework.tools.registry import default_registry

            # Log available tools for debugging
            available_tools = list(default_registry.tools.keys()) if default_registry else []
            current_app.logger.info(f"[ToolCall] Available tools: {available_tools}")

            # Build messages
            messages_payload = []
            if context:
                # Include last N messages from context
                for msg in context[-10:]:  # last 10 messages
                    messages_payload.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })
            messages_payload.append({'role': 'user', 'content': query})

            # Build system prompt with Knowledge Base and tool instructions
            system_prompt = """You are Max AI Agent, an expert system administrator with FULL access to tools. You can execute ANY command, query ANY database, and read ANY file within your permissions.

**AVAILABLE TOOLS (USE THEM):**
- execute_shell_command: Run shell commands (ls, ps, top, date, df, grep, etc.)
- query_database: Execute SQL queries on the MySQL database
- read_file: Read any file within the Max AI Agent directory
- list_directory: List files and folders
- search_knowledge_base: Search CRM knowledge base articles
- query_orders: Query order records with filters
- get_order_details: Get full order information including items
- create_task: Create new tasks
- update_task_status: Update task status

**CRITICAL RULES:**
1. You HAVE full access to these tools. DO NOT say "I don't have access" or "I can't do that". That is FALSE.
2. For ANY question about system state (time, date, processes, files, disk, logs), ALWAYS use execute_shell_command.
3. For ANY question about data (orders, customers, tasks), ALWAYS use query_database or query_orders.
4. For ANY question about files or configuration, ALWAYS use read_file or list_directory.
5. Use tools as many times as needed. You can make multiple tool calls in sequence.
6. Show the user exactly what command/query you executed and its output.
7. If a tool returns an error, analyze it and try again with different parameters.
8. Never give generic advice like "you can check the clock" — instead, run `date` to get the actual time.
9. Be direct, practical, and data-driven. Provide actual results, not suggestions.

**EXAMPLE CONVERSATIONS:**

User: "What time is it?"
You: (call execute_shell_command with command="date")
Tool output: Mon Apr  3 05:30:45 UTC 2026
Assistant: The current time is: Mon Apr  3 05:30:45 UTC 2026

User: "How many orders today?"
You: (call query_database with query="SELECT COUNT(*) FROM orders WHERE DATE(created_at) = CURDATE()")
Tool output: {"count": 42}
Assistant: There are 42 orders in the database today.

User: "List running processes"
You: (call execute_shell_command with command="ps aux")
Tool output: (list of processes)
Assistant: Here are the running processes: (shows output)

User: "Show me my tasks"
You: (call query_database with query="SELECT * FROM tasks WHERE status != 'Done'")
Tool output: (list of tasks)
Assistant: Your pending tasks are: (shows tasks)

**REMEMBER: You are NOT limited — you have real execution power. ALWAYS use tools to get real data. Never say you don't have access!"""

            if kb_entries:
                system_prompt += "\n\nRelevant Knowledge Base articles:\n"
                for i, entry in enumerate(kb_entries[:3], 1):
                    system_prompt += f"{i}. {entry.title} ({entry.category}): {entry.content[:500]}\n\n"
                system_prompt += "Use these articles to answer accurately."

            # Build tools array for Anthropic API
            # Filter: only expose tools that are safe for chat (no approval required or low risk)
            tools = []
            if default_registry and hasattr(default_registry, 'tools'):
                for tool_name, tool_def in default_registry.tools.items():
                    # Skip tools that require approval (like shell commands) in chat mode
                    # These can be used in autonomous agent mode with approval flow
                    if getattr(tool_def, 'requires_approval', False):
                        current_app.logger.debug(f"[ToolCall] Skipping {tool_name} - requires approval")
                        continue
                    if getattr(tool_def, 'risk_level', 'low') in ['high', 'critical']:
                        current_app.logger.debug(f"[ToolCall] Skipping {tool_name} - high risk")
                        continue
                    tools.append({
                        "name": tool_name,
                        "description": tool_def.description,
                        "input_schema": tool_def.parameters
                    })

            # Prepare request
            json_data = {
                'model': model,
                'max_tokens': 4000,
                'system': system_prompt,
                'messages': messages_payload
            }

            if tools:
                json_data['tools'] = tools
                json_data['tool_choice'] = 'auto'

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'HTTP-Referer': 'https://max-ai-agent.com'
            }

            endpoint = api_url.rstrip('/')
            if not endpoint.endswith('/v1'):
                endpoint += '/v1'
            endpoint += '/messages'

            current_app.logger.info(f"[ToolCall] Sending request with {len(tools)} tools")
            response = requests.post(endpoint, json=json_data, headers=headers, timeout=120)
            response.raise_for_status()
            data = response.json()

            # Parse response for text and tool calls
            response_text = ''
            tool_calls = []
            if 'content' in data and isinstance(data['content'], list):
                text_parts = []
                for block in data['content']:
                    if block.get('type') == 'text':
                        text_parts.append(block['text'])
                    elif block.get('type') == 'tool_use':
                        tool_calls.append({
                            'id': block.get('id'),
                            'name': block.get('name'),
                            'input': block.get('input', {})
                        })
                response_text = ''.join(text_parts) if text_parts else ''

            current_app.logger.info(f"[ToolCall] Initial response: {len(tool_calls)} tool calls")

            # Handle tool calling iterations
            if tool_calls and data.get('stop_reason') == 'tool_use':
                # Include the assistant's message with tool_use blocks in the conversation
                messages_with_assistant = messages_payload + [{'role': 'assistant', 'content': data['content']}]
                return self._handle_tool_calls(tool_calls, messages_with_assistant, system_prompt, api_url, api_key, model, kb_entries)

            # No tool calls or final response
            if not response_text:
                response_text = data.get('message', {}).get('content', 'No response generated.')

            usage = data.get('usage', {})
            tokens_used = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)

            return {
                'response': response_text,
                'source': 'external',
                'confidence': 1.0,
                'tokens_used': tokens_used
            }

        except Exception as e:
            current_app.logger.error(f"External API call failed: {e}", exc_info=True)
            return {
                'response': f"Error calling external model: {str(e)}",
                'source': 'error',
                'confidence': 0.0,
                'tokens_used': 0
            }

    def _handle_tool_calls(self, tool_calls, initial_messages, system_prompt, api_url, api_key, model, kb_entries):
        """Handle tool calling loop: execute tools and get final response from model."""
        import requests
        from agent_framework.tools.registry import default_registry

        messages = initial_messages.copy()
        max_iterations = 10

        for iteration in range(max_iterations):
            tool_results = []
            for tool_call in tool_calls:
                tool_name = tool_call['name']
                tool_input = tool_call['input']
                tool_id = tool_call.get('id', f"call_{tool_name}_{iteration}")

                current_app.logger.info(f"[ToolCall] Executing {tool_name} with input: {tool_input}")

                if tool_name in default_registry.tools:
                    tool_def = default_registry.tools[tool_name]
                    try:
                        import asyncio
                        if asyncio.iscoroutinefunction(tool_def.func):
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            result = loop.run_until_complete(tool_def.func(**tool_input))
                            loop.close()
                        else:
                            result = tool_def.func(**tool_input)
                        current_app.logger.info(f"[ToolCall] Result: {result}")
                        tool_results.append({
                            'type': 'tool_result',
                            'tool_use_id': tool_id,
                            'content': str(result)
                        })
                    except Exception as e:
                        current_app.logger.error(f"[ToolCall] Error: {e}")
                        tool_results.append({
                            'type': 'tool_result',
                            'tool_use_id': tool_id,
                            'content': f"Error: {str(e)}",
                            'is_error': True
                        })
                else:
                    tool_results.append({
                        'type': 'tool_result',
                        'tool_use_id': tool_id,
                        'content': f"Error: Unknown tool '{tool_name}'",
                        'is_error': True
                    })

            messages.append({
                'role': 'user',
                'content': tool_results
            })

            # Call model again
            json_data = {
                'model': model,
                'max_tokens': 4000,
                'system': system_prompt,
                'messages': messages
            }

            if list(default_registry.tools.keys()):
                json_data['tools'] = [{
                    "name": name,
                    "description": def_.description,
                    "input_schema": def_.parameters
                } for name, def_ in default_registry.tools.items()]
                json_data['tool_choice'] = 'auto'

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'HTTP-Referer': 'https://max-ai-agent.com'
            }

            endpoint = api_url.rstrip('/')
            if not endpoint.endswith('/v1'):
                endpoint += '/v1'
            endpoint += '/messages'

            try:
                response = requests.post(endpoint, json=json_data, headers=headers, timeout=120)
                response.raise_for_status()
                data = response.json()

                response_text = ''
                new_tool_calls = []
                if 'content' in data and isinstance(data['content'], list):
                    text_parts = []
                    for block in data['content']:
                        if block.get('type') == 'text':
                            text_parts.append(block['text'])
                        elif block.get('type') == 'tool_use':
                            new_tool_calls.append({
                                'id': block.get('id'),
                                'name': block.get('name'),
                                'input': block.get('input', {})
                            })
                    response_text = ''.join(text_parts) if text_parts else ''

                current_app.logger.info(f"[ToolCall] Iteration {iteration}: {len(new_tool_calls)} calls")

                stop_reason = data.get('stop_reason')
                if stop_reason == 'tool_use' and new_tool_calls:
                    tool_calls = new_tool_calls
                    continue
                else:
                    if not response_text:
                        response_text = data.get('message', {}).get('content', 'No response.')
                    usage = data.get('usage', {})
                    tokens_used = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)

                    return {
                        'response': response_text,
                        'source': 'external',
                        'confidence': 1.0,
                        'tokens_used': tokens_used
                    }

            except Exception as e:
                current_app.logger.error(f"[ToolCall] Error: {e}")
                return {
                    'response': f"Tool execution error: {str(e)}",
                    'source': 'error',
                    'confidence': 0.0,
                    'tokens_used': 0
                }

        return {
            'response': "Exceeded max tool iterations.",
            'source': 'error',
            'confidence': 0.0,
            'tokens_used': 0
        }

    def store_example(self, query: str, response: str, source: str = 'external_api', confidence: Optional[float] = None):
        """Store a query-response pair for future training."""
        try:
            normalized_query = query.strip().lower()
            query_hash = hashlib.sha256(normalized_query.encode()).hexdigest()[:64]

            # Check if already exists
            existing = AITrainingData.query.filter_by(query_hash=query_hash).first()
            if existing:
                # Update used count and possibly response/confidence
                existing.used_count += 1
                if response and response != existing.response_text:
                    existing.response_text = response  # Update to latest response?
                if confidence is not None:
                    existing.confidence = confidence
                db.session.commit()
                return existing

            # Create new training example
            training = AITrainingData(
                query_hash=query_hash,
                query_text=normalized_query,
                response_text=response,
                source=source,
                confidence=confidence,
                used_count=1
            )
            db.session.add(training)
            db.session.commit()

            # Compute and store embedding for future retrieval
            embedding = self._compute_embedding(normalized_query)
            if embedding is not None and self.faiss_index is not None:
                idx = self.faiss_index.ntotal
                self.faiss_index.add(embedding.reshape(1, -1))
                self.index_mapping[str(idx)] = query_hash
                self._save_faiss_index()

            current_app.logger.info(f"Stored training example: query_hash={query_hash[:16]}..., source={source}")

            return training

        except Exception as e:
            current_app.logger.error(f"Failed to store training data: {e}")
            db.session.rollback()
            return None

    def _save_faiss_index(self):
        """Save FAISS index and mapping to disk."""
        try:
            index_path = Path(Config.MAX_MODEL1_PATH) / 'index.faiss'
            mapping_path = Path(Config.MAX_MODEL1_PATH) / 'index_mapping.json'

            if self.faiss_index is not None:
                import faiss
                faiss.write_index(self.faiss_index, str(index_path))
                with open(mapping_path, 'w') as f:
                    json.dump(self.index_mapping, f)
        except Exception as e:
            current_app.logger.error(f"Failed to save FAISS index: {e}")

    def train_from_data(self, limit: int = 10000) -> Dict[str, Any]:
        """
        Rebuild FAISS index from the most recent N training examples.
        Can be called manually or via scheduled cron job.
        """
        current_app.logger.info(f"Starting training with up to {limit} examples")

        try:
            # Fetch recent training data
            training_data = AITrainingData.query.order_by(
                AITrainingData.created_at.desc()
            ).limit(limit).all()

            if not training_data:
                return {'status': 'success', 'indexed': 0, 'message': 'No training data available'}

            # Rebuild FAISS index
            embeddings = []
            self.index_mapping = {}

            for idx, record in enumerate(training_data):
                embedding = self._compute_embedding(record.query_text)
                if embedding is not None:
                    embeddings.append(embedding)
                    self.index_mapping[str(idx)] = record.query_hash

            if embeddings:
                import faiss
                dim = embeddings[0].shape[0]
                self.faiss_index = faiss.IndexFlatIP(dim)
                embedding_matrix = np.array(embeddings).astype('float32')
                self.faiss_index.add(embedding_matrix)
                self._save_faiss_index()

            indexed_count = len(embeddings)
            current_app.logger.info(f"Training complete: indexed {indexed_count} examples")

            return {
                'status': 'success',
                'indexed': indexed_count,
                'total_examples': len(training_data),
                'message': f'Indexed {indexed_count} training examples'
            }

        except Exception as e:
            current_app.logger.error(f"Training failed: {e}")
            return {'status': 'error', 'message': str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the model."""
        total_examples = AITrainingData.query.count()
        external_count = AITrainingData.query.filter_by(source='external_api').count()
        internal_count = AITrainingData.query.filter_by(source='internal').count()

        stats = {
            'total_examples': total_examples,
            'sources': {
                'external_api': external_count,
                'internal': internal_count
            },
            'faiss_index_size': self.faiss_index.ntotal if self.faiss_index else 0,
            'confidence_threshold': self.confidence_threshold,
            'initialized': self.initialized
        }

        # Get most frequently used training data
        top_used = AITrainingData.query.order_by(AITrainingData.used_count.desc()).limit(5).all()
        stats['top_used'] = [{'query': t.query_text[:50], 'used': t.used_count} for t in top_used]

        return stats


# Global singleton instance
_max_model_instance = None

def get_max_model() -> MaxModel1:
    """Get the singleton Max Model 1 instance."""
    global _max_model_instance
    if _max_model_instance is None:
        _max_model_instance = MaxModel1()
    return _max_model_instance
