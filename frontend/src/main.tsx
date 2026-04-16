import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { initializeTheme } from './stores/useThemeStore';
import { initializeLocale } from './stores/useLocaleStore';

const queryClient = new QueryClient();
initializeTheme();
initializeLocale();

// 注意：不使用 React.StrictMode
// StrictMode 在开发模式下会双重渲染组件（mount→unmount→mount）
// 这会导致 WebSocket 连接立即断开
ReactDOM.createRoot(document.getElementById('root')!).render(
    <QueryClientProvider client={queryClient}>
        <App />
    </QueryClientProvider>
);
