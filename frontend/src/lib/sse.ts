import { getAccessToken } from "./auth";

const getBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl) {
    if (typeof window !== "undefined" && window.location.hostname === "127.0.0.1") {
      return envUrl.replace("localhost", "127.0.0.1");
    }
    return envUrl;
  }
  const host = typeof window !== "undefined" ? window.location.hostname : "localhost";
  return `http://${host}:8000`;
};

const API_PREFIX = "/api/v1";

export interface StreamEventHandlers {
  onToken: (token: string) => void;
  onCitations?: (citations: any[]) => void;
  onDone?: (messageId: string, outcome?: string) => void;
  onError?: (errorMsg: string) => void;
}

export interface StreamChatParams extends StreamEventHandlers {
  conversationId: string;
  content: string;
  signal?: AbortSignal;
}

export async function streamChatMessage(
  paramsOrConvId: StreamChatParams | string,
  contentOrHandlers?: string | StreamEventHandlers,
  handlersOrSignal?: StreamEventHandlers | AbortSignal,
  maybeSignal?: AbortSignal
) {
  let conversationId = "";
  let content = "";
  let handlers: StreamEventHandlers = { onToken: () => { } };
  let signal: AbortSignal | undefined;

  if (typeof paramsOrConvId === "object") {
    conversationId = paramsOrConvId.conversationId;
    content = paramsOrConvId.content;
    signal = paramsOrConvId.signal;
    handlers = {
      onToken: paramsOrConvId.onToken,
      onCitations: paramsOrConvId.onCitations,
      onDone: paramsOrConvId.onDone,
      onError: paramsOrConvId.onError,
    };
  } else {
    conversationId = paramsOrConvId;
    content = contentOrHandlers as string;
    handlers = handlersOrSignal as StreamEventHandlers;
    signal = maybeSignal;
  }

  const token = getAccessToken();
  const url = `${getBaseUrl()}${API_PREFIX}/conversations/${conversationId}/messages`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ content }),
    credentials: "include",
    signal,
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({ detail: "Stream connection failed" }));
    handlers.onError?.(errData.detail || "Stream connection failed");
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    handlers.onError?.("ReadableStream not supported");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";

    for (const part of parts) {
      if (!part.trim()) continue;
      const lines = part.split("\n");
      let eventType = "message";
      let eventData = "";

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          eventType = line.replace("event: ", "").trim();
        } else if (line.startsWith("data: ")) {
          eventData = line.replace("data: ", "").trim();
        }
      }

      if (!eventData) continue;

      try {
        const parsed = JSON.parse(eventData);
        if (eventType === "token") {
          handlers.onToken(parsed.token || "");
        } else if (eventType === "citations") {
          handlers.onCitations?.(parsed.citations || []);
        } else if (eventType === "done") {
          handlers.onDone?.(parsed.message_id, parsed.outcome);
        } else if (eventType === "error") {
          handlers.onError?.(parsed.detail || parsed.error || "An error occurred during generation");
        }
      } catch {
        // Ignore unparseable SSE frames
      }
    }
  }
}
