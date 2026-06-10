# Sample Documentation

This is a sample documentation file to test the Probe Docs MCP example.

## Installation

To install the package, run:

```bash
npm install @probelabs/probe
```

## Usage

Here's how to use the package:

```javascript
import { search } from '@probelabs/probe';

const results = await search({
  path: '/path/to/your/code',
  query: 'function example'
});

console.log(results);
```

## Configuration

You can configure the search with various options:

- `path`: The path to search in
- `query`: The search query
- `filesOnly`: Skip AST parsing and just output unique files
- `maxResults`: Maximum number of results to return
- `maxTokens`: Maximum tokens to return

## Advanced Features

### Custom Patterns

You can use custom patterns to search for specific code structures:

```javascript
import { query } from '@probelabs/probe';

const results = await query({
  path: '/path/to/your/code',
  pattern: 'function $NAME($$$PARAMS) $$$BODY'
});

console.log(results);
```

### Extracting Code

You can extract code from specific files:

```javascript
import { extract } from '@probelabs/probe';

const results = await extract({
  path: '/path/to/your/code',
  files: ['/path/to/your/code/file.js:10-20']
});

console.log(results);