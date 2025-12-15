import React, { useState, useEffect, useRef, useCallback } from 'react';
import { PublicClientApplication, InteractionRequiredAuthError } from '@azure/msal-browser';
import {
  Box,
  Container,
  Paper,
  TextField,
  IconButton,
  Button,
  Typography,
  Drawer,
  AppBar,
  Toolbar,
  Divider,
  Chip,
  Card,
  CardContent,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  ThemeProvider,
  createTheme,
  CssBaseline,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  Snackbar,
} from '@mui/material';
import {
  Send as SendIcon,
  Psychology as BrainIcon,
  CheckCircle as CheckIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Add as AddIcon,
  EmojiObjects as IdeaIcon,
  Assignment as PlanIcon,
  TrendingUp as ProgressIcon,
  CheckCircleOutline as ResultIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import { v4 as uuidv4 } from 'uuid';

const resolveBackendUrl = () => {
  if (process.env.REACT_APP_BACKEND_URL) {
    return process.env.REACT_APP_BACKEND_URL;
  }
  if (typeof window !== 'undefined') {
    if (window.location.hostname === 'localhost') {
      return 'http://localhost:7000';
    }
    return window.location.origin;
  }
  return 'http://localhost:7000';
};

const BACKEND_URL = resolveBackendUrl();
const WS_URL = BACKEND_URL.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/chat';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
  },
});

