import { useState, useEffect, useCallback } from 'react';
import { Calendar as RBCalendar, dateFnsLocalizer } from 'react-big-calendar';
import { format, parse, startOfWeek, getDay } from 'date-fns';
import { enUS } from 'date-fns/locale';
import { FiChevronLeft, FiChevronRight } from 'react-icons/fi';
import { calendarApi } from '../services/api';
import { getPriorityColor } from '../utils/date';

const locales = { 'en-US': enUS };
const localizer = dateFnsLocalizer({ format, parse, startOfWeek, getDay, locales });

export default function CalendarPage() {
  const [events, setEvents] = useState([]);
  const [selectedDate, setSelectedDate] = useState(null);
  const [dayTasks, setDayTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dayTasksLoading, setDayTasksLoading] = useState(false);
  const [view, setView] = useState('month');

  useEffect(() => {
    fetchEvents();
  }, []);

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const res = await calendarApi.getTasks();
      const tasks = Array.isArray(res.data) ? res.data : [];
      const formattedEvents = tasks.map(task => ({
        id: task.id,
        title: task.title,
        start: task.start ? new Date(task.start) : new Date(task.due_date),
        end: task.end ? new Date(task.end) : new Date(task.due_date),
        allDay: true,
        priority: task.priority,
        status: task.status,
        assigned_to: task.assigned_to,
        assigned_to_name: task.assigned_to_name,
      }));
      setEvents(formattedEvents);
    } catch (error) {
      console.error('Failed to fetch calendar events:', error);
      setEvents([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSlot = useCallback(({ start, end }) => {
    const dateStr = format(start, 'yyyy-MM-dd');
    fetchDayTasks(dateStr);
  }, []);

  const handleSelectEvent = useCallback((event) => {
    // Could open task detail or navigate to task
    }, []);

  const fetchDayTasks = async (dateStr) => {
    setDayTasksLoading(true);
    try {
      const res = await calendarApi.getDayTasks(dateStr);
      setDayTasks(Array.isArray(res.data) ? res.data : []);
      setSelectedDate(new Date(dateStr));
    } catch (error) {
      console.error('Failed to fetch day tasks:', error);
      setDayTasks([]);
    } finally {
      setDayTasksLoading(false);
    }
  };

  const CustomEvent = ({ event }) => {
    if (!event) return null;
    const priorityColor = getPriorityColor(event.priority || 'Medium');
    const statusColor = event.status === 'Done' ? 'border-green-500' :
                       event.status === 'In Progress' ? 'border-blue-500' : 'border-gray-400';

    return (
      <div
        className={`w-full h-full px-1.5 py-1 rounded-sm text-xs flex flex-col justify-center overflow-hidden ${priorityColor} border-l-2 ${statusColor} shadow-sm hover:opacity-80`}
        title={`${event.title} (${event.status})`}
      >
        <span className="font-medium truncate leading-tight">{event.title}</span>
        {event.assigned_to_name && (
          <span className="text-[10px] opacity-75 truncate">{event.assigned_to_name}</span>
        )}
      </div>
    );
  };

  const messages = {
    next: () => <FiChevronRight className="w-4 h-4" />,
    previous: () => <FiChevronLeft className="w-4 h-4" />,
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Calendar</h1>
      </div>

      <div className="card overflow-hidden">
        <div className="h-[600px] lg:h-[700px]">
          <RBCalendar
            localizer={localizer}
            events={events}
            defaultView="month"
            view={view}
            onView={setView}
            onSelectEvent={handleSelectEvent}
            onSelectSlot={handleSelectSlot}
            selectable
            components={{
              event: CustomEvent,
            }}
            messages={messages}
            className="h-full rbc-custom dark:text-gray-100 rbc-month-view"
            popup
          />
        </div>
      </div>

      {/* Selected day's tasks modal */}
      {selectedDate && (
        <div className="modal-backdrop" onClick={() => setSelectedDate(null)}>
          <div className="modal-content max-w-lg" onClick={(e) => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Tasks for {selectedDate.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
              </h2>
              <button onClick={() => setSelectedDate(null)} className="p-2 hover:bg-gray-100 dark:hover:bg-dark-800 rounded-lg">
                ×
              </button>
            </div>

            <div className="p-6 max-h-96 overflow-y-auto">
              {dayTasksLoading ? (
                <div className="flex justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
                </div>
              ) : dayTasks.length === 0 ? (
                <div className="text-center py-8 text-gray-600 dark:text-gray-400">
                  <p>No tasks due on this day.</p>
                  <button
                    onClick={() => {
                      setSelectedDate(null);
                      window.location.href = '/tasks?new=true';
                    }}
                    className="mt-3 btn-primary text-sm"
                  >
                    Add Task
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {dayTasks.map(task => (
                    <div
                      key={task.id}
                      onClick={() => {
                        setSelectedDate(null);
                        window.location.href = `/tasks/${task.id}`;
                      }}
                      className="p-3 bg-gray-50 dark:bg-dark-800 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-700 cursor-pointer transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="font-medium text-gray-900 dark:text-white">{task.title}</h4>
                          <div className="flex items-center gap-2 mt-1">
                            <span className={`px-2 py-0.5 text-xs rounded-full ${
                              task.status === 'Done' ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300' :
                              task.status === 'In Progress' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300' :
                              'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                            }`}>
                              {task.status}
                            </span>
                            <span className={`px-2 py-0.5 text-xs rounded-full ${
                              task.priority === 'Urgent' ? 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300' :
                              task.priority === 'High' ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300' :
                              task.priority === 'Medium' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300' :
                              'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300'
                            }`}>
                              {task.priority}
                            </span>
                          </div>
                        </div>
                        {task.assignee && (
                          <img src={task.assignee.avatar_url} alt="" className="w-6 h-6 rounded-full" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
