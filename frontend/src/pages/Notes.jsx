import { useState, useEffect } from 'react';
import { FiPlus, FiEdit2, FiTrash2, FiFileText, FiChevronRight } from 'react-icons/fi';
import ReactMarkdown from 'react-markdown';
import { notesApi } from '../services/api';

export default function Notes() {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedNote, setSelectedNote] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingNote, setEditingNote] = useState(null);
  const [formData, setFormData] = useState({ title: '', content: '' });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchNotes();
  }, []);

  const fetchNotes = async () => {
    setLoading(true);
    try {
      const res = await notesApi.getAll();
      setNotes(Array.isArray(res.data) ? res.data : []);
    } catch (error) {
      console.error('Failed to fetch notes:', error);
      setNotes([]);
    } finally {
      setLoading(false);
    }
  };

  const selectNote = (note) => {
    setSelectedNote(note);
    setEditingNote(null);
    setFormData({ title: '', content: '' });
  };

  const openCreateModal = () => {
    setSelectedNote(null);
    setEditingNote(null);
    setFormData({ title: '', content: '' });
    setError('');
    setModalOpen(true);
  };

  const openEditModal = (note) => {
    setSelectedNote(null);
    setEditingNote(note);
    setFormData({ title: note.title, content: note.content || '' });
    setError('');
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');

    try {
      if (editingNote) {
        await notesApi.update(editingNote.id, formData);
      } else {
        await notesApi.create(formData);
      }
      setModalOpen(false);
      fetchNotes();
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to save note');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (noteId) => {
    if (!window.confirm('Delete this note?')) return;

    try {
      await notesApi.delete(noteId);
      if (selectedNote?.id === noteId) setSelectedNote(null);
      fetchNotes();
    } catch (error) {
      
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Notes</h1>
        <button onClick={openCreateModal} className="btn-primary flex items-center">
          <FiPlus className="mr-2" /> New Note
        </button>
      </div>

      <div className="flex gap-6" style={{ height: 'calc(100vh - 200px)' }}>
        {/* Notes list */}
        <div className="w-1/3 card overflow-y-auto">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-4">All Notes</h2>
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
            </div>
          ) : notes.length === 0 ? (
            <div className="text-center py-8 text-gray-600 dark:text-gray-400">
              <FiFileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No notes yet</p>
              <button onClick={openCreateModal} className="mt-3 btn-primary text-sm">
                Create your first note
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {notes.map(note => (
                <div
                  key={note.id}
                  onClick={() => selectNote(note)}
                  className={`p-3 rounded-lg cursor-pointer transition-colors ${
                    selectedNote?.id === note.id
                      ? 'bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800'
                      : 'hover:bg-gray-50 dark:hover:bg-dark-800 border border-transparent'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-gray-900 dark:text-white truncate">{note.title}</h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Updated: {new Date(note.updated_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => { e.stopPropagation(); openEditModal(note); }}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-dark-700 rounded"
                      >
                        <FiEdit2 className="w-3 h-3" />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(note.id); }}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-dark-700 rounded text-red-500"
                      >
                        <FiTrash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Note content */}
        <div className="flex-1 card overflow-y-auto">
          {selectedNote ? (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">{selectedNote.title}</h2>
                <div className="flex gap-2">
                  <button
                    onClick={() => openEditModal(selectedNote)}
                    className="btn-secondary text-sm py-1.5 px-3"
                  >
                    <FiEdit2 className="inline mr-1" /> Edit
                  </button>
                  <button
                    onClick={() => handleDelete(selectedNote.id)}
                    className="btn-danger text-sm py-1.5 px-3"
                  >
                    <FiTrash2 className="inline mr-1" /> Delete
                  </button>
                </div>
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                Last updated: {new Date(selectedNote.updated_at).toLocaleString()}
              </div>
              <div className="markdown-content">
                <ReactMarkdown>{selectedNote.content || '*No content*'}</ReactMarkdown>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
              <FiFileText className="w-16 h-16 mb-4 opacity-50" />
              <p className="text-lg">Select a note to view</p>
              <p className="text-sm mt-2">Or create a new one</p>
            </div>
          )}
        </div>
      </div>

      {/* Create/Edit Modal */}
      {modalOpen && (
        <div className="modal-backdrop" onClick={() => setModalOpen(false)}>
          <div className="modal-content max-w-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700 flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                {editingNote ? 'Edit Note' : 'New Note'}
              </h2>
              <button onClick={() => setModalOpen(false)} className="p-2 hover:bg-gray-100 dark:hover:bg-dark-800 rounded-lg">
                ×
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {error && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                  {error}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Title</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="input"
                  placeholder="Note title"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Content (Markdown supported)
                </label>
                <textarea
                  value={formData.content}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  className="textarea"
                  rows={15}
                  placeholder="Write your note in markdown..."
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-dark-700">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" disabled={submitting || !formData.title.trim()} className="btn-primary">
                  {submitting ? 'Saving...' : editingNote ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
