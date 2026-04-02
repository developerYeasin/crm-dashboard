from flask import Blueprint, request, jsonify
from models import db, KnowledgeBaseEntry
from auth import login_required, log_activity

kb_bp = Blueprint('kb', __name__)

@kb_bp.route('/kb', methods=['GET'])
@login_required
def get_kb_entries():
    """Get all knowledge base entries, optionally filtered by category."""
    category = request.args.get('category')
    query = KnowledgeBaseEntry.query

    if category:
        query = query.filter_by(category=category)

    entries = query.order_by(KnowledgeBaseEntry.category, KnowledgeBaseEntry.title).all()
    return jsonify([e.to_dict() for e in entries]), 200

@kb_bp.route('/kb/categories', methods=['GET'])
@login_required
def get_kb_categories():
    """Get all unique categories."""
    categories = db.session.query(KnowledgeBaseEntry.category).distinct().all()
    return jsonify([c[0] for c in categories]), 200

@kb_bp.route('/kb', methods=['POST'])
@login_required
def create_kb_entry():
    """Create a new knowledge base entry."""
    data = request.get_json()

    if not data or 'title' not in data or 'category' not in data:
        return jsonify({'error': 'Title and category are required'}), 400

    entry = KnowledgeBaseEntry(
        title=data['title'],
        content=data.get('content'),
        category=data['category']
    )

    db.session.add(entry)
    db.session.commit()

    log_activity('create_kb_entry', {'entry_id': entry.id, 'title': entry.title})

    return jsonify(entry.to_dict()), 201

@kb_bp.route('/kb/<int:entry_id>', methods=['GET'])
@login_required
def get_kb_entry(entry_id):
    """Get a single knowledge base entry."""
    entry = KnowledgeBaseEntry.query.get_or_404(entry_id)
    return jsonify(entry.to_dict()), 200

@kb_bp.route('/kb/<int:entry_id>', methods=['PUT'])
@login_required
def update_kb_entry(entry_id):
    """Update a knowledge base entry."""
    entry = KnowledgeBaseEntry.query.get_or_404(entry_id)
    data = request.get_json()

    if 'title' in data:
        entry.title = data['title']
    if 'content' in data:
        entry.content = data['content']
    if 'category' in data:
        entry.category = data['category']

    db.session.commit()
    log_activity('update_kb_entry', {'entry_id': entry.id, 'title': entry.title})

    return jsonify(entry.to_dict()), 200

@kb_bp.route('/kb/<int:entry_id>', methods=['DELETE'])
@login_required
def delete_kb_entry(entry_id):
    """Delete a knowledge base entry."""
    entry = KnowledgeBaseEntry.query.get_or_404(entry_id)
    entry_title = entry.title
    db.session.delete(entry)
    db.session.commit()

    log_activity('delete_kb_entry', {'entry_id': entry_id, 'title': entry_title})

    return jsonify({'message': 'Knowledge base entry deleted'}), 200

@kb_bp.route('/kb/search', methods=['GET'])
@login_required
def search_kb():
    """Search knowledge base entries by title and content."""
    query = request.args.get('q', '')
    if not query:
        return jsonify([]), 200

    search_term = f'%{query}%'
    entries = KnowledgeBaseEntry.query.filter(
        (KnowledgeBaseEntry.title.ilike(search_term)) |
        (KnowledgeBaseEntry.content.ilike(search_term))
    ).all()

    return jsonify([e.to_dict() for e in entries]), 200
