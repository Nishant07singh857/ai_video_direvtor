'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/Button';
import { Card, CardContent } from '@/components/Card';
import { healthApi } from '@/lib/api';
import { HealthResponse } from '@/types';
import { cn } from '@/lib/utils';

export default function HomePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [dbHealth, setDbHealth] = useState<HealthResponse | null>(null);
  const [redisHealth, setRedisHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function checkHealth() {
      try {
        const [h, db, redis] = await Promise.all([
          healthApi.check(),
          healthApi.db(),
          healthApi.redis(),
        ]);
        setHealth(h.data);
        setDbHealth(db.data);
        setRedisHealth(redis.data);
      } catch (error) {
        console.error('Health check failed:', error);
      } finally {
        setLoading(false);
      }
    }
    checkHealth().catch(console.error);
  }, []);

  const getStatusBadge = (status: string | undefined) => {
    if (!status) return null;
    const configs: Record<string, { bg: string; text: string; label: string }> = {
      healthy: { bg: 'bg-green-100', text: 'text-green-800', label: 'Healthy' },
      unhealthy: { bg: 'bg-red-100', text: 'text-red-800', label: 'Unhealthy' },
      connected: { bg: 'bg-green-100', text: 'text-green-800', label: 'Connected' },
      disconnected: { bg: 'bg-red-100', text: 'text-red-800', label: 'Disconnected' },
    };
    const config = configs[status] || { bg: 'bg-gray-100', text: 'text-gray-800', label: status };
    return (
      <span className={cn('px-2 py-1 rounded-full text-xs font-medium', config.bg, config.text)}>
        {config.label}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <svg
                className="h-8 w-8 text-primary-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
              <h1 className="text-2xl font-bold text-gray-900">AI Video Director</h1>
            </div>
            <nav className="flex items-center gap-4">
              <Link href="/projects" className="text-gray-600 hover:text-gray-900">
                Projects
              </Link>
              <Link href="/projects">
                <Button>Create Project</Button>
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-gray-900 sm:text-5xl">
            Autonomous AI Video Editing
          </h2>
          <p className="mt-4 max-w-2xl mx-auto text-lg text-gray-600">
            Upload raw footage. AI understands, discovers the story, selects the best clips,
            creates a professional edit, critiques it, and improves it. Edit with natural language.
          </p>
        </div>

        {/* System Health */}
        <section className="mb-16">
          <h3 className="text-2xl font-bold text-gray-900 mb-6">System Health</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { title: 'Backend API', health, detail: health?.app },
              { title: 'PostgreSQL', health: dbHealth, detail: dbHealth?.database },
              { title: 'Redis', health: redisHealth, detail: redisHealth?.redis },
            ].map(({ title, health: h, detail }) => (
              <Card key={title} className={loading ? 'animate-pulse' : ''}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <h4 className="text-lg font-medium text-gray-900">{title}</h4>
                    {loading ? (
                      <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
                    ) : (
                      getStatusBadge(h?.status)
                    )}
                  </div>
                  {detail && !loading && (
                    <p className="mt-2 text-sm text-gray-500">{detail}</p>
                  )}
                  {!loading && h?.error && (
                    <p className="mt-2 text-sm text-red-600">{h.error}</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* Features */}
        <section className="mb-16">
          <h3 className="text-2xl font-bold text-gray-900 mb-6 text-center">Core Capabilities</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                icon: (
                  <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                ),
                title: 'Understand Footage',
                description: 'AI analyzes video, audio, speech, faces, emotions, and actions in every shot.',
              },
              {
                icon: (
                  <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                ),
                title: 'Discover Stories',
                description: 'Generates multiple story candidates from your footage and selects the strongest narrative.',
              },
              {
                icon: (
                  <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                ),
                title: 'Professional Edit',
                description: 'Creates timeline with pacing, music, captions, color, and transitions. Critiques and revises.',
              },
            ].map((feature, index) => (
              <Card key={index}>
                <CardContent className="pt-6">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100 text-primary-600">
                    {feature.icon}
                  </div>
                  <h4 className="mt-4 text-lg font-medium text-gray-900">{feature.title}</h4>
                  <p className="mt-2 text-gray-600">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* CTA */}
        <div className="text-center">
          <Link href="/projects">
            <Button size="lg" className="w-auto">
              Get Started - Create Project
            </Button>
          </Link>
          <p className="mt-4 text-sm text-gray-500">
            Or view existing projects
            <Link href="/projects" className="ml-2 text-primary-600 hover:underline">
              here
            </Link>
          </p>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500">
            AI Video Director &copy; 2024 - Phase 1 Foundation
          </p>
        </div>
      </footer>
    </div>
  );
}
