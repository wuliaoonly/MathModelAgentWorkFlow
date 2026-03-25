type MessageHandler = (data: any) => void;
type ConnectionStatusHandler = (connected: boolean) => void;

export class TaskWebSocket {
  private socket: WebSocket | null = null;
  private url: string;
  private onMessage: MessageHandler;
  private onConnectionChange?: ConnectionStatusHandler;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000; // 2秒
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private shouldReconnect = true;
  private isManualClose = false;

  constructor(
    url: string, 
    onMessage: MessageHandler,
    onConnectionChange?: ConnectionStatusHandler
  ) {
    this.url = url;
    this.onMessage = onMessage;
    this.onConnectionChange = onConnectionChange;
  }

  connect() {
    // 清理之前的重连定时器
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    try {
      this.socket = new WebSocket(this.url);
      
      this.socket.onopen = () => {
        console.log('✅ WebSocket 连接已建立');
        this.reconnectAttempts = 0; // 重置重连次数
        this.onConnectionChange?.(true);
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.onMessage(data);
        } catch (error) {
          console.error('❌ 解析 WebSocket 消息失败:', error);
        }
      };

      this.socket.onclose = (event) => {
        console.log('🔌 WebSocket 连接已关闭', event.code, event.reason);
        this.onConnectionChange?.(false);

        // 检查关闭码，某些错误不应该重连
        const shouldNotReconnect = [
          1008, // Task not found
          1003, // Unsupported data
          1007, // Invalid frame payload data
          1002, // Protocol error
        ];

        if (shouldNotReconnect.indexOf(event.code) !== -1) {
          console.warn(`⚠️ 收到错误码 ${event.code}，停止重连: ${event.reason}`);
          this.shouldReconnect = false;
          return;
        }

        // 如果不是手动关闭且应该重连，则尝试重连
        if (!this.isManualClose && this.shouldReconnect) {
          this.attemptReconnect();
        }
      };

      this.socket.onerror = (error) => {
        console.error('❌ WebSocket 错误:', error);
      };
    } catch (error) {
      console.error('❌ 创建 WebSocket 连接失败:', error);
      this.attemptReconnect();
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error(`❌ 达到最大重连次数 (${this.maxReconnectAttempts})，停止重连`);
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * this.reconnectAttempts;
    
    console.log(`🔄 尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})，${delay}ms 后重试...`);

    this.reconnectTimer = setTimeout(() => {
      console.log(`🔄 开始第 ${this.reconnectAttempts} 次重连...`);
      this.connect();
    }, delay);
  }

  send(data: any) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    } else {
      console.warn('⚠️ WebSocket 未连接，无法发送消息');
    }
  }

  close() {
    this.isManualClose = true;
    this.shouldReconnect = false;
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    
    console.log('🔌 WebSocket 已手动关闭');
  }

  // 获取当前连接状态
  isConnected(): boolean {
    return this.socket !== null && this.socket.readyState === WebSocket.OPEN;
  }

  // 重置重连状态（用于页面刷新等场景）
  resetReconnect() {
    this.reconnectAttempts = 0;
    this.shouldReconnect = true;
    this.isManualClose = false;
  }
}

