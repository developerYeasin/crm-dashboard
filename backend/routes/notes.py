from flask import Blueprint, request, jsonify
from models import db, Note
from auth import login_required, log_activity

notes_bp = Blueprint('notes', __name__)

@notes_bp.route('/notes', methods=['GET'])
@login_required
def get_notes():
    """Get all notes."""
    notes = Note.query.order_by(Note.updated_at.desc()).all()
    return jsonify([n.to_dict() for n in notes]), 200

@notes_bp.route('/notes', methods=['POST'])
@login_required
def create_note():
    """Create a new note."""
    data = request.get_json()

    if not data or 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400

    note = Note(
        title=data['title'],
        content=data.get('content')
    )

    db.session.add(note)
    db.session.commit()

    log_activity('create_note', {'note_id': note.id, 'title': note.title})

    return jsonify(note.to_dict()), 201

@notes_bp.route('/notes/<int:note_id>', methods=['GET'])
@login_required
def get_note(note_id):
    """Get a single note."""
    note = Note.query.get_or_404(note_id)
    return jsonify(note.to_dict()), 200

@notes_bp.route('/notes/<int:note_id>', methods=['PUT'])
@login_required
def update_note(note_id):
    """Update a note."""
    note = Note.query.get_or_404(note_id)
    data = request.get_json()

    if 'title' in data:
        note.title = data['title']
    if 'content' in data:
        note.content = data['content']

    note.updated_at = datetime.utcnow()
    db.session.commit()

    log_activity('update_note', {'note_id': note.id, 'title': note.title})

    return jsonify(note.to_dict()), 200

@notes_bp.route('/notes/<int:note_id>', methods=['DELETE'])
@login_required
def delete_note(note_id):
    """Delete a note."""
    note = Note.query.get_or_404(note_id)
    note_title = note.title
    db.session.delete(note)
    db.session.commit()

    log_activity('delete_note', {'note_id': note_id, 'title': note_title})

    return jsonify({'message': 'Note deleted'}), 200
