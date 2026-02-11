'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getProjects, Project } from '@/lib/api';
import { Grid3x3 } from 'lucide-react';

export default function KanbanIndexPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProjects();

    // Check for last-visited project in localStorage
    const lastProjectId = localStorage.getItem('kanban-last-project');
    if (lastProjectId) {
      router.push(`/projects/${lastProjectId}/board`);
    }
  }, []);

  const loadProjects = async () => {
    try {
      const data = await getProjects();
      setProjects(data);
    } catch (error) {
      console.error('Failed to load projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleProjectSelect = (projectId: number) => {
    localStorage.setItem('kanban-last-project', projectId.toString());
    router.push(`/projects/${projectId}/board`);
  };

  if (loading) {
    return <div className="p-8">Loading...</div>;
  }

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Kanban Board</h1>
          <p className="text-gray-600">Select a project to view its Kanban board</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {projects.map(project => (
            <button
              key={project.id}
              onClick={() => handleProjectSelect(project.id)}
              className="p-6 bg-white rounded-xl border border-gray-200 hover:border-indigo-300 hover:shadow-md transition-all text-left"
            >
              <div className="flex items-center gap-3 mb-2">
                <Grid3x3 className="w-6 h-6 text-indigo-600" />
                <h2 className="text-xl font-semibold text-gray-900">{project.name}</h2>
              </div>
              {project.description && (
                <p className="text-gray-600 text-sm">{project.description}</p>
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
