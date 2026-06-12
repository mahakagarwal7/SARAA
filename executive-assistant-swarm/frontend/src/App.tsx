import { useRef, useState, useEffect } from 'react';
import { 
  FluentProvider, 
  webDarkTheme, 
  Button, 
  Title1, 
  Text, 
  Toaster,
  useId,
  useToastController,
  Toast,
  ToastTitle,
  ToastBody
} from '@fluentui/react-components';
import {
  Bot24Regular, 
  Send24Regular, 
  Stop24Regular,
  Search24Regular,
  Edit24Regular,
  CalendarLtr24Regular,
  Person24Regular,
  Mic24Regular,
  MicOff24Regular
} from '@fluentui/react-icons';
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { loginRequest } from "./authConfig";
import { executeSwarmStream, type SwarmResult } from './services/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import * as THREE from 'three';
// @ts-ignore
import NET from 'vanta/src/vanta.net';
import './App.css';

function getAgentColor(agentName: string) {
  const name = agentName.toLowerCase();
  if (name.includes('research')) return '#3b82f6'; 
  if (name.includes('write') || name.includes('briefing')) return '#10b981'; 
  if (name.includes('schedul') || name.includes('calendar')) return '#f59e0b'; 
  if (name.includes('orchestrator') || name.includes('executor')) return '#8b5cf6'; 
  return '#64748b'; 
}

function getAgentIcon(agentName: string) {
  const name = agentName.toLowerCase();
  if (name.includes('research')) return <Search24Regular />;
  if (name.includes('write') || name.includes('briefing')) return <Edit24Regular />;
  if (name.includes('schedul') || name.includes('calendar')) return <CalendarLtr24Regular />;
  if (name.includes('orchestrator') || name.includes('executor')) return <Bot24Regular />;
  return <Person24Regular />;
}

