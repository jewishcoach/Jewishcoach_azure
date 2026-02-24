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

const LIGHT = { text: 'text-[#1E293B]', muted: 'text-[#64748B]', accent: 'text-[#0EA5E9]', card: 'bg-gray-50 border border-gray-200', input: 'border-gray-200 bg-white text-[#1E293B] placeholder-gray-400', btn: 'bg-[#0EA5E9] text-white', btnSecondary: 'bg-gray-200 text-[#1E293B]', progress: 'from-[#0EA5E9] to-[#38BDF8]' };
const DARK = { text: 'text-[#F5F5F0]', muted: 'text-[#F5F5F0]/70', card: 'bg-white/[0.06] border border-white/[0.1]', input: 'border-white/10 bg-white/[0.04] text-[#F5F5F0] placeholder-[#F5F5F0]/40', btn: '', btnSecondary: 'bg-white/10 text-[#F5F5F0]', progress: 'from-[#BF953F] to-[#FCF6BA]' };

interface GoalsManagerProps { variant?: 'light' | 'dark'; }
export const GoalsManager = ({ variant = 'dark' }: GoalsManagerProps) => {
  const { getToken } = useAuth();
  const { t } = useTranslation();
  const theme = variant === 'light' ? LIGHT : DARK;
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
    return <div className={`text-center py-8 ${theme.muted}`}>{t('chat.loading')}</div>;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Target className={`w-5 h-5 ${variant === 'light' ? 'text-[#0EA5E9]' : 'text-[#FCF6BA]'}`} />
          <h3 className={`text-lg font-bold ${theme.text}`}>{t('goals.title')}</h3>
        </div>
        <div className="flex gap-2">
          <button
            onClick={quickSetWeekly}
            className={`px-4 py-2 rounded-lg transition-colors text-sm ${variant === 'light' ? 'bg-gray-200 text-[#1E293B] hover:bg-gray-300' : 'bg-white/10 text-[#F5F5F0] hover:bg-white/15'}`}
          >
            {t('goals.weekly')}
          </button>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors"
            style={variant === 'light' ? { background: '#0EA5E9', color: 'white' } : { background: 'linear-gradient(45deg, #BF953F, #FCF6BA)', color: '#020617' }}
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
            className={`rounded-2xl p-6 border ${theme.card}`}
          >
            <div className="space-y-4">
              <div>
                <label className={`block text-sm font-medium mb-2 ${theme.text}`}>{t('goals.title_input')}</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  placeholder={t('goals.title_placeholder')}
                  required
                  className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-[#0EA5E9]/30 focus:outline-none ${variant === 'light' ? 'border-gray-200 bg-white text-[#1E293B] placeholder-gray-400' : 'border-white/10 bg-white/[0.04] text-[#F5F5F0] placeholder-[#F5F5F0]/40 focus:ring-[#FCF6BA]/30'}`}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={`block text-sm font-medium mb-2 ${theme.text}`}>{t('goals.type')}</label>
                  <select
                    value={formData.goal_type}
                    onChange={(e) => setFormData({...formData, goal_type: e.target.value})}
                    className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:outline-none ${variant === 'light' ? 'border-gray-200 bg-white text-[#1E293B] focus:ring-[#0EA5E9]/30' : 'border-white/10 bg-white/[0.04] text-[#F5F5F0] focus:ring-[#FCF6BA]/30'}`}
                  >
                    <option value="weekly">{t('goals.weekly')}</option>
                    <option value="monthly">{t('goals.monthly')}</option>
                    <option value="custom">{t('goals.custom')}</option>
                  </select>
                </div>

                <div>
                  <label className={`block text-sm font-medium mb-2 ${theme.text}`}>{t('goals.target')}</label>
                  <input
                    type="number"
                    value={formData.target_count}
                    onChange={(e) => setFormData({...formData, target_count: parseInt(e.target.value)})}
                    min="1"
                    required
                    className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:outline-none ${variant === 'light' ? 'border-gray-200 bg-white text-[#1E293B] focus:ring-[#0EA5E9]/30' : 'border-white/10 bg-white/[0.04] text-[#F5F5F0] focus:ring-[#FCF6BA]/30'}`}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={`block text-sm font-medium mb-2 ${theme.text}`}>{t('goals.startDate')}</label>
                  <input
                    type="date"
                    value={formData.start_date}
                    onChange={(e) => setFormData({...formData, start_date: e.target.value})}
                    required
                    className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:outline-none ${variant === 'light' ? 'border-gray-200 bg-white text-[#1E293B] focus:ring-[#0EA5E9]/30' : 'border-white/10 bg-white/[0.04] text-[#F5F5F0] focus:ring-[#FCF6BA]/30'}`}
                  />
                </div>

                <div>
                  <label className={`block text-sm font-medium mb-2 ${theme.text}`}>{t('goals.endDate')}</label>
                  <input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => setFormData({...formData, end_date: e.target.value})}
                    required
                    className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:outline-none ${variant === 'light' ? 'border-gray-200 bg-white text-[#1E293B] focus:ring-[#0EA5E9]/30' : 'border-white/10 bg-white/[0.04] text-[#F5F5F0] focus:ring-[#FCF6BA]/30'}`}
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  type="submit"
                  className="flex items-center gap-2 px-6 py-2 rounded-lg transition-colors"
                  style={variant === 'light' ? { background: '#0EA5E9', color: 'white' } : { background: 'linear-gradient(45deg, #BF953F, #FCF6BA)', color: '#020617' }}
                >
                  <Save className="w-4 h-4" />
                  {t('goals.save')}
                </button>
                <button
                  type="button"
                  onClick={resetForm}
                  className={`px-6 py-2 rounded-lg transition-colors ${variant === 'light' ? 'bg-gray-200 text-[#1E293B] hover:bg-gray-300' : 'bg-white/10 text-[#F5F5F0] hover:bg-white/15'}`}
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
          <div className={`col-span-2 text-center py-8 ${theme.muted}`}>
            {t('goals.noGoals')}
          </div>
        ) : (
          goals.map((goal) => (
            <motion.div
              key={goal.id}
              layout
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className={`rounded-2xl p-6 border ${theme.card}`}
            >
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-2">
                  <Target className={`w-5 h-5 ${variant === 'light' ? 'text-[#0EA5E9]' : 'text-[#FCF6BA]'}`} />
                  <h4 className={`font-bold ${theme.text}`}>{goal.title}</h4>
                </div>
                <button
                  onClick={() => handleDelete(goal.id)}
                  className={`${theme.muted} hover:text-red-400 transition-colors`}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Progress Bar */}
              <div className="mb-4">
                <div className={`flex justify-between text-sm mb-2 ${theme.muted}`}>
                  <span>{goal.current_count} / {goal.target_count} {t('goals.sessions')}</span>
                  <span className={`font-bold ${theme.text}`}>{Math.round(goal.progress_percentage || 0)}%</span>
                </div>
                <div className={`w-full rounded-full h-3 ${variant === 'light' ? 'bg-gray-200' : 'bg-white/10'}`}>
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${goal.progress_percentage || 0}%` }}
                    className={`bg-gradient-to-r h-3 rounded-full ${variant === 'light' ? 'from-[#0EA5E9] to-[#38BDF8]' : 'from-[#BF953F] to-[#FCF6BA]'}`}
                  />
                </div>
              </div>

              {/* Status */}
              <div className="flex items-center justify-between text-sm">
                <div className={`flex items-center gap-2 ${theme.muted}`}>
                  <TrendingUp className="w-4 h-4" />
                  {goal.days_remaining !== null && goal.days_remaining > 0 ? (
                    <span>{goal.days_remaining} {t('goals.daysRemaining')}</span>
                  ) : (
                    <span className="text-red-400">{t('goals.ended')}</span>
                  )}
                </div>

                {goal.is_completed ? (
                  <span className={`flex items-center gap-1 font-bold ${variant === 'light' ? 'text-[#0EA5E9]' : 'text-[#FCF6BA]'}`}>
                    <Check className="w-4 h-4" />
                    {t('goals.completed')}
                  </span>
                ) : goal.current_count >= (goal.target_count || 0) ? (
                  <button
                    onClick={() => handleComplete(goal.id)}
                    className={`px-3 py-1 rounded-lg transition-colors text-sm ${variant === 'light' ? 'bg-[#0EA5E9]/20 text-[#0EA5E9] hover:bg-[#0EA5E9]/30' : 'bg-[#FCF6BA]/20 text-[#FCF6BA] hover:bg-[#FCF6BA]/30'}`}
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

