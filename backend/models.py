from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from extensions import db


# ========== ORIGINAL MODELS ==========

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    role = db.Column(db.String(50), default='Member', nullable=False)
    avatar_url = db.Column(db.String(500), nullable=True)
    current_token = db.Column(db.String(64), nullable=True, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def check_password(self, password):
        from bcrypt import checkpw
        return checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'is_admin': self.is_admin,
            'role': self.role,
            'avatar_url': self.avatar_url,
            'current_token': self.current_token,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    division = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(100), nullable=False)
    upazila_zone = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text, nullable=True)  # Full address
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=True)  # Price for COD/Prepaid
    payment_type = db.Column(db.Enum('COD', 'Prepaid', name='payment_type_enum'), nullable=False, default='COD')
    courier_parcel_id = db.Column(db.String(100), nullable=True)
    position = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    status = db.relationship('OrderStatus', backref='order', lazy=True, uselist=False, cascade='all, delete-orphan')
    media = db.relationship('Media', backref='order', lazy=True, cascade='all, delete-orphan')
    activity_logs = db.relationship('ActivityLog', backref='order', lazy=True, cascade='all, delete-orphan')


class OrderStatus(db.Model):
    __tablename__ = 'order_status'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, unique=True)

    # Design & Production
    design_ready = db.Column(db.Boolean, default=False, nullable=False)
    is_printed = db.Column(db.Boolean, default=False, nullable=False)
    picking_done = db.Column(db.Boolean, default=False, nullable=False)

    # Delivery
    delivery_status = db.Column(db.Enum('Submitted', 'Delivered', 'Returned', name='delivery_status_enum'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Media(db.Model):
    __tablename__ = 'media'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('order_items.id'), nullable=True)  # Nullable: media can belong to order or item
    side = db.Column(db.String(20), nullable=True)  # 'front', 'back', or NULL for order-level or non-apparel
    file_path = db.Column(db.String(500), nullable=False)  # For local path or Cloudinary public_id
    file_url = db.Column(db.String(500), nullable=True)  # For Cloudinary URL (or populated on demand)
    file_type = db.Column(db.Enum('Image', 'Video', 'File', name='file_type_enum'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to OrderItem (optional)
    item = db.relationship('OrderItem', backref=db.backref('media', cascade='all, delete-orphan'), lazy=True)


class ActivityLog(db.Model):
    __tablename__ = 'activity_log'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Serialize log entry to dictionary"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'action': self.action,
            'details': self.details,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class OrderItem(db.Model):
    """Items within an order (e.g., t-shirt designs)"""
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    size = db.Column(db.String(20), nullable=False)  # e.g., S, M, L, XL, XXL
    quantity = db.Column(db.Integer, nullable=False, default=1)
    position = db.Column(db.Integer, nullable=True)  # For ordering items within an order
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to order - cascade delete from order to items
    order = db.relationship('Order', backref=db.backref('items', cascade='all, delete-orphan'))

    # Media relationship - items can have multiple images (front/back/etc)
    # Media deletes will cascade from item via db.backref with cascade on Media.item relationship

    def to_dict(self, with_media=False):
        """Serialize item to dictionary"""
        data = {
            'id': self.id,
            'order_id': self.order_id,
            'size': self.size,
            'quantity': self.quantity,
            'position': self.position,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if with_media:
            # Separate front and back images
            front = []
            back = []
            other = []
            for m in self.media:
                media_dict = {
                    'id': m.id,
                    'file_path': m.file_path,
                    'file_url': m.file_url,
                    'file_type': m.file_type,
                    'side': m.side,
                    'uploaded_at': m.uploaded_at.isoformat() if m.uploaded_at else None
                }
                if m.side == 'front':
                    front.append(media_dict)
                elif m.side == 'back':
                    back.append(media_dict)
                else:
                    other.append(media_dict)
            data['front_images'] = front
            data['back_images'] = back
            data['other_images'] = other  # For any images without side specified
        return data


# ========== AI ASSISTANT MODELS ==========

class AIConversation(db.Model):
    """Tracks AI chat conversations"""
    __tablename__ = 'ai_conversations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Null for system-only
    title = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    messages = db.relationship('AIMessage', backref='conversation', lazy=True, cascade='all, delete-orphan')
    user = db.relationship('User', backref='ai_conversations')


class AIMessage(db.Model):
    """Stores individual chat messages"""
    __tablename__ = 'ai_messages'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('ai_conversations.id'), nullable=False)
    role = db.Column(db.Enum('user', 'assistant', 'system', name='ai_role_enum'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Optional context about what the AI was doing
    action_taken = db.Column(db.String(500), nullable=True)  # e.g., "Created cron job", "Executed command"
    command_executed = db.Column(db.Text, nullable=True)  # If a shell command was run
    command_output = db.Column(db.Text, nullable=True)  # Output from the command


class AIAction(db.Model):
    """Logs all AI-triggered actions for audit"""
    __tablename__ = 'ai_actions'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('ai_conversations.id'), nullable=True)
    action_type = db.Column(db.String(100), nullable=False)  # 'cron_create', 'shell_command', 'db_query', 'file_operation'
    description = db.Column(db.Text, nullable=False)
    command = db.Column(db.Text, nullable=True)  # The actual command/action performed
    result = db.Column(db.Text, nullable=True)  # Success/failure/output
    status = db.Column(db.Enum('pending', 'approved', 'rejected', 'completed', 'failed', name='action_status_enum'), default='pending')
    executed_by = db.Column(db.String(100), nullable=True)  # 'ai' or user email
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    executed_at = db.Column(db.DateTime, nullable=True)


class SystemCronJob(db.Model):
    """Cron jobs that can be created by AI or manually"""
    __tablename__ = 'system_cron_jobs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    command = db.Column(db.Text, nullable=False)  # Command to execute
    schedule = db.Column(db.String(100), nullable=False)  # Cron expression
    enabled = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.String(100), nullable=False)  # 'ai' or user email
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_run = db.Column(db.DateTime, nullable=True)
    last_output = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)


class SystemCommandLog(db.Model):
    """Logs all system commands executed (for audit)"""
    __tablename__ = 'system_command_logs'

    id = db.Column(db.Integer, primary_key=True)
    command = db.Column(db.Text, nullable=False)
    executed_by = db.Column(db.String(100), nullable=False)  # 'ai' or user email
    conversation_id = db.Column(db.Integer, db.ForeignKey('ai_conversations.id'), nullable=True)
    output = db.Column(db.Text, nullable=True)
    exit_code = db.Column(db.Integer, nullable=True)
    execution_time = db.Column(db.Float, nullable=True)  # Seconds
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum('success', 'failed', 'timeout', name='cmd_status_enum'), nullable=False)


class SystemMetric(db.Model):
    """Store system metrics that AI can query"""
    __tablename__ = 'system_metrics'

    id = db.Column(db.Integer, primary_key=True)
    metric_type = db.Column(db.String(50), nullable=False)  # 'disk', 'memory', 'cpu', 'network', 'process'
    metric_name = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=True)  # 'GB', '%', 'MB/s'
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    extra_data = db.Column(db.JSON, nullable=True)  # Additional context


