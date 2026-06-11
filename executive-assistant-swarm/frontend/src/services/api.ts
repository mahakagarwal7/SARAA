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
  onEvent: (event: any) => void,
  signal?: AbortSignal
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
      use_mock_scheduler: !token // Force mock mode if no token is provided
    })
  });

  if (!response.ok) {
    throw new Error(`Stream failed: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) return;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const dataStr = line.replace('data: ', '').trim();
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
};