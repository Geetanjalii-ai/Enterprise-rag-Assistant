import { describe, it, expect, vi, beforeEach } from 'vitest';
import { streamChatMessage } from './sse';
import { getAccessToken } from './auth';

vi.mock('./auth', () => ({
  getAccessToken: vi.fn(),
}));

describe('streamChatMessage SSE parser', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('correctly dispatches token, citations, and done events', async () => {
    (getAccessToken as any).mockReturnValue('mock-jwt-token');

    const ssePayload = [
      'event: token\ndata: {"token": "Hello "}\n\n',
      'event: token\ndata: {"token": "world!"}\n\n',
      'event: citations\ndata: {"citations": [{"chunk_id": "c1", "document_title": "Handbook"}]}\n\n',
      'event: done\ndata: {"message_id": "msg-123"}\n\n',
    ].join('');

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(ssePayload));
        controller.close();
      },
    });

    (globalThis as any).fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: stream,
    });

    const tokens: string[] = [];
    const citationsList: any[] = [];
    let savedDoneId = '';

    await streamChatMessage({
      conversationId: 'conv-1',
      content: 'Hello',
      onToken: (tok: string) => tokens.push(tok),
      onCitations: (c: any[]) => citationsList.push(...c),
      onDone: (id: string) => {
        savedDoneId = id;
      },
      onError: (err: string) => {
        throw new Error(err);
      },
    });

    expect(tokens.join('')).toBe('Hello world!');
    expect(citationsList).toHaveLength(1);
    expect(citationsList[0].document_title).toBe('Handbook');
    expect(savedDoneId).toBe('msg-123');
  });

  it('handles error response from server', async () => {
    (getAccessToken as any).mockReturnValue('mock-jwt-token');

    (globalThis as any).fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      json: vi.fn().mockResolvedValue({ detail: 'Forbidden' }),
    });

    let reportedError = '';
    await streamChatMessage({
      conversationId: 'conv-1',
      content: 'Hello',
      onToken: () => {},
      onCitations: () => {},
      onDone: () => {},
      onError: (err: string) => {
        reportedError = err;
      },
    });

    expect(reportedError).toContain('Forbidden');
  });
});
