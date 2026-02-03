import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { Target, Plus, X, Save, Trash2, TrendingUp, Check } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface Goal {
  id: number;
  title: string;
  description: string | null;
  goal_type: string;
  target_count: number | null;
  current_count: number;
  start_date: string;
  end_date: string;
  status: string;
  progress_percentage: number | null;
  days_remaining: number | null;
  is_completed: boolean;
}

export const GoalsManager = () => {
  const { getToken } = useAuth();
  const { t } = useTranslation();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  
  const [formData, setFormData] = useState({
    goal_type: 'weekly',
    title: '',
    description: '',
    target_count: 3,
    start_date: '',
    end_date: '',
  });

  useEffect(() => {
    loadGoals();
  }, []);

  const loadGoals = async () => {
    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/calendar/goals?status=active`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setGoals(data);
    } catch (error) {
      console.error('Error loading goals:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const token = await getToken();
      await fetch(`${API_URL}/calendar/goals`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...formData,
          start_date: new Date(formData.start_date + 'T00:00:00').toISOString(),
          end_date: new Date(formData.end_date + 'T23:59:59').toISOString(),
        })
      });
      
      await loadGoals();
      resetForm();
    } catch (error) {
      console.error('Error creating goal:', error);
    }
  };

  const handleComplete = async (goalId: number) => {
    try {
      const token = await getToken();
      await fetch(`${API_URL}/calendar/goals/${goalId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status: 'completed' })
      });
      await loadGoals();
    } catch (error) {
      console.error('Error completing goal:', error);
    }
  };

  const handleDelete = async (goalId: number) => {
    if (!confirm(t('goals.deleteConfirm'))) return;
    
    try {
      const token = await getToken();
      await fetch(`${API_URL}/calendar/goals/${goalId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      await loadGoals();
    } catch (error) {
      console.error('Error deleting goal:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      goal_type: 'weekly',
      title: '',
      description: '',
      target_count: 3,
      start_date: '',
      end_date: '',
    });
    setShowAddForm(false);
  };

  const getThisWeekDates = () => {
    const now = new Date();
    const dayOfWeek = now.getDay();
    const startOfWeek = new Date(now);
    startOfWeek.setDate(now.getDate() - dayOfWeek);
    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 6);
    
    return {
      start: startOfWeek.toISOString().split('T')[0],
      end: endOfWeek.toISOString().split('T')[0]
    };
  };

  const quickSetWeekly = () => {
    const { start, end } = getThisWeekDates();
    setFormData({
      ...formData,
      goal_type: 'weekly',
      title: t('goals.title_placeholder'),
      target_count: 3,
      start_date: start,
      end_date: end
    });
    setShowAddForm(true);
  };

  if (loading) {
    return <div className="text-center py-8">{t('chat.loading')}</div>;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Target className="w-5 h-5 text-accent" />
          <h3 className="text-lg font-bold">{t('goals.title')}</h3>
        </div>
        <div className="flex gap-2">
          <button
            onClick={quickSetWeekly}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            {t('goals.weekly')}
          </button>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-dark transition-colors"
          >
            {showAddForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
            {showAddForm ? t('goals.cancel') : t('goals.new')}
          </button>
        </div>
      </div>

      {/* Add Form */}
      <AnimatePresence>
        {showAddForm && (
          <motion.form
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            onSubmit={handleSubmit}
            className="bg-white rounded-2xl p-6 shadow-lg border border-accent/20"
          >
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">{t('goals.title_input')}</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  placeholder={t('goals.title_placeholder')}
                  required
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-accent"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">{t('goals.type')}</label>
                  <select
                    value={formData.goal_type}
                    onChange={(e) => setFormData({...formData, goal_type: e.target.value})}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-accent"
                  >
                    <option value="weekly">{t('goals.weekly')}</option>
                    <option value="monthly">{t('goals.monthly')}</option>
                    <option value="custom">{t('goals.custom')}</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">{t('goals.target')}</label>
                  <input
                    type="number"
                    value={formData.target_count}
                    onChange={(e) => setFormData({...formData, target_count: parseInt(e.target.value)})}
                    min="1"
                    required
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-accent"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">{t('goals.startDate')}</label>
                  <input
                    type="date"
                    value={formData.start_date}
                    onChange={(e) => setFormData({...formData, start_date: e.target.value})}
                    required
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-accent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">{t('goals.endDate')}</label>
                  <input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => setFormData({...formData, end_date: e.target.value})}
                    required
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-accent"
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  type="submit"
                  className="flex items-center gap-2 px-6 py-2 bg-accent text-white rounded-lg hover:bg-accent-dark transition-colors"
                >
                  <Save className="w-4 h-4" />
                  {t('goals.save')}
                </button>
                <button
                  type="button"
                  onClick={resetForm}
                  className="px-6 py-2 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors"
                >
                  {t('goals.cancel')}
                </button>
              </div>
            </div>
          </motion.form>
        )}
      </AnimatePresence>

      {/* Goals List */}
      <div className="grid md:grid-cols-2 gap-4">
        {goals.length === 0 ? (
          <div className="col-span-2 text-center py-8 text-gray-500">
            {t('goals.noGoals')}
          </div>
        ) : (
          goals.map((goal) => (
            <motion.div
              key={goal.id}
              layout
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-gradient-to-br from-white to-blue-50 rounded-2xl p-6 shadow-lg border border-blue-200"
            >
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-2">
                  <Target className="w-5 h-5 text-accent" />
                  <h4 className="font-bold">{goal.title}</h4>
                </div>
                <button
                  onClick={() => handleDelete(goal.id)}
                  className="text-gray-400 hover:text-red-600 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Progress Bar */}
              <div className="mb-4">
                <div className="flex justify-between text-sm mb-2">
                  <span>{goal.current_count} / {goal.target_count} {t('goals.sessions')}</span>
                  <span className="font-bold">{Math.round(goal.progress_percentage || 0)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${goal.progress_percentage || 0}%` }}
                    className="bg-gradient-to-r from-accent to-green-500 h-3 rounded-full"
                  />
                </div>
              </div>

              {/* Status */}
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-gray-600">
                  <TrendingUp className="w-4 h-4" />
                  {goal.days_remaining !== null && goal.days_remaining > 0 ? (
                    <span>{goal.days_remaining} {t('goals.daysRemaining')}</span>
                  ) : (
                    <span className="text-red-600">{t('goals.ended')}</span>
                  )}
                </div>

                {goal.is_completed ? (
                  <span className="flex items-center gap-1 text-green-600 font-bold">
                    <Check className="w-4 h-4" />
                    {t('goals.completed')}
                  </span>
                ) : goal.current_count >= (goal.target_count || 0) ? (
                  <button
                    onClick={() => handleComplete(goal.id)}
                    className="px-3 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
                  >
                    {t('goals.complete')}
                  </button>
                ) : null}
              </div>
            </motion.div>
          ))
        )}
      </div>
    </div>
  );
};

