import React, { Component, type ErrorInfo, type ReactNode, useEffect } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Loader2 } from 'lucide-react';

import { ThemeProvider } from './components/common/ThemeProvider';
import { NotificationProvider } from './components/common/NotificationProvider';
import { SINGLETON_CANVAS_ID, SINGLETON_CANVAS_NAME } from './config/singletonCanvas';
import { I18nProvider, translate, useI18n } from './i18n';

const Canvas = React.lazy(() =>
  import('./components/canvas/Canvas').then((module) => ({ default: module.Canvas })),
);

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('React Error Boundary caught an error:', error);
    console.error('Component stack:', errorInfo.componentStack);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-red-50 p-8 dark:bg-zinc-950">
          <div className="w-full max-w-2xl rounded-lg border border-red-100 bg-white p-6 shadow-xl dark:border-zinc-800 dark:bg-zinc-900">
            <h1 className="mb-4 text-2xl font-bold text-red-600 dark:text-red-300">
              {translate('app.errorTitle')}
            </h1>
            <div className="mb-4 rounded bg-red-100 p-4 dark:bg-red-950/40">
              <p className="font-mono text-sm text-red-800 dark:text-red-100">
                {this.state.error?.message}
              </p>
            </div>
            {this.state.errorInfo && (
              <details className="mb-4">
                <summary className="cursor-pointer text-gray-600 hover:text-gray-800 dark:text-zinc-400 dark:hover:text-zinc-200">
                  {translate('app.showStackTrace')}
                </summary>
                <pre className="mt-2 max-h-64 overflow-auto rounded bg-gray-100 p-4 text-xs dark:bg-zinc-950 dark:text-zinc-300">
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}
            <button
              onClick={() => window.location.reload()}
              className="rounded bg-blue-500 px-4 py-2 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-500"
            >
              {translate('app.reloadPage')}
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

const GlobalErrorHandler = () => {
  useEffect(() => {
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      console.error('Unhandled promise rejection:', event.reason);
    };

    const handleError = (event: ErrorEvent) => {
      console.error(
        'Global JS error:',
        event.message,
        '\nLocation:',
        event.filename,
        ':',
        event.lineno,
      );
    };

    window.addEventListener('unhandledrejection', handleUnhandledRejection);
    window.addEventListener('error', handleError);

    return () => {
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
      window.removeEventListener('error', handleError);
    };
  }, []);

  return null;
};

const Board = () => {
  const { t } = useI18n();

  return (
    <div className="App">
      <React.Suspense
        fallback={(
          <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
            <div className="text-center">
              <Loader2 className="mx-auto mb-4 h-10 w-10 animate-spin text-blue-500" />
              <p className="text-gray-500 dark:text-gray-400">{t('app.loadingCanvas')}</p>
            </div>
          </div>
        )}
      >
        <Canvas roomId={SINGLETON_CANVAS_ID} roomName={SINGLETON_CANVAS_NAME} />
      </React.Suspense>
    </div>
  );
};

function App() {
  return (
    <I18nProvider>
      <ThemeProvider>
        <NotificationProvider>
          <ErrorBoundary>
            <GlobalErrorHandler />
            <BrowserRouter>
              <Routes>
                <Route path="/" element={<Board />} />
                {/* Single-instance mode disables login/rooms/join flows without deleting the codepaths. */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </BrowserRouter>
          </ErrorBoundary>
        </NotificationProvider>
      </ThemeProvider>
    </I18nProvider>
  );
}

export default App;
