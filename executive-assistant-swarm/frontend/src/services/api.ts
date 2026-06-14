import axios from 'axios';

// Connect to the FastAPI backend
const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds timeout (LLMs can be slow)
});

export interface ExecutionLog {
  agent: string;
  status: string;
}

export interface SwarmResult {
  status: string;
  final_summary: string;
  execution_log: ExecutionLog[];
  results: any;
}

export interface User {
  id: string;
  username: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Thread {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  role: string;
  content: string;
  execution_log?: string;
  created_at: string;
}

export const loginUser = async (username: string, password: string): Promise<AuthResponse> => {
  const response = await api.post('/auth/login', { username, password });
  return response.data;
};

export const registerUser = async (username: string, password: string, email: string): Promise<AuthResponse> => {
  const response = await api.post('/auth/register', { username, password, email });
  return response.data;
};

export const forgotPassword = async (username: string, email: string): Promise<{ message: string }> => {
  const response = await api.post('/auth/forgot-password', { username, email });
  return response.data;
};

export const resetPassword = async (username: string, code: string, newPassword: string): Promise<{ message: string }> => {
  const response = await api.post('/auth/reset-password', { username, code, new_password: newPassword });
  return response.data;
};

export const getThreads = async (token: string): Promise<Thread[]> => {
  const response = await api.get('/threads', {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

export const getThreadMessages = async (threadId: string, token: string): Promise<Message[]> => {
  const response = await api.get(`/threads/${threadId}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

export const createThread = async (title: string, token: string): Promise<{ id: string; title: string }> => {
  const response = await api.post('/threads', { title }, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

export const executeSwarm = async (prompt: string): Promise<SwarmResult> => {
  const response = await api.post('/execute', {
    user_prompt: prompt,
    use_mock_scheduler: false
  });
  return response.data;
};

export const executeSwarmStream = async (
  prompt: string,
  token: string | undefined,
  threadId: string | undefined,
  chatHistory: {role: string, content: string}[],
  onEvent: (event: any) => void,
  signal?: AbortSignal,
  imageBase64?: string,
  fileName?: string,
  fileBase64?: string
): Promise<void> => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json'
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}/execute/stream`, {
    method: 'POST',
    headers,
    signal,
    body: JSON.stringify({
      user_prompt: prompt,
      thread_id: threadId,
      image_base64: imageBase64,
      file_name: fileName,
      file_base64: fileBase64,
      chat_history: chatHistory.map(msg => ({ role: msg.role, content: msg.content })),
      use_mock_scheduler: false, // Switch to True AutoGen Swarm Mode
    })
  });

  if (!response.ok) {
    throw new Error(`Stream failed: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) return;

  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    let eventEndIndex;
    while ((eventEndIndex = buffer.indexOf('\n\n')) >= 0) {
      const eventStr = buffer.slice(0, eventEndIndex);
      buffer = buffer.slice(eventEndIndex + 2);

      const lines = eventStr.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6).trim();
          if (dataStr) {
            try {
              const parsedData = JSON.parse(dataStr);
              onEvent(parsedData);
            } catch (e) {
              console.error("Failed to parse SSE JSON:", dataStr, e);
            }
          }
        }
      }
    }
  }
};