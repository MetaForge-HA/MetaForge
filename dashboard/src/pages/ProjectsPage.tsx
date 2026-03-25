import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useProjects, useCreateProject } from '../hooks/use-projects';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/shared/StatusBadge';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonCard } from '../components/ui/Skeleton';
import { useToast } from '../components/ui/Toast';
import { formatRelativeTime } from '../utils/format-time';

export function ProjectsPage() {
  const { data: projects, isLoading, isError, refetch } = useProjects();
  const createProject = useCreateProject();
  const toast = useToast();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  if (isLoading) {
    return (
      <div data-testid="loading-skeleton">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">Projects</h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div>
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">Projects</h2>
        </div>
        <Card className="flex flex-col items-center py-12 text-center">
          <p className="text-base font-medium text-red-600 dark:text-red-400">
            Failed to load projects
          </p>
          <p className="mt-1 text-sm text-zinc-500">
            There was a problem fetching your projects.
          </p>
          <Button variant="secondary" className="mt-4" onClick={() => void refetch()}>
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    createProject.mutate(
      { name: name.trim(), description: description.trim() },
      {
        onSuccess: () => {
          setName('');
          setDescription('');
          setShowForm(false);
          toast.success('Project created successfully.');
        },
        onError: (err) => {
          toast.error((err as Error)?.message ?? 'Failed to create project.');
        },
      },
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
          Projects
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-zinc-500">{projects?.length ?? 0} projects</span>
          <Button
            type="button"
            variant="primary"
            onClick={() => setShowForm(!showForm)}
          >
            {showForm ? 'Cancel' : 'New Project'}
          </Button>
        </div>
      </div>

      {showForm && (
        <Card className="mb-6">
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label
                htmlFor="project-name"
                className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300"
              >
                Project name
              </label>
              <input
                id="project-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Drone Flight Controller"
                className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm placeholder:text-zinc-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100 dark:placeholder:text-zinc-500"
              />
            </div>
            <div>
              <label
                htmlFor="project-desc"
                className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300"
              >
                Description
              </label>
              <textarea
                id="project-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                placeholder="Brief project description"
                className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm placeholder:text-zinc-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100 dark:placeholder:text-zinc-500"
              />
            </div>
            <Button
              type="submit"
              variant="primary"
              disabled={!name.trim() || createProject.isPending}
            >
              {createProject.isPending ? 'Creating...' : 'Create Project'}
            </Button>
          </form>
        </Card>
      )}

      {!projects?.length ? (
        <EmptyState
          title="No projects yet"
          description="Create a project with the button above or run 'forge setup' to get started."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Link key={project.id} to={`/projects/${project.id}`}>
              <Card className="transition-shadow hover:shadow-md">
                <div className="mb-3 flex items-start justify-between">
                  <h3 className="font-medium text-zinc-900 dark:text-zinc-100">
                    {project.name}
                  </h3>
                  <StatusBadge status={project.status} />
                </div>
                <p className="mb-4 text-sm text-zinc-500 line-clamp-2">
                  {project.description}
                </p>
                <div className="flex items-center justify-between text-xs text-zinc-400">
                  <span>{project.work_products.length} work_products</span>
                  <span>{project.agentCount} agents</span>
                  <span>{formatRelativeTime(project.lastUpdated)}</span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
