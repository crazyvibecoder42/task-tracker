'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface MarkdownRendererProps {
  content: string;
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  // Sanitize link URLs to prevent XSS via javascript: or data: protocols
  const sanitizeUrl = (url: string | undefined): string => {
    if (!url) return '';

    // Allow only safe protocols
    const allowedProtocols = ['http:', 'https:', 'mailto:'];
    try {
      const parsedUrl = new URL(url, window.location.href);
      if (allowedProtocols.includes(parsedUrl.protocol)) {
        return url;
      }
    } catch {
      // Invalid URL or relative URL - treat as safe if it doesn't contain ':'
      if (!url.includes(':')) {
        return url;
      }
    }

    // Unsafe protocol detected - return empty string
    return '';
  };

  return (
    <div className="prose prose-sm max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.test(className || '') ? /language-(\w+)/.exec(className || '') : null;
            return !inline && match ? (
              <SyntaxHighlighter
                style={vscDarkPlus}
                language={match[1]}
                PreTag="div"
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            ) : (
              <code className="bg-gray-100 text-red-600 px-1 py-0.5 rounded text-sm" {...props}>
                {children}
              </code>
            );
          },
          a({ node, children, href, ...props }: any) {
            const safeHref = sanitizeUrl(href);
            return (
              <a
                href={safeHref}
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-600 hover:text-indigo-800 underline"
                {...props}
              >
                {children}
              </a>
            );
          },
          h1: ({ node, children, ...props }: any) => (
            <h1 className="text-2xl font-bold mt-6 mb-4" {...props}>
              {children}
            </h1>
          ),
          h2: ({ node, children, ...props }: any) => (
            <h2 className="text-xl font-bold mt-5 mb-3" {...props}>
              {children}
            </h2>
          ),
          h3: ({ node, children, ...props }: any) => (
            <h3 className="text-lg font-semibold mt-4 mb-2" {...props}>
              {children}
            </h3>
          ),
          ul: ({ node, children, ...props }: any) => (
            <ul className="list-disc list-inside my-3 space-y-1" {...props}>
              {children}
            </ul>
          ),
          ol: ({ node, children, ...props }: any) => (
            <ol className="list-decimal list-inside my-3 space-y-1" {...props}>
              {children}
            </ol>
          ),
          p: ({ node, children, ...props }: any) => (
            <p className="my-3 leading-relaxed" {...props}>
              {children}
            </p>
          ),
          blockquote: ({ node, children, ...props }: any) => (
            <blockquote className="border-l-4 border-gray-300 pl-4 italic my-4" {...props}>
              {children}
            </blockquote>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
