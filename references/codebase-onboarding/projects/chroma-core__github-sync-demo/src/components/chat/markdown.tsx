import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";

export const components = {
  code: ({ node, inline, className, children, ...props }: any) => {
    const match = /language-(\w+)/.exec(className || "");
    const language = match ? match[1] : "";

    if (!inline && language) {
      return (
        <SyntaxHighlighter
          style={oneLight}
          language={language}
          PreTag="div"
          className="rounded-md text-xs border-[.1px] border-border"
          showLineNumbers={true}
          {...props}
        >
          {String(children).replace(/\n$/, "")}
        </SyntaxHighlighter>
      );
    }

    return (
      <code
        className={`${className} text-sm bg-secondary py-0.5 px-1 rounded-sm break-words whitespace-pre-wrap`}
        {...props}
      >
        {children}
      </code>
    );
  },
  ol: ({ node, children, ...props }: any) => {
    return (
      <ol
        className="space-y-3 list-decimal ml-[3.2ch]"
        style={{ listStyleType: "decimal-leading-zero" }}
        {...props}
      >
        {children}
      </ol>
    );
  },
  li: ({ node, children, ...props }: any) => {
    return (
      <li className="leading-normal list-outside" {...props}>
        {children}
      </li>
    );
  },
  ul: ({ node, children, ...props }: any) => {
    return (
      <ul className="list-disc list-inside ml-4" {...props}>
        {children}
      </ul>
    );
  },
  strong: ({ node, children, ...props }: any) => {
    return (
      <span className="font-semibold" {...props}>
        {children}
      </span>
    );
  },
};
