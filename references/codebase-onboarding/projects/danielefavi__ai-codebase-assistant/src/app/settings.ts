export const EXT_TO_LANG: Record<string, string> = {
  html: 'html',
  htm: 'html',
  cpp: 'cpp',
  h: 'cpp',
  hpp: 'cpp',
  go: 'go',
  java: 'java',
  js: 'js',
  ts: 'js',
  php: 'php',
  proto: 'proto',
  py: 'python',
  rst: 'rst',
  ruby: 'ruby',
  rs: 'rust',
  scala: 'scala',
  swift: 'swift',
  md: 'markdown',
  tex: 'latex',
  sol: 'sol'
}

export const PROMPT_TO_SUMMARIZE_FULL_FILE: string = ``;



export const PROMPT_FOR_SUMMARIZING_TEXT: string = `You are an AI assistant specialized in summarizing technical documentation.
Your task is to read the following text, which may contain technical language related to software systems, architecture, or implementation details.
Provide a concise summary (2 to 4 sentences) that captures the main idea and key points, making it easy for developers to quickly understand the content.
Avoid repeating the original text verbatim and exclude any unnecessary detail or boilerplate.

{contextInfo}

Input Text:
{inputText}`;



export const PROMPT_FOR_SUMMARIZING_CODE: string = `You are a senior software engineer with deep expertise in reading and interpreting code.
Your task is to analyze the provided code snippet and its contextual information, then generate a concise and clear summary of what the code does.
Focus on clarity and brevity. Avoid repeating comments or variable names unless they are essential to understanding the logic.

{contextInfo}

Code Snippet:
{inputText}`;



export const PROMPT_FOR_REFINING_PROMPT: string = `You are an AI assistant. Rephrase a user's question into a search query.

### Example
User Question: "How do I add an item to the cart?"
Rephrased Search Query: "Code for adding a product to the shopping cart."

### Example
User Question: "Where are the API routes?"
Rephrased Search Query: "File defining the application's API endpoints and routing logic."

### Example
User Question: "What happens during user signup?"
Rephrased Search Query: "User registration process, including validation, user creation, and password hashing."

### Task
User Question: "{userQuestion}"
Rephrased Search Query:`;



export const PROMPT_USER_QUERY_AND_DATA_CONTEXT: string = `As a senior software engineer, your primary role is to answer the user's question about a codebase using the provided code snippets as your sole source of truth.

**Instructions:**
1.  Carefully analyze the code snippets provided in the "Context" section.
2.  Formulate a clear and concise answer to the "User Question" based *exclusively* on this context.
3.  Do not use any external knowledge or make assumptions about the codebase that are not supported by the context.
4.  If you write code, ensure it aligns with the style and conventions found in the provided snippets.
5.  If the context is insufficient to answer the question, respond with: "I cannot answer this question based on the provided code snippets."

---

**Context:**
{contextData}


---

**User Question:**
{userQuery}


---

**Your Answer:**`;