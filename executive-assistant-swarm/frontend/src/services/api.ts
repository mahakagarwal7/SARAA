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
    use_mock_scheduler: true // Keep true until your teammate fixes Graph API
  });
  return response.data;
};