function AppContent() {
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<SwarmResult | null>(null);
  const [liveLogs, setLiveLogs] = useState<{agent: string, status: string}[]>([]);
  const [isInputEmptyError, setIsInputEmptyError] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechError, setSpeechError] = useState<string | null>(null);

  const vantaRef = useRef<HTMLDivElement>(null);
  const searchBarRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  // Magnetic Cursor Tracking for the Vercel Glow
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!searchBarRef.current) return;
    const rect = searchBarRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    searchBarRef.current.style.setProperty('--mouse-x', `${x}px`);
    searchBarRef.current.style.setProperty('--mouse-y', `${y}px`);
  };

  // Initialize SpeechRecognition
  useEffect(() => {
    // @ts-ignore
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = true;
      
      recognitionRef.current.onresult = (event: any) => {
        let finalTranscript = '';
        let interimTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }
        if (finalTranscript) {
          setPrompt(prev => prev + (prev ? ' ' : '') + finalTranscript);
        }
      };

      recognitionRef.current.onerror = (event: any) => {
        setSpeechError('Speech recognition error: ' + event.error);
        setIsListening(false);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    } else {
      setSpeechError('Speech recognition is not supported in this browser.');
    }
  }, []);

  const toggleListen = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      setSpeechError(null);
      try {
        recognitionRef.current?.start();
        setIsListening(true);
      } catch (e) {
        console.error("Speech recognition error:", e);
      }
    }
  };

  useEffect(() => {
    let vantaEffect: any;
    if (vantaRef.current) {
      vantaEffect = NET({
        el: vantaRef.current,
        THREE: THREE,
        mouseControls: true,
        touchControls: true,
        gyroControls: false,
        minHeight: 200.00,
        minWidth: 200.00,
        scale: 1.00,
        scaleMobile: 1.00,
        color: 0xfacc15,
        backgroundColor: 0x050505,
        points: 12.00,
        maxDistance: 22.00,
        spacing: 16.00,
        showDots: true
      });
    }
    return () => {
      if (vantaEffect) vantaEffect.destroy();
    };
  }, []);

  const abortControllerRef = useRef<AbortController | null>(null);
  const toasterId = useId("toaster");
  const { dispatchToast } = useToastController(toasterId);

  const { instance, accounts } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  const isIdle = !isLoading && !result && liveLogs.length === 0;

  // Auto-resize textarea
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [prompt]);

  const handleExecute = async () => {
    if (!prompt.trim()) {
      setIsInputEmptyError(true);
      setTimeout(() => setIsInputEmptyError(false), 600);
      return;
    }
    
    setIsLoading(true);
    setResult(null);
    setLiveLogs([]);

    abortControllerRef.current = new AbortController();

    let token = undefined;
    if (isAuthenticated && accounts.length > 0) {
      try {
        const tokenResponse = await instance.acquireTokenSilent({
          ...loginRequest,
          account: accounts[0]
        });
        token = tokenResponse.accessToken;
      } catch (e) {
        console.warn("Silent token acquisition failed. Using mock mode.", e);
      }
    }

    try {
      await executeSwarmStream(prompt, token, (event) => {
        if (event.type === 'log') {
          setLiveLogs((prev: any[]) => [...prev, { agent: event.agent, status: event.status || event.message }]);
        } else if (event.type === 'result') {
          setResult(event.data);
          setIsLoading(false);
        } else if (event.type === 'error') {
          dispatchToast(
            <Toast><ToastTitle>Execution Failed</ToastTitle><ToastBody>{event.message}</ToastBody></Toast>,
            { intent: "error" }
          );
          setIsLoading(false);
        }
      }, abortControllerRef.current.signal);
    } catch (err: any) {
      if (err.name === 'AbortError') {
        dispatchToast(
          <Toast><ToastTitle>Execution Stopped</ToastTitle><ToastBody>Swarm execution was manually aborted.</ToastBody></Toast>,
          { intent: "warning" }
        );
      } else {
        dispatchToast(
          <Toast><ToastTitle>Connection Failed</ToastTitle><ToastBody>{err.message || 'Failed to connect to the Agent Swarm.'}</ToastBody></Toast>,
          { intent: "error" }
        );
      }
      setIsLoading(false);
    } finally {
      abortControllerRef.current = null;
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  return (
    <>
      {/* True 3D WebGL Background */}
      <div ref={vantaRef} className="vanta-bg-container"></div>

      <Toaster toasterId={toasterId} />
      
      {/* Top Right Auth */}
      <div className="auth-container">
        {isAuthenticated ? (
          <Button appearance="subtle" onClick={() => instance.logoutPopup()} aria-label="Sign out">Sign Out ({accounts[0]?.name})</Button>
        ) : (
          <Button appearance="subtle" onClick={() => instance.loginPopup(loginRequest).catch(e => console.error(e))} aria-label="Sign in">Sign In</Button>
        )}
      </div>

      <div className={`app-container ${isIdle ? 'state-idle' : 'state-active'}`}>
        
        {/* Brand Header */}
        <div className="header-minimal">
          <Bot24Regular className="logo-icon-minimal" />
          <Title1 as="h1" className="brand-title">SARAA</Title1>
        </div>
        
        {isIdle && (
          <Text className="brand-subtitle">Strategic Autonomous Research & Action Agent</Text>
        )}

        {/* Input Bar */}
        <div className="input-section">
          <div 
            className={`search-bar ${isInputEmptyError ? 'error-shake' : ''}`}
            ref={searchBarRef}
            onMouseMove={handleMouseMove}
          >
            <textarea 
              ref={textareaRef}
              placeholder="Deploy the swarm..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={isLoading}
              className="search-textarea"
              rows={1}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleExecute();
                }
              }}
            />
            <div className="search-actions">
              <Button
                appearance="transparent"
                icon={isListening ? <MicOff24Regular /> : <Mic24Regular />}
                onClick={toggleListen}
                className={`mic-button ${isListening ? 'listening' : ''}`}
                title={speechError || "Voice Dictation"}
                aria-label="Voice Dictation"
              />
              {isLoading ? (
                <Button appearance="subtle" icon={<Stop24Regular />} onClick={handleStop} aria-label="Stop Execution" className="action-btn stop-btn" />
              ) : (
                <Button appearance="subtle" icon={<Send24Regular />} onClick={handleExecute} aria-label="Execute Swarm" className="action-btn send-btn" />
              )}
            </div>
          </div>
        </div>

        {/* Orchestration Pipeline (Logs) */}
        {!isIdle && !result && (
          <div className="pipeline-card fade-in">
            <div className="pipeline-container">
              {liveLogs.map((log: any, index: number) => (
                <div key={index} className="pipeline-step fade-in-up">
                  <div className="step-icon" style={{ color: getAgentColor(log.agent), borderColor: getAgentColor(log.agent) }}>
                    {getAgentIcon(log.agent)}
                  </div>
                  <div className="step-content">
                    <span className="step-agent" style={{ color: getAgentColor(log.agent) }}>{log.agent}</span>
                    <span className="step-status">{log.status}</span>
                  </div>
                </div>
              ))}
              
              <div className="pipeline-step active-step fade-in-up">
                <div className="step-icon pulsing-icon" style={{ color: '#FACC15', borderColor: '#FACC15' }}>
                  <Bot24Regular />
                </div>
                <div className="step-content">
                  <span className="step-agent" style={{ color: '#FACC15' }}>{liveLogs.length > 0 ? liveLogs[liveLogs.length - 1].agent : 'Orchestrator'} is working</span>
                  <span className="dots"><span>.</span><span>.</span><span>.</span></span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Final Results (Notion Style) */}
        {result && (
          <div className="results-document doc-entrance">
            <div className="doc-header">
              <Text className="doc-meta">Status: Complete • {result.execution_log.length} steps executed</Text>
            </div>
            
            <div className="markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.final_summary}</ReactMarkdown>
            </div>

            {result.results?.briefing && (
              <div className="markdown-body briefing-section">
                <hr className="doc-divider" />
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.results.briefing.briefing_markdown}</ReactMarkdown>
              </div>
            )}
            {result.results?.writer && result.results.writer.draft_document && (
              <div className="markdown-body writer-section">
                <hr className="doc-divider" />
                <h2>Draft {result.results.writer.document_type || "Document"}</h2>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.results.writer.draft_document}</ReactMarkdown>
              </div>
            )}
          </div>
        )}

      </div>
    </>
  );
}

function App() {
  return (
    <FluentProvider theme={webDarkTheme}>
      <AppContent />
    </FluentProvider>
  );
}

export default App;