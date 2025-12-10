import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom';
import React, { Component, ErrorInfo, ReactNode, useEffect } from 'react';
const Canvas = React.lazy(() => import('./components/canvas/Canvas').then(module => ({ default: module.Canvas })));
import { Login } from './pages/Login';
import { Rooms } from './pages/Rooms';
import { Welcome } from './pages/Welcome';
import Settings from './pages/Settings';
import { Loader2 } from 'lucide-react';
import { ThemeProvider } from './components/common/ThemeProvider';
import { NotificationProvider } from './components/common/NotificationProvider';

// ==================== 错误边界组件 ====================
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
    console.error('React Error Boundary 捕获错误:', error);
    console.error('组件堆栈:', errorInfo.componentStack);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-red-50 flex items-center justify-center p-8">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-2xl w-full">
            <h1 className="text-2xl font-bold text-red-600 mb-4">⚠️ 应用发生错误</h1>
            <div className="bg-red-100 rounded p-4 mb-4">
              <p className="font-mono text-sm text-red-800">
                {this.state.error?.message}
              </p>
            </div>
            {this.state.errorInfo && (
              <details className="mb-4">
                <summary className="cursor-pointer text-gray-600 hover:text-gray-800">
                  查看详细堆栈
                </summary>
                <pre className="mt-2 p-4 bg-gray-100 rounded text-xs overflow-auto max-h-64">
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              刷新页面
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// ==================== 全局错误监听 ====================
const GlobalErrorHandler = () => {
  useEffect(() => {
    // 捕获未处理的 Promise 错误
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      console.error('未处理的 Promise 错误:', event.reason);
      // 可以在这里显示 toast 通知
    };

    // 捕获全局 JS 错误
    const handleError = (event: ErrorEvent) => {
      console.error('全局 JS 错误:', event.message, '\n位置:', event.filename, ':', event.lineno);
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

// ==================== 路由保护 ====================
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const token = localStorage.getItem('token');
  const isGuest = localStorage.getItem('isGuest') === 'true';

  // 允许有 token 或游客模式访问
  if (!token && !isGuest) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

// ==================== 主应用 ====================
function App() {
  return (
    <ThemeProvider>
      <NotificationProvider>
        <ErrorBoundary>
          <GlobalErrorHandler />
          <BrowserRouter>
            <Routes>
              {/* 欢迎页 - 应用入口 */}
              <Route path="/" element={<Welcome />} />

              {/* 登录页 */}
              <Route path="/login" element={<Login />} />

              {/* 房间列表 */}
              <Route
                path="/rooms"
                element={
                  <ProtectedRoute>
                    <Rooms />
                  </ProtectedRoute>
                }
              />

              {/* AI 设置页面 */}
              <Route
                path="/settings"
                element={
                  <ProtectedRoute>
                    <Settings />
                  </ProtectedRoute>
                }
              />

              {/* 画布房间 */}
              <Route
                path="/room/:roomId"
                element={
                  <ProtectedRoute>
                    <Board />
                  </ProtectedRoute>
                }
              />
            </Routes>
          </BrowserRouter>
        </ErrorBoundary>
      </NotificationProvider>
    </ThemeProvider>
  );
}

const Board = () => {
  const { roomId } = useParams<{ roomId: string }>();
  return (
    <div className="App">
      <React.Suspense fallback={
        <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
          <div className="text-center">
            <Loader2 className="h-10 w-10 animate-spin text-blue-500 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">正在加载画布...</p>
          </div>
        </div>
      }>
        <Canvas roomId={roomId} />
      </React.Suspense>
    </div>
  );
};

export default App;