class Setting(db.Model):
    """Application settings stored in database"""
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    settings_key = db.Column(db.String(100), unique=True, nullable=False)
    settings_value = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(50), nullable=False, default='string')  # string, integer, boolean, json, encrypted
    category = db.Column(db.String(50), nullable=False, default='general')
    description = db.Column(db.Text, nullable=True)
    is_encrypted = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get(cls, key, default=None):
        """Get setting value, decrypting if necessary"""
        setting = cls.query.filter_by(settings_key=key).first()
        if not setting:
            return default

        val = setting.settings_value
        if setting.is_encrypted and val:
            try:
                from cryptography.fernet import Fernet
                from base64 import b64encode
                import hashlib
                from flask import current_app
                secret = current_app.config.get('SECRET_KEY', 'order-tracker-secret-change-in-production')
                key_bytes = hashlib.sha256(secret.encode()).digest()
                fernet_key = b64encode(key_bytes)
                cipher = Fernet(fernet_key)
                decrypted = cipher.decrypt(val.encode()).decode()
                return decrypted
            except Exception:
                return val
        return val

    @classmethod
    def set(cls, key, value, type='string', category='general', description=None, is_encrypted=False):
        """Set setting value, encrypting if necessary"""
        setting = cls.query.filter_by(settings_key=key).first()
        if not setting:
            setting = cls(settings_key=key)

        stored_value = value
        if is_encrypted and value:
            try:
                from cryptography.fernet import Fernet
                from base64 import b64encode
                import hashlib
                from flask import current_app
                secret = current_app.config.get('SECRET_KEY', 'order-tracker-secret-change-in-production')
                key_bytes = hashlib.sha256(secret.encode()).digest()
                fernet_key = b64encode(key_bytes)
                cipher = Fernet(fernet_key)
                encrypted = cipher.encrypt(str(value).encode()).decode()
                stored_value = encrypted
            except Exception as e:
                current_app.logger.error(f'Encryption failed for setting {key}: {str(e)}')
                stored_value = value

        setting.settings_value = stored_value
        setting.type = type
        setting.category = category
        setting.description = description
        setting.is_encrypted = is_encrypted

        db.session.add(setting)
        db.session.commit()
        return setting

    @classmethod
    def delete(cls, key):
        """Delete a setting"""
        setting = cls.query.filter_by(settings_key=key).first()
        if setting:
            db.session.delete(setting)
            db.session.commit()
            return True
        return False

    @classmethod
    def get_all_by_category(cls, category):
        """Get all settings for a category"""
        settings = cls.query.filter_by(category=category).all()
        result = []
        for s in settings:
            result.append({
                'key': s.settings_key,
                'value': cls.get(s.settings_key),
                'type': s.type,
                'category': s.category,
                'description': s.description,
                'is_encrypted': s.is_encrypted
            })
        return result

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'key': self.settings_key,
            'value': Setting.get(self.settings_key) if self.is_encrypted else self.settings_value,
            'type': self.type,
            'category': self.category,
            'description': self.description,
            'is_encrypted': self.is_encrypted,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# ========== CRM TEAM MODELS ==========

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship('User', foreign_keys=[author_id], backref='user_comments')

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'author_id': self.author_id,
            'author_name': self.author.name if self.author else 'Unknown',
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='To Do')
    priority = db.Column(db.String(20), nullable=False, default='Medium')
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.Text, nullable=True)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    assignee = db.relationship('User', foreign_keys=[assigned_to], backref='tasks_assigned', lazy=True)
    assigner = db.relationship('User', foreign_keys=[assigned_by], backref='tasks_created', lazy=True)
    comments = db.relationship('Comment', backref='task', lazy=True, cascade='all, delete-orphan')
    __table_args__ = (
        db.Index('idx_task_status', 'status'),
        db.Index('idx_task_priority', 'priority'),
        db.Index('idx_task_assigned_to', 'assigned_to'),
        db.Index('idx_task_due_date', 'due_date'),
        db.Index('idx_task_created_at', 'created_at'),
    )

    def to_dict(self, include_details=False):
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'assigned_to': self.assigned_to,
            'assigned_by': self.assigned_by,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_details:
            data['assignee'] = self.assignee.to_dict() if self.assignee else None
            data['assigner'] = self.assigner.to_dict() if self.assigner else None
            data['comments'] = [c.to_dict() for c in self.comments]
        return data

class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (db.Index('idx_note_created_at', 'created_at'),)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class KnowledgeBaseEntry(db.Model):
    __tablename__ = 'kb_entries'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.Index('idx_kb_category', 'category'),)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'category': self.category,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ScheduledReminder(db.Model):
    __tablename__ = 'scheduled_reminders'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True)
    reminder_type = db.Column(db.String(50), nullable=False)
    scheduled_for = db.Column(db.DateTime, nullable=False)
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, nullable=True)
    __table_args__ = (
        db.Index('idx_reminder_scheduled_for', 'scheduled_for'),
        db.Index('idx_reminder_sent', 'sent'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'reminder_type': self.reminder_type,
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'message': self.message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'sent': self.sent,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None
        }