function App() {
  const [sessionId, setSessionId] = useState(() => uuidv4());
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [showInternalProcess, setShowInternalProcess] = useState(true);
  const [orchestratorEvents, setOrchestratorEvents] = useState([]);
  const [agentEvents, setAgentEvents] = useState({});
  const [currentAgents, setCurrentAgents] = useState(new Set());
  const [currentTurn, setCurrentTurn] = useState(0); // Track conversation turn for tool call grouping
  const [, setLastFinalAnswer] = useState(null); // Track last final answer for deduplication

  const [authConfig, setAuthConfig] = useState({ authEnabled: false });
  const [authConfigLoaded, setAuthConfigLoaded] = useState(false);
  const [msalApp, setMsalApp] = useState(null);
  const [account, setAccount] = useState(null);
  const [accessToken, setAccessToken] = useState(null);

  // Agent selection state
  const [availableAgents, setAvailableAgents] = useState([]);
  const [currentAgent, setCurrentAgent] = useState('');
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const processEndRef = useRef(null);
  const authPromptedRef = useRef(false);

  const isAuthEnabled = authConfig.authEnabled;
  const isSignedIn = !!accessToken;
  const canInteract = !isAuthEnabled || (isSignedIn && authConfigLoaded);
  const shouldBlockUi = isAuthEnabled && authConfigLoaded && !isSignedIn;
  const inputPlaceholder = canInteract ? 'Type your message...' : 'Sign in to chat…';
// Memoized to prevent unnecessary re-creation when used in effects
  const buildAuthHeaders = useCallback(() => (accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),[accessToken]);

  const acquireAccessToken = async (instance, activeAccount, scope) => {
    if (!instance || !activeAccount || !scope) {
      return null;
    }
    try {
      const result = await instance.acquireTokenSilent({
        scopes: [scope],
        account: activeAccount,
      });
      return result.accessToken;
    } catch (error) {
      if (error instanceof InteractionRequiredAuthError) {
        const interactiveResult = await instance.acquireTokenPopup({
          scopes: [scope],
          account: activeAccount,
        });
        return interactiveResult.accessToken;
      }
      throw error;
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const scrollProcessToBottom = () => {
    processEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);
  useEffect(scrollProcessToBottom, [orchestratorEvents, agentEvents]);

  useEffect(() => {
    const loadAuthConfig = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/auth/config`);
        const data = await response.json();
        setAuthConfig(data);

        if (data.authEnabled && data.clientId && data.authority) {
          const instance = new PublicClientApplication({
            auth: {
              clientId: data.clientId,
              authority: data.authority,
              redirectUri: window.location.origin,
            },
            cache: {
              cacheLocation: 'sessionStorage',
              storeAuthStateInCookie: false,
            },
          });
          await instance.initialize();
          setMsalApp(instance);
          const existingAccount = instance.getActiveAccount() || instance.getAllAccounts()[0];
          if (existingAccount) {
            instance.setActiveAccount(existingAccount);
            setAccount(existingAccount);
            const token = await acquireAccessToken(instance, existingAccount, data.scope);
            if (token) {
              setAccessToken(token);
            }
          }
        }
      } catch (error) {
        console.error('Error loading auth config:', error);
        setSnackbar({
          open: true,
          message: 'Failed to load auth configuration',
          severity: 'error',
        });
      } finally {
        setAuthConfigLoaded(true);
      }
    };

    loadAuthConfig();
  }, []);

  useEffect(() => {
    const attemptInteractiveLogin = async () => {
      if (!msalApp || !authConfig.scope) {
        return;
      }
      const existingAccount = msalApp.getActiveAccount() || msalApp.getAllAccounts()[0];
      if (existingAccount) {
        msalApp.setActiveAccount(existingAccount);
        setAccount(existingAccount);
        const token = await acquireAccessToken(msalApp, existingAccount, authConfig.scope);
        if (token) {
          setAccessToken(token);
        }
        return;
      }

      if (authPromptedRef.current) {
        return;
      }
      authPromptedRef.current = true;
      try {
        const response = await msalApp.loginPopup({
          scopes: [authConfig.scope],
          prompt: 'select_account',
        });
        msalApp.setActiveAccount(response.account);
        setAccount(response.account);
        const token = response.accessToken || (await acquireAccessToken(msalApp, response.account, authConfig.scope));
        if (token) {
          setAccessToken(token);
        }
      } catch (error) {
        console.error('Automatic sign-in failed:', error);
        setSnackbar({
          open: true,
          message: 'Sign-in required to continue',
          severity: 'warning',
        });
        authPromptedRef.current = false;
      }
    };

    if (authConfigLoaded && authConfig.authEnabled && !accessToken) {
      attemptInteractiveLogin();
    }
  }, [authConfigLoaded, authConfig, msalApp, accessToken]);

  // Fetch available agents on component mount
  useEffect(() => {
    const fetchAgents = async () => {
      if (!authConfigLoaded) {
        return;
      }
      if (isAuthEnabled && !accessToken) {
        return;
      }
      try {
        const response = await fetch(`${BACKEND_URL}/agents`, {
          headers: {
            ...buildAuthHeaders(),
          },
        });

        if (!response.ok) {
          throw new Error(`Status ${response.status}`);
        }

        const data = await response.json();
        const agents = Array.isArray(data.agents) ? data.agents : [];
        setAvailableAgents(agents);
        setCurrentAgent(data.current_agent ?? (agents[0]?.module_path || ''));
      } catch (error) {
        console.error('Error fetching agents:', error);
        setSnackbar({
          open: true,
          message: 'Failed to load available agents',
          severity: 'error',
        });
      }
    };
    fetchAgents();
  }, [authConfigLoaded, isAuthEnabled, accessToken, buildAuthHeaders]);

// Memoized to ensure stable reference for useEffect dependencies
const handleWebSocketMessage = useCallback((event) => {
    const { type } = event;

    switch (type) {
      case 'orchestrator':
        // Add orchestrator event with deduplication (check last event content)
        setOrchestratorEvents((prev) => {
          const lastEvent = prev[prev.length - 1];
          // Skip if same kind and same content as last event
          if (lastEvent && lastEvent.kind === event.kind && lastEvent.content === event.content) {
            return prev;
          }
          return [...prev, event];
        });
        break;

      case 'agent_start':
        setCurrentAgents((prev) => new Set([...prev, event.agent_id]));
        setAgentEvents((prev) => {
          // Don't recreate if already exists
          if (prev[event.agent_id]) {
            return prev;
          }
          return {
            ...prev,
            [event.agent_id]: {
              name: event.agent_id.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
              tokens: [],
              complete: false,
              // Convention: store agent's display preference (default true for backward compatibility)
              showMessageInInternalProcess: event.show_message_in_internal_process !== false,
            },
          };
        });
        break;

      case 'agent_token':
        setAgentEvents((prev) => ({
          ...prev,
          [event.agent_id]: {
            ...prev[event.agent_id],
            tokens: [...(prev[event.agent_id]?.tokens || []), event.content],
          },
        }));
        break;

      case 'agent_message':
        setCurrentAgents((prev) => {
          const newSet = new Set(prev);
          newSet.delete(event.agent_id);
          return newSet;
        });
        setAgentEvents((prev) => {
          // Don't update if already marked complete with same message
          const existing = prev[event.agent_id];
          if (existing?.complete && existing.finalMessage === event.content) {
            return prev;
          }
          return {
            ...prev,
            [event.agent_id]: {
              ...existing,
              finalMessage: event.content,
              complete: true,
            },
          };
        });
        break;

      case 'tool_called':
        // Tool was called by an agent - track it under that agent with turn number
        setAgentEvents((prev) => {
          const agentId = event.agent_id || 'single_agent';
          const existing = prev[agentId] || { name: agentId, tokens: [], toolCallsByTurn: {} };
          
          // Group tools by turn number - use turn from event if available, otherwise use frontend's currentTurn
          const turnNumber = event.turn !== undefined ? event.turn : currentTurn;
          const toolCallsByTurn = existing.toolCallsByTurn || {};
          const turnTools = toolCallsByTurn[turnNumber] || [];
          
          // Add tool to current turn if not already there
          if (!turnTools.includes(event.tool_name)) {
            turnTools.push(event.tool_name);
            toolCallsByTurn[turnNumber] = turnTools;
          }
          
          return {
            ...prev,
            [agentId]: {
              ...existing,
              toolCallsByTurn,
            },
          };
        });
        break;

      case 'final_result':
        // Final answer from the workflow - check for duplicates against last message
        if (event.content) {
          setMessages((prev) => {
            // Check if last message is identical
            const lastMsg = prev[prev.length - 1];
            if (lastMsg && lastMsg.role === 'assistant' && lastMsg.content === event.content) {
              console.log('[DEDUP] Skipping duplicate final_result');
              return prev;
            }
            return [
              ...prev,
              {
                role: 'assistant',
                content: event.content,
                timestamp: new Date(),
              },
            ];
          });
          setLastFinalAnswer(event.content);
        }
        setIsProcessing(false);
        break;

      case 'message':
        // Legacy message event (for Autogen compatibility) - also check for duplicates
        if (event.content) {
          setMessages((prev) => {
            // Check if last message is identical
            const lastMsg = prev[prev.length - 1];
            if (lastMsg && lastMsg.role === 'assistant' && lastMsg.content === event.content) {
              console.log('[DEDUP] Skipping duplicate message event');
              return prev;
            }
            return [
              ...prev,
              {
                role: 'assistant',
                content: event.content,
                timestamp: new Date(),
              },
            ];
          });
          setLastFinalAnswer(event.content);
        }
        setIsProcessing(false);
        break;

      case 'done':
        setIsProcessing(false);
        break;

      case 'error':
        console.error('Backend error:', event.message);
        setMessages((prev) => [
          ...prev,
          {
            role: 'error',
            content: `Error: ${event.message}`,
            timestamp: new Date(),
          },
        ]);
        setIsProcessing(false);
        break;

      default:
        break;
    }
  },[currentTurn]);

  useEffect(() => {
    if (isAuthEnabled && !accessToken) {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }
    if (!authConfigLoaded) {
      return;
    }

    // Connect to WebSocket
    const connectWebSocket = () => {
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('WebSocket connected');
        // Register session
        ws.send(JSON.stringify({
          session_id: sessionId,
          access_token: isAuthEnabled ? accessToken : null,
        }));
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };

      wsRef.current = ws;
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [sessionId, isAuthEnabled, accessToken, authConfigLoaded, handleWebSocketMessage]);

  const handleSend = () => {
    if (!input.trim() || !wsRef.current || isProcessing) return;
    if (isAuthEnabled && !accessToken) {
      setSnackbar({ open: true, message: 'Sign in to chat', severity: 'warning' });
      return;
    }

    // Increment turn for this new request
    setCurrentTurn((prev) => prev + 1);

    // Add user message
    setMessages((prev) => [
      ...prev,
      {
        role: 'user',
        content: input,
        timestamp: new Date(),
      },
    ]);

    // NOTE: Do NOT clear orchestratorEvents/agentEvents here - they should accumulate
    // across multiple turns. Only clear on new session or explicit reset.
    // Just reset the last answer deduplication tracking.
    setLastFinalAnswer(null);

    // Send to backend
    wsRef.current.send(JSON.stringify({
      session_id: sessionId,
      prompt: input,
      access_token: isAuthEnabled ? accessToken : null,
    }));

    setInput('');
    setIsProcessing(true);
  };

  const handleNewSession = async () => {
    if (isAuthEnabled && !accessToken) {
      setSnackbar({ open: true, message: 'Sign in to start a session', severity: 'warning' });
      return;
    }
    // Generate new session ID
    const newSessionId = uuidv4();
    
    // Clear all state
    setMessages([]);
    setInput('');
    setIsProcessing(false);
    setOrchestratorEvents([]);
    setAgentEvents({});
    setCurrentAgents(new Set());
    setCurrentTurn(0);
    setLastFinalAnswer(null);

    // Close existing WebSocket
    if (wsRef.current) {
      wsRef.current.close();
    }

    // Call backend to reset old session (optional cleanup)
    try {
      await fetch(`${BACKEND_URL}/reset_session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...buildAuthHeaders() },
        body: JSON.stringify({ session_id: sessionId }),
      });
    } catch (error) {
      console.error('Error resetting session:', error);
    }

    // Update session ID (will trigger WebSocket reconnect via useEffect)
    setSessionId(newSessionId);
  };

  const handleSignIn = async () => {
    if (!msalApp || !authConfig.scope) {
      setSnackbar({ open: true, message: 'Auth is not ready yet', severity: 'warning' });
      return;
    }
    try {
      const response = await msalApp.loginPopup({ scopes: [authConfig.scope] });
      msalApp.setActiveAccount(response.account);
      setAccount(response.account);
      const token = response.accessToken || (await acquireAccessToken(msalApp, response.account, authConfig.scope));
      if (token) {
        setAccessToken(token);
      }
    } catch (error) {
      console.error('Sign-in failed:', error);
      setSnackbar({ open: true, message: 'Sign-in failed', severity: 'error' });
    }
  };

  const handleSignOut = async () => {
    if (!msalApp) {
      return;
    }
    try {
      await msalApp.logoutPopup({ account: msalApp.getActiveAccount() ?? undefined });
    } catch (error) {
      console.error('Sign-out failed:', error);
    } finally {
      setAccount(null);
      setAccessToken(null);
    }
  };

  const handleAgentChange = async (event) => {
    const newAgentModule = event.target.value;
    if (isAuthEnabled && !accessToken) {
      setSnackbar({ open: true, message: 'Sign in to change agents', severity: 'warning' });
      return;
    }
    
    try {
      const response = await fetch(`${BACKEND_URL}/agents/set`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...buildAuthHeaders() },
        body: JSON.stringify({ module_path: newAgentModule }),
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        setCurrentAgent(newAgentModule);
        setSnackbar({
          open: true,
          message: `Agent changed successfully to ${newAgentModule.split('.').pop().replace(/_/g, ' ')}`,
          severity: 'success',
        });
        
        // Start a new session when agent changes
        handleNewSession();
      } else {
        setSnackbar({
          open: true,
          message: `Failed to change agent: ${data.message}`,
          severity: 'error',
        });
      }
    } catch (error) {
      console.error('Error changing agent:', error);
      setSnackbar({
        open: true,
        message: 'Failed to change agent',
        severity: 'error',
      });
    }
  };

  const handleKeyPress = (e) => {
    if (!canInteract) {
      return;
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Helper: Get icon and label for orchestrator event kind
  const getOrchestratorDisplay = (kind) => {
    switch (kind) {
      case 'instruction':
        return { icon: <SendIcon fontSize="small" />, label: '📤 Instructing Agent', color: 'secondary', bgColor: '#f3e5f5' };
      case 'task_ledger':
        return { icon: <PlanIcon fontSize="small" />, label: '📋 Planning', color: 'info', bgColor: '#e3f2fd' };
      case 'user_task':
        return { icon: <IdeaIcon fontSize="small" />, label: '📝 Task Received', color: 'default', bgColor: '#f5f5f5' };
      case 'notice':
        return { icon: <ResultIcon fontSize="small" />, label: '📢 Notice', color: 'warning', bgColor: '#fff3e0' };
      // Legacy kinds from old implementation
      case 'plan':
        return { icon: <PlanIcon fontSize="small" />, label: '📋 Planning', color: 'primary', bgColor: '#e3f2fd' };
      case 'progress':
        return { icon: <ProgressIcon fontSize="small" />, label: '⚙️ Working', color: 'info', bgColor: '#e1f5fe' };
      case 'result':
        return { icon: <ResultIcon fontSize="small" />, label: '✅ Decision', color: 'success', bgColor: '#e8f5e9' };
      default:
        return { icon: <IdeaIcon fontSize="small" />, label: '💭 Thinking', color: 'default', bgColor: '#f5f5f5' };
    }
  };

  // Note: Agent Framework limitation - MagenticOrchestratorMessageEvent does not expose
  // the target agent (next_speaker) in streaming callbacks. The progress ledger's
  // next_speaker field is used internally but not passed to message_callback.
  // Without a generalizable way to determine delegation targets, we omit this display.

  // Helper: Get creative emoji for agent
  const getAgentEmoji = (agentId) => {
    if (agentId.includes('crm') || agentId.includes('billing')) return '💳';
    if (agentId.includes('product') || agentId.includes('promotion')) return '🎁';
    if (agentId.includes('security') || agentId.includes('auth')) return '🔒';
    return '🤖';
  };

  if (shouldBlockUi) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Box
          sx={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 3,
            bgcolor: 'background.default',
            p: 3,
          }}
        >
          <Paper sx={{ p: 4, maxWidth: 420, textAlign: 'center' }} elevation={6}>
            <Typography variant="h5" gutterBottom>
              Sign in to continue
            </Typography>
            <Typography color="text.secondary" sx={{ mb: 2 }}>
              This workspace requires Microsoft Entra ID authentication before showing the agents.
            </Typography>
            <LinearProgress sx={{ mb: 2 }} />
            <Button variant="contained" onClick={handleSignIn} disabled={!msalApp || !authConfig.scope}>
              Sign in with Microsoft
            </Button>
          </Paper>
          <Snackbar
            open={snackbar.open}
            autoHideDuration={4000}
            onClose={() => setSnackbar({ ...snackbar, open: false })}
            anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
          >
            <Alert
              onClose={() => setSnackbar({ ...snackbar, open: false })}
              severity={snackbar.severity}
              sx={{ width: '100%' }}
            >
              {snackbar.message}
            </Alert>
          </Snackbar>
        </Box>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', height: '100vh' }}>
        {/* Internal Process Drawer */}
        <Drawer
          variant="persistent"
          anchor="left"
          open={showInternalProcess}
          sx={{
            width: showInternalProcess ? 400 : 0,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: 400,
              boxSizing: 'border-box',
            },
          }}
        >
          <Toolbar />
          <Box sx={{ p: 2, overflow: 'auto', height: '100%' }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <BrainIcon color="primary" />
              Internal Process
            </Typography>
            <Divider sx={{ mb: 2 }} />

            {/* Orchestrator Events */}
            {orchestratorEvents.length > 0 && (
              <Accordion defaultExpanded>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <BrainIcon fontSize="small" color="primary" />
                    Orchestrator ({orchestratorEvents.length})
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {orchestratorEvents.map((event, idx) => {
                      const display = getOrchestratorDisplay(event.kind);
                      
                      return (
                        <Card key={idx} variant="outlined" sx={{ bgcolor: display.bgColor }}>
                          <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                              <Chip
                                icon={display.icon}
                                label={display.label}
                                size="small"
                                color={display.color}
                              />
                            </Box>
                            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                              {event.content}
                            </Typography>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </Box>
                </AccordionDetails>
              </Accordion>
            )}

            {/* Agent Events */}
            {Object.entries(agentEvents)
              .filter(([agentId, agentData]) => agentData.showMessageInInternalProcess !== false) // Convention: only show if agent wants it
              .map(([agentId, agentData]) => {
              const agentEmoji = getAgentEmoji(agentId);
              return (
                <Accordion key={agentId} defaultExpanded={!agentData.complete}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <span style={{ fontSize: '1.2em' }}>{agentEmoji}</span>
                      {agentData.name}
                      {currentAgents.has(agentId) && (
                        <Chip label="Working..." size="small" color="secondary" />
                      )}
                      {agentData.complete && (
                        <CheckIcon fontSize="small" color="success" />
                      )}
                    </Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    {/* Show tools called by this agent, grouped by turn */}
                    {agentData.toolCallsByTurn && Object.keys(agentData.toolCallsByTurn).length > 0 && (
                      <Box sx={{ mb: 1 }}>
                        {Object.entries(agentData.toolCallsByTurn)
                          .sort(([turnA], [turnB]) => Number(turnA) - Number(turnB))
                          .map(([turn, tools]) => (
                            <Box key={turn} sx={{ mb: 0.5 }}>
                              <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 0.5 }}>
                                Turn {turn}:
                              </Typography>
                              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', ml: 1 }}>
                                {tools.map((tool, idx) => (
                                  <Chip
                                    key={idx}
                                    label={`🔧 ${tool}`}
                                    size="small"
                                    variant="outlined"
                                    color="info"
                                  />
                                ))}
                              </Box>
                            </Box>
                          ))}
                      </Box>
                    )}
                    <Card variant="outlined" sx={{ bgcolor: '#fff3e0' }}>
                      <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                          {agentData.finalMessage || agentData.tokens.join('')}
                        </Typography>
                      </CardContent>
                    </Card>
                  </AccordionDetails>
                </Accordion>
              );
            })}

            {/* Tool Calls for agents that don't show messages in internal process */}
            {Object.entries(agentEvents)
              .filter(([agentId, agentData]) => 
                agentData.showMessageInInternalProcess === false && 
                agentData.toolCallsByTurn && 
                Object.keys(agentData.toolCallsByTurn).length > 0
              )
              .map(([agentId, agentData]) => (
              <Accordion key={agentId} defaultExpanded>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    🔧 Tool Calls
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Box>
                    {Object.entries(agentData.toolCallsByTurn)
                      .sort(([turnA], [turnB]) => Number(turnA) - Number(turnB))
                      .map(([turn, tools]) => (
                        <Box key={turn} sx={{ mb: 1 }}>
                          <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 0.5 }}>
                            Turn {turn}:
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', ml: 1 }}>
                            {tools.map((tool, idx) => (
                              <Chip
                                key={idx}
                                label={`🔧 ${tool}`}
                                size="small"
                                variant="outlined"
                                color="info"
                              />
                            ))}
                          </Box>
                        </Box>
                      ))}
                  </Box>
                </AccordionDetails>
              </Accordion>
            ))}

            <div ref={processEndRef} />
          </Box>
        </Drawer>

        {/* Main Chat Area */}
        <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          {/* App Bar */}
          <AppBar position="static">
            <Toolbar>
              <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                🤖 Magentic AI Assistant
              </Typography>

              {isAuthEnabled && (
                isSignedIn ? (
                  <Button color="inherit" onClick={handleSignOut} sx={{ mr: 2 }}>
                    Sign out {account?.username ? `(${account.username})` : ''}
                  </Button>
                ) : (
                  <Button color="inherit" onClick={handleSignIn} disabled={!authConfigLoaded} sx={{ mr: 2 }}>
                    Sign in
                  </Button>
                )
              )}
              
              {/* Agent Selector */}
              <FormControl sx={{ minWidth: 250, mr: 2 }} size="small">
                <InputLabel id="agent-select-label" sx={{ color: 'white' }}>
                  Active Agent
                </InputLabel>
                <Select
                  labelId="agent-select-label"
                  value={currentAgent}
                  label="Active Agent"
                  onChange={handleAgentChange}
                  disabled={isProcessing || !canInteract}
                  sx={{
                    color: 'white',
                    '.MuiOutlinedInput-notchedOutline': {
                      borderColor: 'rgba(255, 255, 255, 0.3)',
                    },
                    '&:hover .MuiOutlinedInput-notchedOutline': {
                      borderColor: 'rgba(255, 255, 255, 0.5)',
                    },
                    '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                      borderColor: 'white',
                    },
                    '.MuiSvgIcon-root': {
                      color: 'white',
                    },
                  }}
                >
                  {(Array.isArray(availableAgents) ? availableAgents : []).map((agent) => (
                    <MenuItem key={agent.module_path} value={agent.module_path}>
                      <Box>
                        <Typography variant="body2">{agent.display_name}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {agent.description}
                        </Typography>
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              <Button
                color="inherit"
                onClick={handleNewSession}
                startIcon={<AddIcon />}
                sx={{ mr: 2 }}
                disabled={!canInteract}
              >
                New Session
              </Button>
              <IconButton
                color="inherit"
                onClick={() => setShowInternalProcess(!showInternalProcess)}
              >
                {showInternalProcess ? <VisibilityOffIcon /> : <VisibilityIcon />}
              </IconButton>
            </Toolbar>
          </AppBar>

          {isProcessing && <LinearProgress />}

          {/* Messages */}
          <Box
            sx={{
              flexGrow: 1,
              overflow: 'auto',
              p: 3,
              bgcolor: 'background.default',
            }}
          >
            <Container maxWidth="md">
              {messages.length === 0 && (
                <Paper sx={{ p: 4, textAlign: 'center', bgcolor: 'background.paper' }}>
                  <Typography variant="h5" gutterBottom>
                    Welcome! 👋
                  </Typography>
                  <Typography color="text.secondary">
                    I'm a multi-agent AI assistant. Ask me about customer accounts, billing, promotions, or security.
                  </Typography>
                </Paper>
              )}

              {messages.map((msg, idx) => (
                <Paper
                  key={idx}
                  sx={{
                    p: 2,
                    mb: 2,
                    bgcolor: msg.role === 'user' ? '#e3f2fd' : msg.role === 'error' ? '#ffebee' : 'background.paper',
                  }}
                >
                  <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                    {msg.role === 'user' ? 'You' : msg.role === 'error' ? 'Error' : 'Assistant'} •{' '}
                    {msg.timestamp.toLocaleTimeString()}
                  </Typography>
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </Paper>
              ))}

              <div ref={messagesEndRef} />
            </Container>
          </Box>

          {/* Input Area */}
          <Paper
            sx={{
              p: 2,
              borderTop: 1,
              borderColor: 'divider',
            }}
          >
            <Container maxWidth="md">
              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  fullWidth
                  multiline
                  maxRows={4}
                  placeholder={inputPlaceholder}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  disabled={isProcessing || !canInteract}
                />
                <IconButton
                  color="primary"
                  onClick={handleSend}
                  disabled={!input.trim() || isProcessing || !canInteract}
                  sx={{ alignSelf: 'flex-end' }}
                >
                  <SendIcon />
                </IconButton>
              </Box>
            </Container>
          </Paper>
        </Box>
        
        {/* Snackbar for notifications */}
        <Snackbar
          open={snackbar.open}
          autoHideDuration={4000}
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert
            onClose={() => setSnackbar({ ...snackbar, open: false })}
            severity={snackbar.severity}
            sx={{ width: '100%' }}
          >
            {snackbar.message}
          </Alert>
        </Snackbar>
      </Box>
    </ThemeProvider>
  );
}

export default App;
