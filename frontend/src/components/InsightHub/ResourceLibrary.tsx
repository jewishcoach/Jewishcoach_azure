import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Library, ExternalLink } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiClient } from '../../services/api';

interface Resource {
  id: string;
  title: string;
  type: 'pdf' | 'video' | 'article';
  url?: string;
  snippet?: string;
}

interface ResourceLibraryProps {
  currentPhase: string;
}

export const ResourceLibrary = ({ currentPhase }: ResourceLibraryProps) => {
  const { t, i18n } = useTranslation();
  const [resources, setResources] = useState<Resource[]>([]);
  const [isExpanded, setIsExpanded] = useState(false);
  const isRTL = i18n.dir() === 'rtl';

  useEffect(() => {
    const fetchResources = async () => {
      try {
        const data = await apiClient.getResources(currentPhase);
        setResources(data);
      } catch (error) {
        console.error('Error fetching resources:', error);
      }
    };

    if (currentPhase) {
      fetchResources();
    }
  }, [currentPhase]);

  if (!isExpanded && resources.length === 0) {
    return null; // Don't show if collapsed and empty
  }

  return (
    <div className="border-t border-accent/20 bg-primary-light/10">
      {/* Header - Always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-primary-light/20 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Library size={16} className="text-accent" />
          <h4 className="text-sm font-semibold text-primary">
            {isRTL ? 'ספרייה' : 'Resource Library'}
          </h4>
        </div>
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 12 12"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="text-primary-dark"
          >
            <path
              d="M2 4L6 8L10 4"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </motion.div>
      </button>

      {/* Content - Expandable */}
      {isExpanded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="px-4 pb-4 max-h-48 overflow-y-auto custom-scrollbar"
        >
          {resources.length === 0 ? (
            <p className="text-xs text-primary-dark/60 text-center py-4">
              {isRTL
                ? 'אין משאבים זמינים כרגע'
                : 'No resources available at the moment'}
            </p>
          ) : (
            <div className="space-y-2">
              {resources.map((resource) => (
                <ResourceCard key={resource.id} resource={resource} isRTL={isRTL} />
              ))}
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
};

const ResourceCard = ({ resource, isRTL }: { resource: Resource; isRTL: boolean }) => {
  return (
    <div className="bg-white/80 rounded-lg p-3 border border-accent/10 hover:border-accent/30 transition-all">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <h5 className="text-sm font-medium text-primary mb-1">{resource.title}</h5>
          {resource.snippet && (
            <p className="text-xs text-primary-dark/70 line-clamp-2">{resource.snippet}</p>
          )}
        </div>
        {resource.url && (
          <a
            href={resource.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-shrink-0 text-accent hover:text-accent-dark"
          >
            <ExternalLink size={14} />
          </a>
        )}
      </div>
    </div>
  );
};




