#!/usr/bin/env node
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

// Get the directory of the current module
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path to the MCP server script
const mcpServerPath = path.join(__dirname, 'bin', 'probe-docs-mcp');

// Sample MCP request
const mcpRequest = {
	jsonrpc: '2.0',
	id: '1',
	method: 'mcp.callTool',
	params: {
		name: 'search_docs',
		arguments: {
			query: 'installation',
			maxResults: 5,
			maxTokens: 2000
		}
	}
};

// Start the MCP server
console.log('Starting MCP server...');
const mcpServer = spawn(mcpServerPath, [], {
	stdio: ['pipe', 'pipe', process.stderr]
});

// Handle server output
let buffer = '';
mcpServer.stdout.on('data', (data) => {
	buffer += data.toString();

	// Check if we have a complete JSON response
	try {
		const lines = buffer.split('\n');
		for (let i = 0; i < lines.length; i++) {
			const line = lines[i].trim();
			if (line && line.startsWith('{') && line.endsWith('}')) {
				const response = JSON.parse(line);
				console.log('\nReceived response:');
				console.log(JSON.stringify(response, null, 2));

				// Exit after receiving the response
				console.log('\nTest completed successfully!');
				mcpServer.kill();
				process.exit(0);
			}
		}
	} catch (error) {
		// Not a complete JSON response yet, continue buffering
	}
});

// Send the request after a short delay to allow the server to start
setTimeout(() => {
	console.log('\nSending request:');
	console.log(JSON.stringify(mcpRequest, null, 2));
	mcpServer.stdin.write(JSON.stringify(mcpRequest) + '\n');
}, 1000);

// Handle server exit
mcpServer.on('exit', (code) => {
	if (code !== 0) {
		console.error(`MCP server exited with code ${code}`);
		process.exit(code);
	}
});

// Handle process termination
process.on('SIGINT', () => {
	mcpServer.kill();
	process.exit(0);
});