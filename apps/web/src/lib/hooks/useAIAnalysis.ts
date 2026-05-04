import { useState, useCallback, useRef } from 'react';

export interface ThreatAnalysis {
  severity: 'Critical' | 'High' | 'Medium' | 'Low';
  rootCause: string;
  remediationSteps: string[];
  preventionTips: string[];
}

export interface AIAnalysisState {
  loading: boolean;
  error: string | null;
  analysis: ThreatAnalysis | null;
  lastAnalyzedAt: string | null;
}

export function useAIAnalysis() {
  const [state, setState] = useState<AIAnalysisState>({
    loading: false,
    error: null,
    analysis: null,
    lastAnalyzedAt: null,
  });

  const debounceTimer = useRef<NodeJS.Timeout | null>(null);
  const cacheRef = useRef<Map<string, ThreatAnalysis>>(new Map());

  const analyze = useCallback(async (events: unknown[]) => {
    if (!events || events.length === 0) {
      setState((prev) => ({ ...prev, error: 'No events to analyze' }));
      return;
    }

    // Create cache key from events
    const cacheKey = JSON.stringify(events);
    const cached = cacheRef.current.get(cacheKey);
    if (cached) {
      setState((prev) => ({
        ...prev,
        analysis: cached,
        loading: false,
        error: null,
        lastAnalyzedAt: new Date().toISOString(),
      }));
      return;
    }

    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const response = await fetch('/api/analyze-threat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ events }),
      });

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.status}`);
      }

      const analysis: ThreatAnalysis = await response.json();
      cacheRef.current.set(cacheKey, analysis);

      setState({
        loading: false,
        error: null,
        analysis,
        lastAnalyzedAt: new Date().toISOString(),
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setState((prev) => ({
        ...prev,
        loading: false,
        error: message,
      }));
    }
  }, []);

  const analyzeDebounced = useCallback(
    (events: unknown[]) => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }

      debounceTimer.current = setTimeout(() => {
        analyze(events);
      }, 5000);
    },
    [analyze]
  );

  const clear = useCallback(() => {
    setState({
      loading: false,
      error: null,
      analysis: null,
      lastAnalyzedAt: null,
    });
  }, []);

  return {
    ...state,
    analyze,
    analyzeDebounced,
    clear,
  };
}
