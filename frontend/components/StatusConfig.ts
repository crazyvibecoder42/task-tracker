import { Inbox, Circle, PlayCircle, XCircle, Eye, CheckCircle2, MinusCircle } from 'lucide-react';

export const STATUS_CONFIG = {
  backlog: {
    color: 'bg-gray-100 text-gray-700 border-gray-300',
    icon: Inbox,
    label: 'Backlog'
  },
  todo: {
    color: 'bg-blue-100 text-blue-700 border-blue-300',
    icon: Circle,
    label: 'To Do'
  },
  in_progress: {
    color: 'bg-yellow-100 text-yellow-700 border-yellow-300',
    icon: PlayCircle,
    label: 'In Progress'
  },
  blocked: {
    color: 'bg-red-100 text-red-700 border-red-300',
    icon: XCircle,
    label: 'Blocked'
  },
  review: {
    color: 'bg-purple-100 text-purple-700 border-purple-300',
    icon: Eye,
    label: 'Review'
  },
  done: {
    color: 'bg-green-100 text-green-700 border-green-300',
    icon: CheckCircle2,
    label: 'Done'
  },
  not_needed: {
    color: 'bg-slate-100 text-slate-500 border-slate-300',
    icon: MinusCircle,
    label: 'Not Needed'
  }
} as const;

export type TaskStatus = keyof typeof STATUS_CONFIG;
