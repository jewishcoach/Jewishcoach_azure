import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, Plus, X, Edit2, Save, Trash2, Clock } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface Reminder {
  id: number;
  title: string;
  description: string | null;
  reminder_date: string;
  reminder_time: string | null;
  repeat_type: string;
  repeat_days: number[] | null;
  is_active: boolean;
  next_reminder_date: string | null;
}

export const RemindersManager = () => {
  const { getToken } = useAuth();
  const { t } = useTranslation();
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    reminder_date: '',
    reminder_time: '19:00',
    repeat_type: 'once',
    repeat_days: [] as number[],
  });

  useEffect(() => {
    loadReminders();
  }, []);

  const loadReminders = async () => {
    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/calendar/reminders`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setReminders(data);
    } catch (error) {
      console.error('Error loading reminders:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const token = await getToken();
      const url = editingId 
        ? `${API_URL}/calendar/reminders/${editingId}`
        : `${API_URL}/calendar/reminders`;
      
      const method = editingId ? 'PATCH' : 'POST';
      
      await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...formData,
          reminder_date: new Date(formData.reminder_date + 'T00:00:00').toISOString(),
        })
      });
      
      await loadReminders();
      resetForm();
    } catch (error) {
      console.error('Error saving reminder:', error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm(t('reminders.deleteConfirm'))) return;
    
    try {
      const token = await getToken();
      await fetch(`${API_URL}/calendar/reminders/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      await loadReminders();
    } catch (error) {
      console.error('Error deleting reminder:', error);
    }
  };

  const handleEdit = (reminder: Reminder) => {
    setEditingId(reminder.id);
    setFormData({
      title: reminder.title,
      description: reminder.description || '',
      reminder_date: reminder.reminder_date.split('T')[0],
      reminder_time: reminder.reminder_time || '19:00',
      repeat_type: reminder.repeat_type,
      repeat_days: reminder.repeat_days || [],
    });
    setShowAddForm(true);
  };

  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      reminder_date: '',
      reminder_time: '19:00',
      repeat_type: 'once',
      repeat_days: [],
    });
    setEditingId(null);
    setShowAddForm(false);
  };

  const toggleRepeatDay = (day: number) => {
    setFormData(prev => ({
      ...prev,
      repeat_days: prev.repeat_days.includes(day)
        ? prev.repeat_days.filter(d => d !== day)
        : [...prev.repeat_days, day]
    }));
  };

  const weekDays = ['א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ש'];

  if (loading) {
    return <div className="text-center py-8 text-[#F5F5F0]/70">{t('chat.loading')}</div>;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Bell className="w-5 h-5 text-[#FCF6BA]" />
          <h3 className="text-lg font-bold text-[#F5F5F0]">{t('reminders.title')}</h3>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors"
          style={{ background: 'linear-gradient(45deg, #BF953F, #FCF6BA)', color: '#020617' }}
        >
          {showAddForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
          {showAddForm ? t('reminders.cancel') : t('reminders.new')}
        </button>
      </div>

      {/* Add/Edit Form */}
      <AnimatePresence>
        {showAddForm && (
          <motion.form
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            onSubmit={handleSubmit}
            className="bg-white/[0.04] rounded-2xl p-6 border border-white/[0.08]"
          >
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-[#F5F5F0]">{t('reminders.title_input')}</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  placeholder={t('reminders.title_placeholder')}
                  required
                  className="w-full px-4 py-2 border border-white/10 rounded-lg bg-white/[0.04] text-[#F5F5F0] placeholder-[#F5F5F0]/40 focus:ring-2 focus:ring-[#FCF6BA]/30"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-[#F5F5F0]">{t('reminders.description')}</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  placeholder={t('reminders.description_placeholder')}
                  rows={2}
                  className="w-full px-4 py-2 border border-white/10 rounded-lg bg-white/[0.04] text-[#F5F5F0] placeholder-[#F5F5F0]/40 focus:ring-2 focus:ring-[#FCF6BA]/30"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2 text-[#F5F5F0]">{t('reminders.date')}</label>
                  <input
                    type="date"
                    value={formData.reminder_date}
                    onChange={(e) => setFormData({...formData, reminder_date: e.target.value})}
                    required
                    className="w-full px-4 py-2 border border-white/10 rounded-lg bg-white/[0.04] text-[#F5F5F0] focus:ring-2 focus:ring-[#FCF6BA]/30"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2 text-[#F5F5F0]">{t('reminders.time')}</label>
                  <input
                    type="time"
                    value={formData.reminder_time}
                    onChange={(e) => setFormData({...formData, reminder_time: e.target.value})}
                    className="w-full px-4 py-2 border border-white/10 rounded-lg bg-white/[0.04] text-[#F5F5F0] focus:ring-2 focus:ring-[#FCF6BA]/30"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-[#F5F5F0]">{t('reminders.repeat')}</label>
                <select
                  value={formData.repeat_type}
                  onChange={(e) => setFormData({...formData, repeat_type: e.target.value})}
                  className="w-full px-4 py-2 border border-white/10 rounded-lg bg-white/[0.04] text-[#F5F5F0] focus:ring-2 focus:ring-[#FCF6BA]/30"
                >
                  <option value="once">{t('reminders.once')}</option>
                  <option value="daily">{t('reminders.daily')}</option>
                  <option value="weekly">{t('reminders.weekly')}</option>
                  <option value="biweekly">{t('reminders.biweekly')}</option>
                  <option value="monthly">{t('reminders.monthly')}</option>
                </select>
              </div>

              {formData.repeat_type === 'weekly' && (
                <div>
                  <label className="block text-sm font-medium mb-2 text-[#F5F5F0]">{t('reminders.weekDays')}</label>
                  <div className="flex gap-2">
                    {weekDays.map((day, index) => (
                      <button
                        key={index}
                        type="button"
                        onClick={() => toggleRepeatDay(index)}
                        className={`w-10 h-10 rounded-full transition-colors ${
                          formData.repeat_days.includes(index)
                            ? 'bg-[#FCF6BA]/30 text-[#FCF6BA]'
                            : 'bg-white/10 text-[#F5F5F0] hover:bg-white/15'
                        }`}
                      >
                        {day}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-2">
                <button
                  type="submit"
                  className="flex items-center gap-2 px-6 py-2 rounded-lg transition-colors"
                  style={{ background: 'linear-gradient(45deg, #BF953F, #FCF6BA)', color: '#020617' }}
                >
                  <Save className="w-4 h-4" />
                  {editingId ? t('reminders.update') : t('reminders.save')}
                </button>
                <button
                  type="button"
                  onClick={resetForm}
                  className="px-6 py-2 bg-white/10 text-[#F5F5F0] rounded-lg hover:bg-white/15 transition-colors"
                >
                  {t('reminders.cancel')}
                </button>
              </div>
            </div>
          </motion.form>
        )}
      </AnimatePresence>

      {/* Reminders List */}
      <div className="space-y-3">
        {reminders.length === 0 ? (
          <div className="text-center py-8 text-[#F5F5F0]/50">
            {t('reminders.noReminders')}
          </div>
        ) : (
          reminders.map((reminder) => (
            <motion.div
              key={reminder.id}
              layout
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white/[0.06] rounded-xl p-4 border border-white/[0.1]"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Bell className="w-4 h-4 text-[#FCF6BA]" />
                    <h4 className="font-bold text-[#F5F5F0]">{reminder.title}</h4>
                  </div>
                  {reminder.description && (
                    <p className="text-sm text-[#F5F5F0]/70 mt-1">{reminder.description}</p>
                  )}
                  <div className="flex items-center gap-4 mt-2 text-sm text-[#F5F5F0]/60">
                    <div className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      {new Date(reminder.reminder_date).toLocaleDateString('he-IL')}
                      {reminder.reminder_time && ` • ${reminder.reminder_time}`}
                    </div>
                    <span className="px-2 py-1 bg-[#FCF6BA]/15 text-[#FCF6BA] rounded text-xs">
                      {getRepeatLabel(reminder.repeat_type, t)}
                    </span>
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => handleEdit(reminder)}
                    className="p-2 text-[#F5F5F0]/60 hover:text-[#FCF6BA] transition-colors"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(reminder.id)}
                    className="p-2 text-[#F5F5F0]/60 hover:text-red-400 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </motion.div>
          ))
        )}
      </div>
    </div>
  );
};

function getRepeatLabel(repeatType: string, t: any): string {
  const labels: Record<string, string> = {
    'once': t('reminders.once'),
    'daily': t('reminders.daily'),
    'weekly': t('reminders.weekly'),
    'biweekly': t('reminders.biweekly'),
    'monthly': t('reminders.monthly'),
  };
  return labels[repeatType] || repeatType;
}

