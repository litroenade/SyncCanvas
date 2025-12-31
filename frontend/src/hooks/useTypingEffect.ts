/**
 * useTypingEffect - 打字机效果 Hook
 * 
 * 用于模拟打字机效果，逐字显示文本。
 */

import { useState, useEffect, useRef, useCallback } from 'react';

interface UseTypingEffectOptions {
    /** 打字速度 (每个字符的延迟毫秒数) */
    speed?: number;
    /** 完成回调 */
    onComplete?: () => void;
    /** 是否立即显示完整文本 */
    instant?: boolean;
}

interface UseTypingEffectReturn {
    /** 当前显示的文本 */
    displayText: string;
    /** 是否正在打字 */
    isTyping: boolean;
    /** 是否已完成 */
    isComplete: boolean;
    /** 跳过动画，立即显示完整文本 */
    skip: () => void;
    /** 重置并开始新文本 */
    start: (text: string) => void;
}

/**
 * 打字机效果 Hook
 * 
 * @param initialText - 初始文本
 * @param options - 配置选项
 * @returns 打字机状态和控制函数
 * 
 * @example
 * ```tsx
 * const { displayText, isTyping, skip } = useTypingEffect(message, { speed: 30 });
 * return <p>{displayText}{isTyping && <span className="cursor">|</span>}</p>;
 * ```
 */
export function useTypingEffect(
    initialText: string = '',
    options: UseTypingEffectOptions = {}
): UseTypingEffectReturn {
    const { speed = 30, onComplete, instant = false } = options;

    const [displayText, setDisplayText] = useState(instant ? initialText : '');
    const [isTyping, setIsTyping] = useState(!instant && initialText.length > 0);
    const [isComplete, setIsComplete] = useState(instant || initialText.length === 0);

    const fullTextRef = useRef(initialText);
    const indexRef = useRef(instant ? initialText.length : 0);
    const timerRef = useRef<number | null>(null);

    const clearTimer = useCallback(() => {
        if (timerRef.current !== null) {
            window.clearTimeout(timerRef.current);
            timerRef.current = null;
        }
    }, []);

    const typeNextChar = useCallback(() => {
        if (indexRef.current < fullTextRef.current.length) {
            indexRef.current += 1;
            setDisplayText(fullTextRef.current.slice(0, indexRef.current));

            timerRef.current = window.setTimeout(typeNextChar, speed);
        } else {
            setIsTyping(false);
            setIsComplete(true);
            onComplete?.();
        }
    }, [speed, onComplete]);

    // 当初始文本变化时更新
    useEffect(() => {
        if (instant) {
            setDisplayText(initialText);
            setIsComplete(true);
            setIsTyping(false);
            fullTextRef.current = initialText;
            indexRef.current = initialText.length;
            return;
        }

        // 如果新文本是当前文本的延续，继续打字
        if (initialText.startsWith(fullTextRef.current)) {
            fullTextRef.current = initialText;
            if (!isTyping && indexRef.current < initialText.length) {
                setIsTyping(true);
                setIsComplete(false);
                typeNextChar();
            }
        } else {
            // 新文本完全不同，重新开始
            fullTextRef.current = initialText;
            indexRef.current = 0;
            setDisplayText('');
            setIsTyping(initialText.length > 0);
            setIsComplete(initialText.length === 0);

            if (initialText.length > 0) {
                typeNextChar();
            }
        }

        return clearTimer;
    }, [initialText, instant, typeNextChar, clearTimer, isTyping]);

    const skip = useCallback(() => {
        clearTimer();
        setDisplayText(fullTextRef.current);
        indexRef.current = fullTextRef.current.length;
        setIsTyping(false);
        setIsComplete(true);
        onComplete?.();
    }, [clearTimer, onComplete]);

    const start = useCallback((text: string) => {
        clearTimer();
        fullTextRef.current = text;
        indexRef.current = 0;
        setDisplayText('');
        setIsTyping(text.length > 0);
        setIsComplete(text.length === 0);

        if (text.length > 0) {
            typeNextChar();
        }
    }, [clearTimer, typeNextChar]);

    // 清理
    useEffect(() => {
        return clearTimer;
    }, [clearTimer]);

    return {
        displayText,
        isTyping,
        isComplete,
        skip,
        start,
    };
}

export default useTypingEffect;
