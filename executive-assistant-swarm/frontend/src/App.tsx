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
  MicOff24Regular,
  Image24Regular,
  Dismiss24Regular
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
  const [messages, setMessages] = useState<{role: string, content: string, results?: any}[]>([]);
  const [liveLogs, setLiveLogs] = useState<{agent: string, status: string}[]>([]);
  const [isInputEmptyError, setIsInputEmptyError] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechError, setSpeechError] = useState<string | null>(null);
  
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        dispatchToast(
          <Toast><ToastTitle>File Too Large</ToastTitle><ToastBody>Please select an image under 5MB.</ToastBody></Toast>,
          { intent: "error" }
        );
        return;
      }
      setImageFile(file);
      const url = URL.createObjectURL(file);
      setImagePreviewUrl(url);
    }
  };

  const removeImage = () => {
    setImageFile(null);
    if (imagePreviewUrl) {
      URL.revokeObjectURL(imagePreviewUrl);
      setImagePreviewUrl(null);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
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

  const isIdle = messages.length === 0 && !isLoading && liveLogs.length === 0;

  // Auto-scroll chat to bottom
  const messagesEndRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, liveLogs]);

  // Auto-resize textarea
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [prompt]);

  const handleExecute = async () => {
    if (!prompt.trim() && !imageFile) {
      setIsInputEmptyError(true);
      setTimeout(() => setIsInputEmptyError(false), 600);
      return;
    }
    
    let base64Image: string | undefined = undefined;
    if (imageFile) {
      base64Image = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64String = reader.result as string;
          resolve(base64String.split(',')[1]); // Strip data URI prefix
        };
        reader.onerror = reject;
        reader.readAsDataURL(imageFile);
      });
    }

    const userMessage = { role: 'user', content: prompt || "Analyze this image." };
    if (imageFile) {
      userMessage.content += `\n\n[Attached Image: ${imageFile.name}]`;
    }

    const currentHistory = [...messages];
    
    setMessages([...currentHistory, userMessage]);
    setPrompt('');
    removeImage(); // Clear preview after sending
    setIsLoading(true);
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
      await executeSwarmStream(userMessage.content, token, currentHistory, (event) => {
        if (event.type === 'log') {
          setLiveLogs((prev: any[]) => [...prev, { agent: event.agent, status: event.status || event.message }]);
        } else if (event.type === 'result') {
          setMessages(prev => [...prev, { 
            role: 'assistant', 
            content: event.data.final_summary, 
            results: event.data 
          }]);
          setIsLoading(false);
        } else if (event.type === 'error') {
          dispatchToast(
            <Toast><ToastTitle>Execution Failed</ToastTitle><ToastBody>{event.message}</ToastBody></Toast>,
            { intent: "error" }
          );
          setIsLoading(false);
        }
      }, abortControllerRef.current.signal, base64Image);
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
      <div className="auth-container" style={{ position: 'fixed', top: 16, right: 24, zIndex: 100 }}>
        {isAuthenticated ? (
          <Button appearance="subtle" onClick={() => instance.logoutPopup()} aria-label="Sign out">Sign Out ({accounts[0]?.name})</Button>
        ) : (
          <Button appearance="subtle" onClick={() => instance.loginPopup(loginRequest).catch(e => console.error(e))} aria-label="Sign in">Sign In</Button>
        )}
      </div>

      <div className={`app-container ${isIdle ? 'state-idle' : 'state-chat'}`}>
        
        {isIdle && (
          <div className="idle-hero">
            <div className="header-minimal">
              <Bot24Regular className="logo-icon-minimal" />
              <Title1 as="h1" className="brand-title">SARAA</Title1>
            </div>
            <Text className="brand-subtitle">Strategic Autonomous Research & Action Agent</Text>
          </div>
        )}

        {/* Chat Thread */}
        {!isIdle && (
          <div className="chat-thread">
            {messages.map((msg, idx) => (
              <div key={idx} className={`message-bubble ${msg.role}`}>
                {msg.role === 'user' ? (
                  <div className="user-text">{msg.content}</div>
                ) : (
                  <div className="results-document">
                    <div className="doc-header">
                      <Text className="doc-meta">Status: Complete • {msg.results?.execution_log?.length || 0} steps executed</Text>
                    </div>
                    
                    <div className="markdown-body">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                )}
              </div>
            ))}
            
            {/* Active Loading State */}
            {isLoading && (
              <div className="message-bubble assistant">
                <div className="status-card fade-in">
                  {(() => {
                    const latestLog = liveLogs.length > 0 ? liveLogs[liveLogs.length - 1] : { agent: 'Orchestrator', status: 'Thinking...' };
                    const agentColor = getAgentColor(latestLog.agent);
                    return (
                      <div className="active-agent-container">
                        <div className="active-agent-icon pulsing-icon" style={{ color: agentColor, borderColor: agentColor }}>
                          {getAgentIcon(latestLog.agent)}
                        </div>
                        <div className="active-agent-info">
                          <span className="active-agent-name" style={{ color: agentColor }}>
                            {latestLog.agent} <span className="dots" style={{ color: agentColor }}><span>.</span><span>.</span><span>.</span></span>
                          </span>
                          <span className="active-agent-status">{latestLog.status}</span>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Input Bar Fixed to Bottom */}
        <div className={`input-section ${isIdle ? 'input-idle' : 'input-chat'}`}>
          <div className={`search-bar ${isInputEmptyError ? 'error-shake' : ''}`} ref={searchBarRef} onMouseMove={handleMouseMove}>
            {imagePreviewUrl && (
              <div className="image-preview-container" style={{ position: 'relative', marginBottom: 8, padding: 8, borderRadius: 8, background: 'rgba(255, 255, 255, 0.05)', display: 'inline-block', width: 'fit-content', zIndex: 10 }}>
                <img src={imagePreviewUrl} alt="Upload preview" style={{ height: 64, width: 'auto', borderRadius: 4 }} />
                <Button 
                  icon={<Dismiss24Regular />} 
                  appearance="subtle" 
                  onClick={removeImage} 
                  style={{ position: 'absolute', top: -8, right: -8, background: '#333', minWidth: 24, padding: 2, borderRadius: '50%' }}
                  aria-label="Remove image"
                />
              </div>
            )}
            
            <div className="search-input-row">
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
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  style={{ display: 'none' }} 
                  accept="image/*" 
                  onChange={handleImageUpload} 
                />
                <Button
                  appearance="transparent"
                  icon={<Image24Regular />}
                  onClick={() => fileInputRef.current?.click()}
                  className="action-btn image-button"
                  aria-label="Upload Image"
                  title="Upload Image"
                />
                <Button
                  appearance="transparent"
                  icon={isListening ? <MicOff24Regular /> : <Mic24Regular />}
                  onClick={toggleListen}
                  className={`action-btn mic-button ${isListening ? 'listening' : ''}`}
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
        </div>

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