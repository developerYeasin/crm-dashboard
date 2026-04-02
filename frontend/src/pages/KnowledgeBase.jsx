import { useState, useEffect } from 'react';
import { FiPlus, FiEdit2, FiTrash2, FiChevronDown, FiChevronRight, FiSearch, FiBook, FiFolder } from 'react-icons/fi';
import { kbApi } from '../services/api';
import ReactMarkdown from 'react-markdown';

export default function KnowledgeBase() {
  const [entries, setEntries] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [expandedCategories, setExpandedCategories] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredEntries, setFilteredEntries] = useState([]);

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState(null);
  const [formData, setFormData] = useState({ title: '', content: '', category: '' });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [newCategory, setNewCategory] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [entriesRes, categoriesRes] = await Promise.all([
        kbApi.getAll(),
        kbApi.getCategories(),
      ]);
      setEntries(entriesRes.data);
      setCategories(categoriesRes.data);

      // Auto-expand all categories initially
      const expanded = {};
      categoriesRes.data.forEach(cat => expanded[cat] = true);
      setExpandedCategories(expanded);
    } catch (error) {
      console.error('Failed to fetch knowledge base:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let filtered = entries;

    if (selectedCategory !== 'All') {
      filtered = filtered.filter(e => e.category === selectedCategory);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(e =>
        e.title.toLowerCase().includes(q) ||
        e.content.toLowerCase().includes(q)
      );
    }

    setFilteredEntries(filtered);
  }, [entries, selectedCategory, searchQuery]);

  const toggleCategory = (category) => {
    setExpandedCategories(prev => ({
      ...prev,
      [category]: !prev[category],
    }));
  };

  const groupedEntries = filteredEntries.reduce((acc, entry) => {
    if (!acc[entry.category]) acc[entry.category] = [];
    acc[entry.category].push(entry);
    return acc;
  }, {});

  const openCreateModal = () => {
    setEditingEntry(null);
    setFormData({ title: '', content: '', category: categories[0] || '' });
    setNewCategory('');
    setError('');
    setModalOpen(true);
  };

  const openEditModal = (entry) => {
    setEditingEntry(entry);
    setFormData({ title: entry.title, content: entry.content || '', category: entry.category });
    setNewCategory('');
    setError('');
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');

    const data = {
      ...formData,
      category: newCategory || formData.category,
    };

    try {
      if (editingEntry) {
        await kbApi.update(editingEntry.id, data);
      } else {
        await kbApi.create(data);
      }
      setModalOpen(false);
      fetchData();
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to save entry');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (entryId) => {
    if (!window.confirm('Delete this knowledge base entry?')) return;

    try {
      await kbApi.delete(entryId);
      if (selectedEntry?.id === entryId) setSelectedEntry(null);
      fetchData();
    } catch (error) {
      alert('Failed to delete entry');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Knowledge Base</h1>
        <button onClick={openCreateModal} className="btn-primary flex items-center">
          <FiPlus className="mr-2" /> Add Entry
        </button>
      </div>

      <div className="flex gap-6" style={{ height: 'calc(100vh - 200px)' }}>
        {/* Sidebar */}
        <div className="w-80 card flex flex-col overflow-y-auto">
          {/* Search */}
          <div className="mb-4">
            <div className="relative">
              <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search knowledge base..."
                className="input pl-9"
              />
            </div>
          </div>

          {/* Category filter */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Filter by Category</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="select"
            >
              <option value="All">All Categories</option>
              {categories.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          {/* Entries grouped by category */}
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
            </div>
          ) : (
            <div className="flex-1 space-y-1">
              {Object.keys(groupedEntries).length === 0 ? (
                <div className="text-center py-8 text-gray-600 dark:text-gray-400">
                  <FiBook className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No entries found</p>
                </div>
              ) : (
                Object.entries(groupedEntries).map(([category, catEntries]) => (
                  <div key={category}>
                    <button
                      onClick={() => toggleCategory(category)}
                      className="w-full flex items-center justify-between p-2 hover:bg-gray-50 dark:hover:bg-dark-800 rounded-lg"
                    >
                      <div className="flex items-center">
                        <FiFolder className="mr-2 text-yellow-500" />
                        <span className="font-medium text-gray-900 dark:text-white">{category}</span>
                        <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                          ({catEntries.length})
                        </span>
                      </div>
                      {expandedCategories[category] ? <FiChevronDown className="w-4 h-4" /> : <FiChevronRight className="w-4 h-4" />}
                    </button>

                    {expandedCategories[category] && (
                      <div className="ml-6 mt-1 space-y-1">
                        {catEntries.map(entry => (
                          <div
                            key={entry.id}
                            onClick={() => setSelectedEntry(entry)}
                            className={`p-2 rounded-lg cursor-pointer text-left flex items-center justify-between group ${
                              selectedEntry?.id === entry.id
                                ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                                : 'hover:bg-gray-50 dark:hover:bg-dark-800 text-gray-700 dark:text-gray-300'
                            }`}
                          >
                            <div className="flex-1 min-w-0">
                              <h4 className="font-medium truncate">{entry.title}</h4>
                              <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                {new Date(entry.created_at).toLocaleDateString()}
                              </p>
                            </div>
                            <div className="flex opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                onClick={(e) => { e.stopPropagation(); openEditModal(entry); }}
                                className="p-1 hover:bg-gray-200 dark:hover:bg-dark-700 rounded"
                              >
                                <FiEdit2 className="w-3 h-3" />
                              </button>
                              <button
                                onClick={(e) => { e.stopPropagation(); handleDelete(entry.id); }}
                                className="p-1 hover:bg-gray-200 dark:hover:bg-dark-700 rounded text-red-500"
                              >
                                <FiTrash2 className="w-3 h-3" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Entry content */}
        <div className="flex-1 card overflow-y-auto">
          {selectedEntry ? (
            <div>
              <div className="flex items-start justify-between mb-4">
                <div>
                  <span className="text-sm text-primary-600 dark:text-primary-400 font-medium">
                    {selectedEntry.category}
                  </span>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{selectedEntry.title}</h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    Created: {new Date(selectedEntry.created_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => openEditModal(selectedEntry)}
                    className="btn-secondary text-sm py-1.5 px-3"
                  >
                    <FiEdit2 className="inline mr-1" /> Edit
                  </button>
                  <button
                    onClick={() => handleDelete(selectedEntry.id)}
                    className="btn-danger text-sm py-1.5 px-3"
                  >
                    <FiTrash2 className="inline mr-1" /> Delete
                  </button>
                </div>
              </div>
              <div className="markdown-content">
                <ReactMarkdown>{selectedEntry.content || '*No content*'}</ReactMarkdown>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
              <FiBook className="w-16 h-16 mb-4 opacity-50" />
              <p className="text-lg">Select an entry to view</p>
              <p className="text-sm mt-2">Or create a new one</p>
            </div>
          )}
        </div>
      </div>

      {/* Create/Edit Modal */}
      {modalOpen && (
        <div className="modal-backdrop" onClick={() => setModalOpen(false)}>
          <div className="modal-content max-w-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                {editingEntry ? 'Edit Entry' : 'Add Knowledge Base Entry'}
              </h2>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {error && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                  {error}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Title *</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="input"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Category</label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="select mb-2"
                >
                  {categories.map(cat => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
                <input
                  type="text"
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  className="input"
                  placeholder="Or type a new category..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Content (Markdown)
                </label>
                <textarea
                  value={formData.content}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  className="textarea"
                  rows={12}
                  placeholder="Write your knowledge base entry in markdown..."
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
                  {submitting ? 'Saving...' : editingEntry ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
