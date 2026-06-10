import type { ComponentProps, ReactNode } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import rehypeHighlight from 'rehype-highlight'
import remarkGfm from 'remark-gfm'
import { cn } from '../lib/utils'
import { CodeBlock, InlineCode } from './code-block'

interface MarkdownProps {
  content: string
  className?: string
}

function getNodeText(node: unknown): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(getNodeText).join('')
  if (node && typeof node === 'object' && 'props' in node) {
    const props = (node as { props: { children?: unknown } }).props
    return getNodeText(props.children)
  }
  return ''
}

const components: Components = {
  h1: (props) => <h3 className="mt-4 mb-2 text-base font-semibold tracking-tight" {...props} />,
  h2: (props) => <h3 className="mt-4 mb-2 text-base font-semibold tracking-tight" {...props} />,
  h3: (props) => <h3 className="mt-3 mb-2 text-sm font-semibold tracking-tight" {...props} />,
  h4: (props) => <h4 className="mt-3 mb-1.5 text-sm font-semibold" {...props} />,
  p: (props) => <p className="my-2 leading-relaxed" {...props} />,
  ul: (props) => <ul className="my-2 ml-5 list-disc space-y-1" {...props} />,
  ol: (props) => <ol className="my-2 ml-5 list-decimal space-y-1" {...props} />,
  li: (props) => <li className="leading-relaxed" {...props} />,
  a: ({ href, children, ...rest }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer noopener"
      className="font-medium text-primary underline underline-offset-2 hover:opacity-80"
      {...rest}
    >
      {children}
    </a>
  ),
  blockquote: (props) => (
    <blockquote
      className="my-3 border-l-2 border-border pl-3 text-muted-foreground italic"
      {...props}
    />
  ),
  hr: () => <hr className="my-4 border-border" />,
  table: (props) => (
    <div className="my-3 overflow-x-auto">
      <table className="w-full border-collapse text-sm" {...props} />
    </div>
  ),
  th: (props) => (
    <th className="border border-border bg-muted/40 px-2 py-1 text-left font-semibold" {...props} />
  ),
  td: (props) => <td className="border border-border px-2 py-1" {...props} />,
  pre: ({ children }: ComponentProps<'pre'> & { children?: ReactNode }) => <>{children}</>,
  code: ({ className, children, ...rest }) => {
    const match = /language-(\w+)/.exec(className ?? '')
    const language = match?.[1]
    const isBlock = !!language || (typeof children === 'string' && children.includes('\n'))

    if (!isBlock) {
      return (
        <InlineCode className={className} {...rest}>
          {children}
        </InlineCode>
      )
    }

    const raw = getNodeText(children).replace(/\n$/, '')
    return (
      <CodeBlock language={language} raw={raw}>
        <code className={className}>{children}</code>
      </CodeBlock>
    )
  },
}

export function Markdown({ content, className }: MarkdownProps) {
  return (
    <div className={cn('text-sm', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
