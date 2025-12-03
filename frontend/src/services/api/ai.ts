import axios from 'axios';
import { config } from '../../config/env';

/**
 * AI 服务接口
 */
export const aiApi = {
    /**
     * 调用 AI 生成图形
     * @param prompt - 用户提示词
     * @param roomId - 房间 ID
     * @returns 生成结果
     */
    generateShapes: async (prompt: string, roomId: string) => {
        const response = await axios.post(`${config.apiBaseUrl}/ai/generate`, {
            prompt,
            room_id: roomId,
        });
        return response.data;
    },
};

