"""
Chat file upload endpoints.
"""

import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from extensions import db
from models import ChatAttachment, AIMessage
from auth import login_required
from werkzeug.utils import secure_filename

chat_media_bp = Blueprint('chat_media', __name__)

UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
CHAT_UPLOAD_DIR = os.path.join(UPLOAD_FOLDER, 'chat')

# Ensure upload directory exists
os.makedirs(CHAT_UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {
    'image': {'png', 'jpg', 'jpeg', 'gif', 'webp'},
    'document': {'pdf', 'doc', 'docx', 'txt', 'md'},
    'video': {'mp4', 'mov', 'avi'},
}

def allowed_file(filename):
    """Check if file extension is allowed."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    for allowed_set in ALLOWED_EXTENSIONS.values():
        if ext in allowed_set:
            return True
    return False

def get_file_type(filename):
    """Determine file type based on extension."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown'
    for ftype, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return ftype
    return 'file'

@chat_media_bp.route('/api/chat/upload', methods=['POST'])
@login_required
def upload_chat_file():
    """Upload a file for chat attachment."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    try:
        # Generate unique filename
        original_name = secure_filename(file.filename)
        ext = original_name.rsplit('.', 1)[1].lower() if '.' in original_name else ''
        unique_filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
        rel_path = os.path.join('chat', unique_filename)
        abs_path = os.path.join(UPLOAD_FOLDER, rel_path)

        # Ensure directory exists
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        # Save file
        file.save(abs_path)

        # Determine file type
        file_type = get_file_type(original_name)

        # For images, we could generate a thumbnail here (optional)

        # Build response URL (relative to static uploads)
        file_url = f"/uploads/{rel_path.replace(os.sep, '/')}"

        return jsonify({
            'success': True,
            'file': {
                'original_name': original_name,
                'file_path': rel_path,
                'file_url': file_url,
                'file_type': file_type,
                'size': os.path.getsize(abs_path)
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Chat file upload failed: {e}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@chat_media_bp.route('/api/chat/attachment/<int:attachment_id>', methods=['DELETE'])
@login_required
def delete_chat_attachment(attachment_id):
    """Delete a chat attachment (if allowed)."""
    attachment = ChatAttachment.query.get_or_404(attachment_id)

    # Check permissions: user must own the message's conversation
    message = AIMessage.query.get(attachment.message_id)
    if not message:
        return jsonify({'error': 'Message not found'}), 404

    conversation = message.conversation
    from auth import get_current_user
    user = get_current_user()
    if conversation.user_id != user.id:
        return jsonify({'error': 'Not authorized'}), 403

    # Delete file from filesystem
    try:
        file_path = os.path.join(UPLOAD_FOLDER, attachment.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        current_app.logger.warning(f"Failed to delete file {attachment.file_path}: {e}")

    # Delete record
    db.session.delete(attachment)
    db.session.commit()

    return jsonify({'message': 'Attachment deleted'}), 200
