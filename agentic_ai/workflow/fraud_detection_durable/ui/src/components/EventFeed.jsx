import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  IconButton,
  Tooltip,
  Divider,
  Badge,
} from '@mui/material';
import PauseIcon from '@mui/icons-material/Pause';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import PowerSettingsNewIcon from '@mui/icons-material/PowerSettingsNew';
import { API_CONFIG } from '../constants/config';

const MAX_EVENTS = 80;

const EVENT_TYPE_COLORS = {
  login: '#2196f3',
  transaction: '#4caf50',
  data_usage: '#9c27b0',
  api_call: '#607d8b',
  auth_failure: '#f44336',
};

const EVENT_TYPE_LABELS = {
  login: 'LOGIN',
  transaction: 'TXN',
  data_usage: 'DATA',
  api_call: 'API',
  auth_failure: 'AUTH',
};

/**
 * Live Event Feed panel showing Layer 1 telemetry events.
 * 
 * Connects to the backend's /api/events/stream SSE endpoint.
 * Green = normal, amber/red = anomaly detected.
 * 
 * When Layer 1 auto-triggers a workflow, a "workflow_auto_started" event
 * arrives with the DTS instance_id. The user can click to connect the
 * WorkflowVisualizer to that running orchestration.
 */
export default function EventFeed({ onAnomalyDetected, onWorkflowAutoStarted }) {
  const [events, setEvents] = useState([]);
  const [paused, setPaused] = useState(false);
  const [connected, setConnected] = useState(false);
  const [anomalyCount, setAnomalyCount] = useState(0);
  const [autoStartedAlerts, setAutoStartedAlerts] = useState([]);
  const [producerRunning, setProducerRunning] = useState(false);
  const scrollRef = useRef(null);
  const pausedRef = useRef(false);
  const eventsRef = useRef([]);
  const eventSourceRef = useRef(null);

  // Keep ref in sync with state
  useEffect(() => { pausedRef.current = paused; }, [paused]);

  // Poll server-side ambient producer status so the toggle reflects reality.
  useEffect(() => {
    let cancelled = false;
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.PRODUCER_STATUS}`);
        if (res.ok) {
          const data = await res.json();
          if (!cancelled) setProducerRunning(!!data.running);
        }
      } catch {
        /* backend not ready yet — ignore */
      }
    };
    fetchStatus();
    const t = setInterval(fetchStatus, 5000);
    return () => { cancelled = true; clearInterval(t); };
  }, []);

  const toggleProducer = useCallback(async () => {
    const endpoint = producerRunning
      ? API_CONFIG.ENDPOINTS.PRODUCER_STOP
      : API_CONFIG.ENDPOINTS.PRODUCER_START;
    try {
      const res = await fetch(`${API_CONFIG.BASE_URL}${endpoint}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setProducerRunning(!!data.running);
      }
    } catch (err) {
      console.error('Failed to toggle ambient feed:', err);
    }
  }, [producerRunning]);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (!paused && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events, paused]);

  // Connect to SSE stream
  useEffect(() => {
    const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.EVENTS_STREAM}`;
    console.log('Connecting to event stream:', url);
    
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      console.log('Event stream connected');
      setConnected(true);
    };

    es.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data);

        // Handle workflow auto-started events — these carry the DTS instance_id
        if (event.event_type === 'workflow_auto_started') {
          const alertInfo = {
            instance_id: event.details?.instance_id,
            alert_id: event.details?.alert_id,
            alert_type: event.details?.alert_type,
            description: event.details?.description,
            severity: event.details?.severity,
            customer_id: event.customer_id,
            customer_name: event.customer_name,
            timestamp: event.timestamp,
          };
          setAutoStartedAlerts(prev => [alertInfo, ...prev].slice(0, 5));
          setAnomalyCount(prev => prev + 1);
          // Don't add to the normal event list — it will render as a banner
          return;
        }

        if (event.is_anomaly) {
          setAnomalyCount(prev => prev + 1);
          if (onAnomalyDetected) {
            onAnomalyDetected(event);
          }
        }

        if (!pausedRef.current) {
          eventsRef.current = [...eventsRef.current.slice(-(MAX_EVENTS - 1)), event];
          setEvents(eventsRef.current);
        }
      } catch (err) {
        console.error('Error parsing event:', err);
      }
    };

    es.onerror = () => {
      setConnected(false);
      console.warn('Event stream disconnected, will retry...');
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [onAnomalyDetected]);

  const handleClear = useCallback(() => {
    eventsRef.current = [];
    setEvents([]);
    setAnomalyCount(0);
    setAutoStartedAlerts([]);
  }, []);

  const formatTime = (ts) => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return '';
    }
  };

  const formatDetails = (event) => {
    const d = event.details || {};
    switch (event.event_type) {
      case 'login':
        return `${d.country || '?'} · ${d.ip || ''}`;
      case 'transaction':
        return `$${(d.amount || 0).toFixed(2)} · ${d.merchant || ''}`;
      case 'data_usage':
        return `${(d.gb_used || 0).toFixed(1)} GB`;
      case 'api_call':
        return `${d.endpoint || ''} · ${d.status_code || ''}`;
      case 'auth_failure':
        return `${d.reason || ''} · ${d.ip || ''}`;
      default:
        return JSON.stringify(d).slice(0, 40);
    }
  };

  return (
    <Paper elevation={2} sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <Box sx={{ px: 1.5, py: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: 1, borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Badge
            variant="dot"
            color={connected ? 'success' : 'error'}
            sx={{ '& .MuiBadge-badge': { width: 8, height: 8, borderRadius: '50%' } }}
          >
            <Typography variant="subtitle2" fontWeight={700}>Live Feed</Typography>
          </Badge>
          {anomalyCount > 0 && (
            <Chip
              icon={<WarningAmberIcon sx={{ fontSize: 14 }} />}
              label={anomalyCount}
              size="small"
              color="warning"
              sx={{ height: 20, fontSize: 11 }}
            />
          )}
        </Box>
        <Box>
          <Tooltip title={producerRunning ? 'Stop ambient feed (server)' : 'Start ambient feed (server)'}>
            <IconButton size="small" onClick={toggleProducer} color={producerRunning ? 'success' : 'default'}>
              <PowerSettingsNewIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title={paused ? 'Resume rendering' : 'Pause rendering'}>
            <IconButton size="small" onClick={() => setPaused(p => !p)}>
              {paused ? <PlayArrowIcon fontSize="small" /> : <PauseIcon fontSize="small" />}
            </IconButton>
          </Tooltip>
          <Tooltip title="Clear">
            <IconButton size="small" onClick={handleClear}>
              <DeleteSweepIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Auto-started workflow banners */}
      {autoStartedAlerts.length > 0 && (
        <Box sx={{ px: 1, py: 0.5, display: 'flex', flexDirection: 'column', gap: 0.5, borderBottom: 1, borderColor: 'divider', bgcolor: 'rgba(244,67,54,0.05)' }}>
          {autoStartedAlerts.map((a, i) => (
            <Box
              key={a.instance_id || i}
              onClick={() => onWorkflowAutoStarted && onWorkflowAutoStarted(a)}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 0.5,
                p: 0.5,
                borderRadius: 1,
                bgcolor: 'rgba(244,67,54,0.10)',
                cursor: onWorkflowAutoStarted ? 'pointer' : 'default',
                '&:hover': onWorkflowAutoStarted ? { bgcolor: 'rgba(244,67,54,0.20)' } : {},
                transition: 'background-color 0.15s',
              }}
            >
              <WarningAmberIcon sx={{ fontSize: 14, color: 'error.main' }} />
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography sx={{ fontSize: 10, fontWeight: 700, color: 'error.main' }}>
                  ⚡ Auto-investigation started
                </Typography>
                <Typography sx={{ fontSize: 9, color: 'text.secondary', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  C{a.customer_id} · {a.alert_type?.replace(/_/g, ' ')} · {a.severity}
                </Typography>
              </Box>
              {onWorkflowAutoStarted && (
                <Tooltip title="View workflow">
                  <OpenInNewIcon sx={{ fontSize: 14, color: 'primary.main' }} />
                </Tooltip>
              )}
            </Box>
          ))}
        </Box>
      )}

      {/* Event list */}
      <Box
        ref={scrollRef}
        sx={{
          flex: 1,
          overflow: 'auto',
          fontSize: 11,
          fontFamily: '"JetBrains Mono", "Fira Code", "Consolas", monospace',
          bgcolor: '#fafafa',
          p: 0.5,
        }}
      >
        {events.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ p: 2, textAlign: 'center', fontSize: 12 }}>
            {!connected
              ? 'Connecting to event stream…'
              : producerRunning
                ? 'Waiting for events…'
                : 'Ambient feed is idle — press the ⏻ power button above to start it.'}
          </Typography>
        )}
        {events.map((evt, i) => (
          <Box
            key={evt.id || i}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
              py: 0.25,
              px: 0.5,
              borderRadius: 0.5,
              bgcolor: evt.is_anomaly
                ? (evt.alert_triggered ? 'rgba(244,67,54,0.12)' : 'rgba(255,152,0,0.10)')
                : 'transparent',
              '&:hover': { bgcolor: evt.is_anomaly ? undefined : 'rgba(0,0,0,0.03)' },
            }}
          >
            {/* Indicator dot */}
            <FiberManualRecordIcon
              sx={{
                fontSize: 8,
                color: evt.is_anomaly ? '#f44336' : '#4caf50',
                flexShrink: 0,
              }}
            />
            {/* Timestamp */}
            <Typography component="span" sx={{ fontSize: 10, color: 'text.secondary', minWidth: 55, flexShrink: 0 }}>
              {formatTime(evt.timestamp)}
            </Typography>
            {/* Event type badge */}
            <Chip
              label={EVENT_TYPE_LABELS[evt.event_type] || evt.event_type}
              size="small"
              sx={{
                height: 16,
                fontSize: 9,
                fontWeight: 700,
                bgcolor: EVENT_TYPE_COLORS[evt.event_type] || '#999',
                color: '#fff',
                minWidth: 36,
                '& .MuiChip-label': { px: 0.5 },
              }}
            />
            {/* Customer */}
            <Typography component="span" sx={{ fontSize: 10, color: 'text.primary', minWidth: 60, flexShrink: 0 }}>
              C{evt.customer_id}
            </Typography>
            {/* Details */}
            <Typography component="span" sx={{ fontSize: 10, color: 'text.secondary', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {formatDetails(evt)}
            </Typography>
            {/* Anomaly indicator */}
            {evt.alert_triggered && (
              <Chip
                label="ALERT"
                size="small"
                color="error"
                sx={{ height: 16, fontSize: 9, fontWeight: 700, ml: 'auto', '& .MuiChip-label': { px: 0.5 } }}
              />
            )}
            {evt.is_anomaly && !evt.alert_triggered && (
              <Chip
                label={evt.anomaly_rule?.replace(/_/g, ' ')}
                size="small"
                color="warning"
                sx={{ height: 16, fontSize: 8, ml: 'auto', '& .MuiChip-label': { px: 0.5 } }}
              />
            )}
          </Box>
        ))}
      </Box>

      {/* Footer status */}
      <Box sx={{ px: 1.5, py: 0.5, borderTop: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="caption" color="text.secondary">
          {events.length} events
        </Typography>
        {paused && (
          <Chip label="PAUSED" size="small" color="info" sx={{ height: 18, fontSize: 10 }} />
        )}
      </Box>
    </Paper>
  );
}
