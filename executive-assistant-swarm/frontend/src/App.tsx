import { useState } from 'react';
import { 
  FluentProvider, 
  webLightTheme, 
  Button, 
  Textarea, 
  Title1, 
  Text, 
  Card, 
  CardHeader, 
  Spinner,
  Badge,
  Field
} from '@fluentui/react-components';
import { 
  Bot24Regular, 
  Send24Regular, 
  CheckmarkCircle24Regular,
  Play24Regular 
} from '@fluentui/react-icons';
import { executeSwarm, type SwarmResult } from './services/api';
import './App.css';

function App() {
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<SwarmResult | null>(null);
  const [error, setError] = useState('');

  const handleExecute = async () => {
    if (!prompt.trim()) return;
    
    setIsLoading(true);
    setResult(null);
    setError('');

    try {
      const response = await executeSwarm(prompt);
      setResult(response);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to connect to the Agent Swarm. Is the backend running?');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <FluentProvider theme={webLightTheme}>
      <div className="app-container">
        {/* Header */}
        <header className="app-header">
          <div className="logo-container">
            <Bot24Regular className="logo-icon" />
            <Title1 as="h1">Executive Assistant Agent Swarm</Title1>
          </div>
          <Text size={300} className="subtitle">
            Autonomous AI agents orchestrating research, scheduling, and briefing generation.
          </Text>
        </header>

        {/* Input Section */}
        <Card className="input-card">
          <CardHeader 
            header={<Text weight="semibold">Enter Executive Request</Text>} 
            description="The Orchestrator will automatically decompose this into tasks for the Research, Scheduler, and Briefing agents."
          />
          <Field>
            <Textarea 
              appearance="outline" 
              placeholder="e.g., I have a strategy meeting with Contoso next week. Research their latest AI product launches, check my calendar for conflicts, and generate a prep briefing."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={4}
              disabled={isLoading}
            />
          </Field>
          <div className="button-container">
            <Button 
              appearance="primary" 
              icon={<Send24Regular />} 
              onClick={handleExecute} 
              disabled={isLoading || !prompt.trim()}
              size="large"
            >
              {isLoading ? 'Swarm Processing...' : 'Execute Swarm'}
            </Button>
          </div>
        </Card>

        {/* Loading / Agent Status Section */}
        {isLoading && (
          <Card className="status-card">
            <CardHeader 
              header={<Text weight="semibold">🔄 Agent Swarm Active</Text>} 
            />
            <div className="agent-steps">
              <div className="step active"><Badge appearance="filled" color="brand">1</Badge> Orchestrator decomposing task...</div>
              <div className="step active"><Badge appearance="filled" color="brand">2</Badge> Research Agent browsing web...</div>
              <div className="step active"><Badge appearance="filled" color="brand">3</Badge> Scheduler Agent checking Graph API...</div>
              <div className="step active"><Badge appearance="filled" color="brand">4</Badge> Briefing Agent generating document...</div>
            </div>
            <div className="spinner-container">
              <Spinner size="large" label="Agents are collaborating..." />
            </div>
          </Card>
        )}

        {/* Error Section */}
        {error && (
          <Card className="error-card">
            <Text weight="semibold" style={{color: 'red'}}>⚠️ Error: {error}</Text>
          </Card>
        )}

        {/* Results Section */}
        {result && (
          <div className="results-container">
            {/* Execution Log */}
            <Card className="result-card">
              <CardHeader 
                header={<Text weight="semibold">📊 Execution Log</Text>} 
                image={<Play24Regular />}
              />
              <div className="log-container">
                {result.execution_log.map((log, index) => (
                  <div key={index} className="log-item">
                    <CheckmarkCircle24Regular style={{ color: '#107c10' }} />
                    <Text><strong>{log.agent}:</strong> {log.status}</Text>
                  </div>
                ))}
              </div>
            </Card>

            {/* Final Summary */}
            <Card className="result-card highlight-card">
              <CardHeader 
                header={<Text weight="semibold" size={400}>📝 Executive Summary</Text>} 
              />
              <Text size={300} className="summary-text">{result.final_summary}</Text>
            </Card>

            {/* Detailed Briefing */}
            {result.results?.briefing && (
              <Card className="result-card">
                <CardHeader 
                  header={<Text weight="semibold" size={400}>📋 Generated Briefing Document</Text>} 
                />
                <div className="briefing-content">
                  <pre>{result.results.briefing.briefing_markdown}</pre>
                </div>
              </Card>
            )}
          </div>
        )}
      </div>
    </FluentProvider>
  );
}

export default App;