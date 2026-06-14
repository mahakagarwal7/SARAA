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
  ToastBody,
  Dialog,
  DialogTrigger,
  DialogSurface,
  DialogTitle,
  DialogBody,
  DialogActions,
  DialogContent,
  Input
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
  Dismiss24Regular,
  Document24Regular,
  Print24Regular,
  Attach24Regular,
  DocumentText24Regular,
  Image24Regular,
  Info24Regular,
  Chat24Regular,
  Add24Regular,
  Navigation24Regular
} from '@fluentui/react-icons';
import { 
  executeSwarmStream,
  loginUser,
  registerUser,
  getThreads,
  getThreadMessages,
  createThread,
  forgotPassword,
  resetPassword
} from './services/api';
import type { User, Thread } from './services/api';
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
  const [loadingThreadId, setLoadingThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<{role: string, content: string, results?: any}[]>([]);
  const [liveLogsByThread, setLiveLogsByThread] = useState<Record<string, {agent: string, status: string}[]>>({});
  const [unreadCounts, setUnreadCounts] = useState<Record<string, number>>({});
  const [isInputEmptyError, setIsInputEmptyError] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechError, setSpeechError] = useState<string | null>(null);
  
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [filePreviewUrl, setFilePreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [user, setUser] = useState<User | null>(() => {
    const savedUser = localStorage.getItem('user');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const isLoading = loadingThreadId !== null && (loadingThreadId === activeThreadId || (activeThreadId === null && loadingThreadId === 'new'));
  const liveLogs = (activeThreadId ? liveLogsByThread[activeThreadId] : liveLogsByThread['new']) || [];

  const activeThreadIdRef = useRef<string | null>(null);
  useEffect(() => {
    activeThreadIdRef.current = activeThreadId;
  }, [activeThreadId]);

  const threadsRef = useRef<Thread[]>([]);
  useEffect(() => {
    threadsRef.current = threads;
  }, [threads]);

  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);
  
  const [authMode, setAuthMode] = useState<'login' | 'register' | 'forgot' | 'reset'>('login');
  const [authUsername, setAuthUsername] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authEmail, setAuthEmail] = useState('');
  const [authCode, setAuthCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSuccessMessage, setAuthSuccessMessage] = useState<string | null>(null);

  // Clear auth state on close
  useEffect(() => {
    if (!isAuthOpen) {
      setAuthUsername('');
      setAuthPassword('');
      setAuthEmail('');
      setAuthCode('');
      setNewPassword('');
      setAuthError(null);
      setAuthSuccessMessage(null);
      setAuthMode('login');
    }
  }, [isAuthOpen]);

  const vantaRef = useRef<HTMLDivElement>(null);
  const searchBarRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  // Fetch threads on load if logged in
  useEffect(() => {
    if (token) {
      loadThreads();
    }
  }, [token]);

  const loadThreads = async () => {
    if (!token) return;
    try {
      const data = await getThreads(token);
      setThreads(data);
    } catch (e) {
      console.error("Failed to load threads", e);
    }
  };

  const handleThreadSelect = async (threadId: string) => {
    setActiveThreadId(threadId);
    setMessages([]);
    setUnreadCounts(prev => ({ ...prev, [threadId]: 0 }));
    if (!token) return;
    try {
      const msgs = await getThreadMessages(threadId, token);
      const formattedMsgs = msgs.map(m => ({
        role: m.role,
        content: m.content,
        results: m.execution_log ? { execution_log: JSON.parse(m.execution_log) } : undefined
      }));
      setMessages(formattedMsgs);
    } catch (e) {
      console.error("Failed to load thread messages", e);
    }
  };

  const handleNewChat = () => {
    setActiveThreadId(null);
    setMessages([]);
    setPrompt('');
    removeFile();
  };

  const handleLogin = async () => {
    setAuthError(null);
    try {
      const res = await loginUser(authUsername, authPassword);
      setToken(res.access_token);
      setUser(res.user);
      localStorage.setItem('token', res.access_token);
      localStorage.setItem('user', JSON.stringify(res.user));
      setIsAuthOpen(false);
    } catch (e: any) {
      setAuthError(e.response?.data?.detail || "Login failed");
    }
  };

  const handleRegister = async () => {
    setAuthError(null);
    if (!authUsername || !authPassword || !authEmail) {
      setAuthError("All fields are required (Username, Email, and Password)");
      return;
    }
    try {
      const res = await registerUser(authUsername, authPassword, authEmail);
      setToken(res.access_token);
      setUser(res.user);
      localStorage.setItem('token', res.access_token);
      localStorage.setItem('user', JSON.stringify(res.user));
      setIsAuthOpen(false);
    } catch (e: any) {
      setAuthError(e.response?.data?.detail || "Registration failed");
    }
  };

  const handleForgotPassword = async () => {
    setAuthError(null);
    setAuthSuccessMessage(null);
    if (!authUsername || !authEmail) {
      setAuthError("Please provide both Username and Email");
      return;
    }
    try {
      const res = await forgotPassword(authUsername, authEmail);
      setAuthSuccessMessage(res.message);
      setAuthMode('reset');
    } catch (e: any) {
      setAuthError(e.response?.data?.detail || "Failed to initiate password reset");
    }
  };

  const handleResetPassword = async () => {
    setAuthError(null);
    setAuthSuccessMessage(null);
    if (!authUsername || !authCode || !newPassword) {
      setAuthError("Please provide Username, Code, and New Password");
      return;
    }
    try {
      const res = await resetPassword(authUsername, authCode, newPassword);
      dispatchToast(
        <Toast><ToastTitle>Success</ToastTitle><ToastBody>{res.message}</ToastBody></Toast>,
        { intent: "success" }
      );
      setAuthSuccessMessage(res.message);
      setAuthMode('login');
      setAuthCode('');
      setNewPassword('');
    } catch (e: any) {
      setAuthError(e.response?.data?.detail || "Failed to reset password");
    }
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setThreads([]);
    handleNewChat();
  };

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

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        dispatchToast(
          <Toast><ToastTitle>File Too Large</ToastTitle><ToastBody>Please select a file under 5MB.</ToastBody></Toast>,
          { intent: "error" }
        );
        return;
      }
      setAttachedFile(file);
      if (file.type.startsWith('image/')) {
        const url = URL.createObjectURL(file);
        setFilePreviewUrl(url);
      } else {
        setFilePreviewUrl(null); // No image preview for docs
      }
    }
  };

  const removeFile = () => {
    setAttachedFile(null);
    if (filePreviewUrl) {
      URL.revokeObjectURL(filePreviewUrl);
      setFilePreviewUrl(null);
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
    if (!prompt.trim() && !attachedFile) {
      setIsInputEmptyError(true);
      setTimeout(() => setIsInputEmptyError(false), 600);
      return;
    }
    
    let base64Image: string | undefined = undefined;
    let base64File: string | undefined = undefined;
    let fileName: string | undefined = undefined;
    
    if (attachedFile) {
      const isImage = attachedFile.type.startsWith('image/');
      const base64String = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
          const b64 = reader.result as string;
          resolve(b64.split(',')[1]); // Strip data URI prefix
        };
        reader.onerror = reject;
        reader.readAsDataURL(attachedFile);
      });
      
      if (isImage) {
        base64Image = base64String;
      } else {
        base64File = base64String;
        fileName = attachedFile.name;
      }
    }

    const userMessage = { role: 'user', content: prompt || "Analyze this file." };
    if (attachedFile) {
      userMessage.content += `\n\n[Attached File: ${attachedFile.name}]`;
    }

    const currentHistory = [...messages];
    
    setMessages([...currentHistory, userMessage]);
    setPrompt('');
    removeFile(); // Clear preview after sending
    
    let currentThreadId = activeThreadId;
    const tempKey = currentThreadId || 'new';
    
    setLoadingThreadId(tempKey);
    setLiveLogsByThread(prev => ({ ...prev, [tempKey]: [] }));

    abortControllerRef.current = new AbortController();

    try {
      if (!currentThreadId && token) {
        // Create new thread
        const newThreadTitle = userMessage.content.slice(0, 30) + "...";
        const newThread = await createThread(newThreadTitle, token);
        currentThreadId = newThread.id;
        
        // Move logs from 'new' to newThread.id, update loadingThreadId
        setLiveLogsByThread(prev => {
          const next = { ...prev };
          if (next['new']) {
            next[currentThreadId!] = next['new'];
            delete next['new'];
          }
          return next;
        });
        
        setLoadingThreadId(currentThreadId);
        setActiveThreadId(currentThreadId);
        loadThreads(); // Refresh thread list
      }

      const targetThreadId = currentThreadId;

      await executeSwarmStream(userMessage.content, token || undefined, targetThreadId || undefined, currentHistory, (event) => {
        const isCurrentActive = activeThreadIdRef.current === targetThreadId;

        if (event.type === 'log') {
          const logKey = targetThreadId || 'new';
          setLiveLogsByThread(prev => ({
            ...prev,
            [logKey]: [...(prev[logKey] || []), { agent: event.agent, status: event.status || event.message }]
          }));
        } else if (event.type === 'result') {
          if (isCurrentActive) {
            setMessages(prev => [...prev, { 
              role: 'assistant', 
              content: event.data.final_summary, 
              results: event.data 
            }]);
          } else {
            if (targetThreadId) {
              setUnreadCounts(prev => ({
                ...prev,
                [targetThreadId]: (prev[targetThreadId] || 0) + 1
              }));
            }
            loadThreads();
          }
          setLoadingThreadId(null);

          // Notifications
          const threadTitle = threadsRef.current.find(t => t.id === targetThreadId)?.title || "Swarm Chat";
          
          if (!document.hasFocus() && 'Notification' in window && Notification.permission === 'granted') {
            new Notification("Search Complete", {
              body: isCurrentActive 
                ? "The swarm has finished compiling your report."
                : `The swarm finished research in "${threadTitle}"`,
              icon: "/favicon.svg"
            });
          }
          
          dispatchToast(
            <Toast>
              <ToastTitle>Search Complete</ToastTitle>
              <ToastBody>
                {isCurrentActive 
                  ? "The swarm has finished compiling your report." 
                  : `The swarm finished research in "${threadTitle}"`}
              </ToastBody>
            </Toast>,
            { intent: "success" }
          );

        } else if (event.type === 'error') {
          if (isCurrentActive) {
            dispatchToast(
              <Toast><ToastTitle>Execution Failed</ToastTitle><ToastBody>{event.message}</ToastBody></Toast>,
              { intent: "error" }
            );
          } else {
            const threadTitle = threadsRef.current.find(t => t.id === targetThreadId)?.title || "Swarm Chat";
            dispatchToast(
              <Toast><ToastTitle>Swarm Error</ToastTitle><ToastBody>Failed in "${threadTitle}": {event.message}</ToastBody></Toast>,
              { intent: "error" }
            );
          }
          setLoadingThreadId(null);
        }
      }, abortControllerRef.current.signal, base64Image, fileName, base64File);
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
      setLoadingThreadId(null);
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
      
      {/* Sidebar for Threads */}
      <div className="sidebar" style={{
        position: 'fixed', top: 0, left: isSidebarOpen ? 0 : -260, bottom: 0, width: 260, 
        backgroundColor: 'rgba(20,20,20,0.85)', backdropFilter: 'blur(10px)', 
        borderRight: '1px solid rgba(255,255,255,0.1)', zIndex: 90, 
        display: 'flex', flexDirection: 'column', padding: 16, boxSizing: 'border-box',
        transition: 'left 0.3s cubic-bezier(0.16, 1, 0.3, 1)'
      }}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          <Button 
            appearance="transparent" 
            icon={<Dismiss24Regular />} 
            onClick={() => setIsSidebarOpen(false)}
            style={{ minWidth: 40, padding: 0 }}
            aria-label="Close Sidebar"
          />
          <Button 
            icon={<Add24Regular />} 
            className="sidebar-btn-new"
            onClick={handleNewChat}
            style={{ flex: 1, justifyContent: 'flex-start', paddingLeft: 12, borderRadius: 8 }}
          >
            New Chat
          </Button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {threads.map(t => (
            <Button 
              key={t.id} 
              icon={<Chat24Regular />} 
              appearance={activeThreadId === t.id ? undefined : "subtle"} 
              className={activeThreadId === t.id ? "sidebar-btn-active" : undefined}
              onClick={() => handleThreadSelect(t.id)}
              style={{ width: '100%', justifyContent: 'flex-start', marginBottom: 4, paddingLeft: 12, borderRadius: 8, textAlign: 'left', display: 'flex', alignItems: 'center' }}
            >
              <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.title}</span>
              {unreadCounts[t.id] > 0 && (
                <span className="unread-badge" style={{
                  backgroundColor: '#facc15',
                  color: '#050505',
                  borderRadius: '10px',
                  padding: '2px 6px',
                  fontSize: '11px',
                  fontWeight: 'bold',
                  marginLeft: 8,
                  flexShrink: 0
                }}>
                  {unreadCounts[t.id]}
                </span>
              )}
            </Button>
          ))}
        </div>
      </div>

      {/* Open Sidebar Button (when sidebar is closed) */}
      {!isSidebarOpen && (
        <div style={{ position: 'fixed', top: 16, left: 16, zIndex: 100 }}>
          <Button 
            appearance="subtle" 
            icon={<Navigation24Regular />} 
            onClick={() => setIsSidebarOpen(true)}
            aria-label="Open Sidebar"
          />
        </div>
      )}

      {/* Top Right Auth */}
      <div className="auth-container" style={{ position: 'fixed', top: 16, right: 24, zIndex: 100 }}>
        {user ? (
          <Button appearance="subtle" onClick={handleLogout} aria-label="Sign out">Sign Out ({user.username})</Button>
        ) : (
          <Dialog open={isAuthOpen} onOpenChange={(_, data) => setIsAuthOpen(data.open)}>
            <DialogTrigger disableButtonEnhancement>
              <Button appearance="subtle">Sign In</Button>
            </DialogTrigger>
            <DialogSurface className="glass-dialog">
              <DialogBody>
                <DialogTitle>
                  {authMode === 'login' ? 'Sign In' : 
                   authMode === 'register' ? 'Sign Up' : 
                   authMode === 'forgot' ? 'Forgot Password' : 'Reset Password'}
                </DialogTitle>
                <DialogContent style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 16 }}>
                  {authError && <Text style={{ color: '#ef4444' }}>{authError}</Text>}
                  {authSuccessMessage && <Text style={{ color: '#10b981' }}>{authSuccessMessage}</Text>}
                  
                  <Input 
                    placeholder="Username" 
                    value={authUsername} 
                    onChange={e => setAuthUsername(e.target.value)} 
                    disabled={authMode === 'reset'}
                  />
                  
                  {(authMode === 'register' || authMode === 'forgot') && (
                    <Input 
                      type="email"
                      placeholder="Email" 
                      value={authEmail} 
                      onChange={e => setAuthEmail(e.target.value)} 
                    />
                  )}
                  
                  {(authMode === 'login' || authMode === 'register') && (
                    <Input 
                      type="password" 
                      placeholder="Password" 
                      value={authPassword} 
                      onChange={e => setAuthPassword(e.target.value)} 
                      onKeyDown={e => e.key === 'Enter' && (authMode === 'login' ? handleLogin() : handleRegister())}
                    />
                  )}
                  
                  {authMode === 'reset' && (
                    <Input 
                      placeholder="Verification Code" 
                      value={authCode} 
                      onChange={e => setAuthCode(e.target.value)} 
                    />
                  )}
                  
                  {authMode === 'reset' && (
                    <Input 
                      type="password" 
                      placeholder="New Password" 
                      value={newPassword} 
                      onChange={e => setNewPassword(e.target.value)} 
                      onKeyDown={e => e.key === 'Enter' && handleResetPassword()}
                    />
                  )}
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-start' }}>
                    {authMode === 'login' && (
                      <>
                        <Button 
                          appearance="transparent" 
                          style={{ padding: 0, height: 'auto', minWidth: 'auto' }}
                          onClick={() => { setAuthMode('register'); setAuthError(null); setAuthSuccessMessage(null); }}
                        >
                          Don't have an account? Sign Up
                        </Button>
                        <Button 
                          appearance="transparent" 
                          style={{ padding: 0, height: 'auto', minWidth: 'auto', color: '#facc15' }}
                          onClick={() => { setAuthMode('forgot'); setAuthError(null); setAuthSuccessMessage(null); }}
                        >
                          Forgot Password?
                        </Button>
                      </>
                    )}
                    
                    {authMode === 'register' && (
                      <Button 
                        appearance="transparent" 
                        style={{ padding: 0, height: 'auto', minWidth: 'auto' }}
                        onClick={() => { setAuthMode('login'); setAuthError(null); setAuthSuccessMessage(null); }}
                      >
                        Already have an account? Sign In
                      </Button>
                    )}
                    
                    {(authMode === 'forgot' || authMode === 'reset') && (
                      <Button 
                        appearance="transparent" 
                        style={{ padding: 0, height: 'auto', minWidth: 'auto' }}
                        onClick={() => { setAuthMode('login'); setAuthError(null); setAuthSuccessMessage(null); }}
                      >
                        Back to Sign In
                      </Button>
                    )}
                  </div>
                </DialogContent>
                <DialogActions style={{ marginTop: 24 }}>
                  <DialogTrigger disableButtonEnhancement>
                    <Button appearance="secondary">Cancel</Button>
                  </DialogTrigger>
                  
                  {authMode === 'login' && (
                    <Button appearance="primary" onClick={handleLogin}>Sign In</Button>
                  )}
                  {authMode === 'register' && (
                    <Button appearance="primary" onClick={handleRegister}>Sign Up</Button>
                  )}
                  {authMode === 'forgot' && (
                    <Button appearance="primary" onClick={handleForgotPassword}>Send Code</Button>
                  )}
                  {authMode === 'reset' && (
                    <Button appearance="primary" onClick={handleResetPassword}>Reset Password</Button>
                  )}
                </DialogActions>
              </DialogBody>
            </DialogSurface>
          </Dialog>
        )}
      </div>

      <div style={{ paddingLeft: isSidebarOpen ? 260 : 0, width: '100vw', boxSizing: 'border-box', transition: 'padding-left 0.3s cubic-bezier(0.16, 1, 0.3, 1)' }}>
        <div className={`app-container ${isIdle ? 'state-idle' : 'state-chat'}`}>
        
        {isIdle && (
          <div className="idle-hero">
            <div className="header-minimal">
              <Bot24Regular className="logo-icon-minimal" />
              <Title1 as="h1" className="brand-title">
                <span className="brand-letter" style={{ animationDelay: '0s' }}>S</span>
                <span className="brand-letter" style={{ animationDelay: '0.15s' }}>A</span>
                <span className="brand-letter" style={{ animationDelay: '0.3s' }}>R</span>
                <span className="brand-letter" style={{ animationDelay: '0.45s' }}>A</span>
                <span className="brand-letter" style={{ animationDelay: '0.6s' }}>A</span>
              </Title1>
            </div>
            <Text className="brand-subtitle">Strategic Autonomous Research & Action Agent</Text>
            <div style={{ marginTop: 24, marginBottom: 24, position: 'relative', zIndex: 100, animation: 'fadeIn 1s ease forwards 0.5s', opacity: 0, pointerEvents: 'auto' }}>
              <Dialog>
                <DialogTrigger disableButtonEnhancement>
                  <button className="info-pill-btn">
                    <Info24Regular style={{ marginRight: 8 }} />
                    <span>What can SARAA do?</span>
                  </button>
                </DialogTrigger>
                <DialogSurface className="glass-dialog">
                  <DialogBody>
                    <DialogTitle>Capabilities Overview</DialogTitle>
                    <DialogContent>
                      <div className="dialog-capabilities">
                        <div className="dialog-cap-item">
                          <Search24Regular className="dialog-icon text-blue" />
                          <div>
                            <strong>Deep Research & Web Browsing:</strong> SARAA utilizes a fleet of autonomous web-scraping agents to search the live internet. It reads multiple sources simultaneously, synthesizes conflicting information, and compiles comprehensive intelligence reports. It doesn't just return links; it reads the pages for you.<br/>
                            <span className="prompt-example"><em>Try: "Conduct a deep dive into the latest breakthroughs in solid-state EV batteries from 2024. Compare the top three leading companies, their manufacturing bottlenecks, and synthesize a timeline for commercial viability."</em></span>
                          </div>
                        </div>
                        <div className="dialog-cap-item">
                          <CalendarLtr24Regular className="dialog-icon text-orange" />
                          <div>
                            <strong>Calendar Sync & Meeting Prep:</strong> Securely connects via Microsoft Graph API to read your live schedule. SARAA will autonomously identify your upcoming meetings, research the attendees on the web, and generate automated briefing documents so you walk into every meeting fully prepared.<br/>
                            <span className="prompt-example"><em>Try: "Check my calendar for tomorrow. Identify any external client meetings, research their company's recent news online, and prepare a 1-page strategic briefing for me before I join the call."</em></span>
                          </div>
                        </div>
                        <div className="dialog-cap-item">
                          <DocumentText24Regular className="dialog-icon text-green" />
                          <div>
                            <strong>Advanced Document Generation:</strong> SARAA goes beyond chat text. It acts as your personal analyst, drafting fully-formatted, multi-page professional executive briefings, strategic industry reports, and highly technical summaries, which it can output as downloadable documents.<br/>
                            <span className="prompt-example"><em>Try: "Draft a comprehensive, professional executive briefing on the macroeconomic impact of AI in the finance sector. Include sections on risk management, algorithmic trading, and regulatory compliance. Format it professionally."</em></span>
                          </div>
                        </div>
                        <div className="dialog-cap-item">
                          <Image24Regular className="dialog-icon text-purple" />
                          <div>
                            <strong>Multimodal Document Analysis:</strong> Click the attachment icon to upload massive PDFs, raw data files, Word Documents, or complex images. SARAA's vision and parsing agents will instantly read, analyze, and extract deep insights, saving you hours of manual reading.<br/>
                            <span className="prompt-example"><em>Try: [Upload a 50-page financial PDF] and ask "Read this entire financial report. Extract the Q3 revenue figures, summarize the CEO's forward-looking guidance, and identify the top three risk factors mentioned."</em></span>
                          </div>
                        </div>
                      </div>
                    </DialogContent>
                    <DialogActions>
                      <DialogTrigger disableButtonEnhancement>
                        <Button appearance="secondary" style={{ borderRadius: 8 }}>Close</Button>
                      </DialogTrigger>
                    </DialogActions>
                  </DialogBody>
                </DialogSurface>
              </Dialog>
            </div>
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
                    <div className="doc-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text className="doc-meta">Status: Complete • {msg.results?.execution_log?.length || 0} steps executed</Text>
                      <Button 
                        icon={<Print24Regular />} 
                        appearance="subtle" 
                        className="print-btn"
                        onClick={() => window.print()}
                      >
                        Export PDF
                      </Button>
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
        <div className={`input-section ${isIdle ? 'input-idle' : 'input-chat'}`} style={!isIdle ? { left: isSidebarOpen ? 'calc(50vw + 130px)' : '50%', transition: 'left 0.3s cubic-bezier(0.16, 1, 0.3, 1)' } : {}}>
          <div className={`search-bar ${isInputEmptyError ? 'error-shake' : ''}`} ref={searchBarRef} onMouseMove={handleMouseMove}>
            {attachedFile && (
              <div className="image-preview-container" style={{ position: 'relative', marginBottom: 8, padding: 8, borderRadius: 8, background: 'rgba(255, 255, 255, 0.05)', display: 'flex', alignItems: 'center', width: 'fit-content', gap: 8, zIndex: 10 }}>
                {filePreviewUrl ? (
                  <img src={filePreviewUrl} alt="Upload preview" style={{ height: 64, width: 'auto', borderRadius: 4 }} />
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 12px', background: '#2d2d2d', borderRadius: 6 }}>
                    <Document24Regular style={{ color: '#3b82f6' }} />
                    <Text>{attachedFile.name}</Text>
                  </div>
                )}
                <Button 
                  icon={<Dismiss24Regular />} 
                  appearance="subtle" 
                  onClick={removeFile} 
                  style={{ background: '#333', minWidth: 24, padding: 2, borderRadius: '50%' }}
                  aria-label="Remove file"
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
                  accept="image/*,.pdf,.doc,.docx" 
                  onChange={handleFileUpload} 
                />
                <Button
                  appearance="transparent"
                  icon={<Attach24Regular />}
                  onClick={() => fileInputRef.current?.click()}
                  className="action-btn file-button"
                  aria-label="Upload File"
                  title="Attach Image or Document"
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