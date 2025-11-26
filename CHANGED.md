# 變更記錄

## 2025-11-26 10:21:15

### Socket.IO 連接錯誤修正

#### 問題描述
- Socket.IO 連接時出現 400 Bad Request 錯誤
- 錯誤訊息顯示 "Invalid session"
- 未登入用戶嘗試連接時會產生錯誤

#### 修正內容

**1. 前端 Socket.IO 連接時機調整** (`public/index.html`)
- 修改連接邏輯：先檢查用戶認證狀態，僅在已登入時才連接 Socket.IO
- 原本在頁面載入時立即連接，現在改為先調用 `/auth/me` 檢查認證狀態
- 只有當 `data.authenticated === true` 時才調用 `ensureSocket()`

**2. Socket.IO 客戶端配置改進** (`public/index.html`)
- 新增 `withCredentials: true` 確保 cookies 正確發送
- 設定 `transports: ['polling', 'websocket']` 支援多種傳輸方式
- 啟用自動重連機制：
  - `reconnection: true`
  - `reconnectionDelay: 1000`
  - `reconnectionAttempts: 5`
- 加入 `connect_error` 事件處理，針對 "Invalid session" 錯誤進行特殊處理
- 當 session 無效時，會自動檢查認證狀態並嘗試重新連接

**3. 後端 Socket.IO 配置** (`app/extensions.py`)
- 啟用 logger 以便除錯：`logger=True`
- 關閉 engineio_logger 減少日誌噪音：`engineio_logger=False`
- 保持 `cors_allowed_origins="*"` 配置（同域時 cookies 會自動發送）

**4. 錯誤處理改進** (`app/services/socketio.py`)
- 在 `on_connect` 方法中加入異常處理
- 當訪問 `current_user` 時發生錯誤（如 session 問題）會記錄警告並優雅地拒絕連接
- 避免因 session 相關錯誤導致應用程式崩潰

#### 技術細節

**問題原因：**
1. 頁面載入時立即嘗試連接 Socket.IO，但此時用戶可能尚未登入
2. 後端的 `on_connect` 檢查 `current_user.is_authenticated` 為 `False` 時返回 `False`
3. Flask-SocketIO 拒絕連接並返回 400 Bad Request
4. Session 管理問題導致 "Invalid session" 錯誤

**解決方案：**
1. 延遲 Socket.IO 連接，直到確認用戶已登入
2. 確保 cookies 正確發送以維持 session
3. 加入自動重連機制處理暫時性錯誤
4. 改進錯誤處理，避免未處理的異常

#### 影響範圍
- 減少未登入用戶的 400 錯誤
- 改善已登入用戶的連接穩定性
- 自動處理 session 過期或無效的情況
- 提升整體用戶體驗

#### 相關檔案
- `public/index.html` - 前端 Socket.IO 連接邏輯
- `app/extensions.py` - Socket.IO 初始化配置
- `app/services/socketio.py` - Socket.IO 事件處理

#### 使用者操作 (User Commands)

**應用此修正後，建議執行以下操作：**

1. **清除瀏覽器快取**
   - 按 `Ctrl + Shift + Delete` (Windows) 或 `Cmd + Shift + Delete` (Mac)
   - 選擇清除快取和 Cookie
   - 或使用無痕模式測試

2. **重新載入應用程式**
   - 如果使用開發模式：重新啟動 Flask 應用
     ```bash
     # 停止現有程序，然後重新執行
     python wsgi.py
     ```
   - 如果使用 uWSGI 生產模式：重新載入 uWSGI
     ```bash
     # 方法 1: 使用 touch-reload
     touch /tmp/uwsgi.reload
     
     # 方法 2: 使用 PID 檔案重啟
     uwsgi --reload /tmp/uwsgi.pid
     
     # 方法 3: 完全重啟
     pkill -f uwsgi
     uwsgi --ini uwsgi.ini
     ```

3. **測試連接**
   - 登入系統後，檢查瀏覽器開發者工具的 Network 標籤
   - 確認 Socket.IO 連接成功（狀態碼 200）
   - 確認不再出現 400 Bad Request 或 "Invalid session" 錯誤

4. **驗證功能**
   - 測試未登入狀態：不應出現 Socket.IO 連接錯誤
   - 測試登入後：Socket.IO 應正常連接
   - 測試重新整理頁面：連接應自動恢復

---

