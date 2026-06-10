import { NextRequest, NextResponse } from 'next/server';
import { fixMermaidSyntax } from '@/lib/gemini';

function getErrorMessage(error: unknown, fallback: string): string {
    return error instanceof Error ? error.message : fallback;
}

export async function POST(req: NextRequest) {
    try {
        const payload = await req.json() as {
            code?: unknown;
            syntaxError?: unknown;
            diagramType?: unknown;
        };
        const code = typeof payload.code === "string" ? payload.code : "";

        if (!code) {
            return NextResponse.json(
                { error: 'Missing code parameter' },
                { status: 400 }
            );
        }

        const fixed = await fixMermaidSyntax(code, {
            syntaxError: typeof payload.syntaxError === "string" ? payload.syntaxError : undefined,
            diagramType: typeof payload.diagramType === "string" ? payload.diagramType : undefined,
        });

        if (!fixed) {
            return NextResponse.json(
                { error: 'Failed to fix Mermaid syntax' },
                { status: 500 }
            );
        }

        return NextResponse.json({ fixed });
    } catch (error: unknown) {
        console.error('Error fixing Mermaid syntax:', error);
        return NextResponse.json(
            { error: getErrorMessage(error, 'Internal server error') },
            { status: 500 }
        );
    }
}
