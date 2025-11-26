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

## 2025-11-26 10:35:51

### Socket.IO 連接錯誤進一步修正

#### 問題描述
- Socket.IO 連接失敗後仍不斷重複嘗試連接
- 控制台出現大量 400 Bad Request 錯誤和連接錯誤訊息
- 即使禁用自動重連，錯誤處理邏輯仍會觸發重試

#### 修正內容

**1. 完全禁用自動重連機制** (`public/index.html`)
- 將 `reconnection: false` 明確設置，完全禁用 Socket.IO 的自動重連
- 加入連接狀態標誌 (`socketConnectionAttempted`, `socketConnectionFailed`) 防止重複嘗試
- 在連接失敗時清理所有事件監聽器，避免殘留的連接嘗試

**2. 改進錯誤處理邏輯** (`public/index.html`)
- 移除錯誤處理中的自動重試邏輯
- 連接失敗時不再自動檢查認證狀態並重試
- 抑制常見的 session/auth 錯誤訊息，減少控制台噪音
- 只有在連接成功時才重置失敗標誌

**3. 改進 `joinSocketRoom` 函數** (`public/index.html`)
- 檢查連接狀態後再嘗試加入房間
- 如果連接失敗，不會立即嘗試重新連接
- 加入短暫延遲等待連接建立

#### 技術細節

**問題原因：**
1. Socket.IO 的自動重連機制在連接失敗後仍會嘗試重連
2. 錯誤處理邏輯中的重試機制導致重複連接嘗試
3. 連接失敗標誌未正確管理，導致多次嘗試

**解決方案：**
1. 完全禁用自動重連，改為手動控制
2. 使用連接狀態標誌防止重複嘗試
3. 連接失敗時清理所有資源，避免殘留連接
4. 只在用戶明確操作（如登入）後才嘗試連接

#### 影響範圍
- 大幅減少控制台錯誤訊息
- 避免無意義的重複連接嘗試
- 改善應用程式性能和資源使用
- 提供更清晰的錯誤狀態管理

#### 相關檔案
- `public/index.html` - Socket.IO 連接邏輯和錯誤處理

#### 使用者操作 (User Commands)

**應用此修正後，建議執行以下操作：**

1. **清除瀏覽器快取和 Cookie**
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

3. **驗證修正效果**
   - 未登入狀態：不應出現任何 Socket.IO 連接嘗試
   - 登入後：Socket.IO 應正常連接，不應出現重複嘗試
   - 控制台：不應出現大量 400 錯誤或連接錯誤訊息

---

## 2025-11-26 10:57:51

### 502 Bad Gateway 錯誤處理與代碼穩定性改進

#### 問題描述
- `/rooms` 端點返回 502 Bad Gateway 錯誤
- `/members` 端點返回 502 Bad Gateway 錯誤
- `/auth/me` 端點也出現失敗
- Socket.IO 連接失敗
- 502 錯誤表示反向代理（Cloudflare）無法連接到後端應用服務器

#### 修正內容

**1. `/members` 端點錯誤處理** (`app/controllers/rooms.py`)
- 加入完整的 try-except 錯誤處理
- 處理可能的 None 值（`name`, `email`, `image`, `created_at` 等）
- 加入資料庫 rollback 機制
- 記錄錯誤日誌以便除錯
- 確保所有欄位都有預設值，避免序列化錯誤

**2. `/rooms/<room_id>/messages` 端點錯誤處理** (`app/controllers/messages.py`)
- 加入完整的 try-except 錯誤處理
- 處理可能的 None 值（`author`, `created_at` 等）
- 加入資料庫 rollback 機制
- 記錄錯誤日誌以便除錯

**3. Socket.IO 全局錯誤處理器** (`app/services/socketio.py`)
- 添加 `@socketio.on_error_default` 裝飾器
- 捕獲所有未處理的 Socket.IO 錯誤
- 記錄錯誤日誌以便除錯

**4. Socket.IO 連接配置改進** (`app/extensions.py`)
- 添加 `ping_timeout=60` 和 `ping_interval=25`
- 改善 WebSocket 連接穩定性

#### 502 Bad Gateway 錯誤診斷

**502 錯誤通常表示：**
1. 後端應用服務器（uWSGI/Flask）沒有運行
2. 應用服務器崩潰或無法響應
3. 反向代理無法連接到後端服務器
4. 應用服務器超時

**診斷步驟：**

1. **檢查應用服務器狀態**
   ```bash
   # 檢查 uWSGI 進程是否運行
   ps aux | grep uwsgi
   
   # 檢查 uWSGI PID 文件
   cat /tmp/uwsgi.pid
   
   # 檢查 uWSGI 日誌
   tail -f /tmp/uwsgi.log
   ```

2. **檢查應用服務器配置**
   - 確認 uWSGI 配置正確
   - 確認應用服務器監聽的端口與反向代理配置一致
   - 確認 Cloudflare/Nginx 正確配置了後端代理

3. **重啟應用服務器**
   ```bash
   # 如果使用 uWSGI
   touch /tmp/uwsgi.reload
   
   # 或完全重啟
   pkill -f uwsgi
   uwsgi --ini uwsgi.ini
   ```

4. **檢查應用日誌**
   - 查看應用程式日誌以確認是否有未處理的異常
   - 檢查資料庫連接是否正常
   - 確認所有依賴服務（MySQL）都在運行

#### 技術細節

**問題原因：**
1. 缺少錯誤處理可能導致應用崩潰
2. 未處理的異常可能導致整個應用服務器無響應
3. 資料庫查詢錯誤可能導致應用掛起
4. None 值序列化錯誤可能導致應用崩潰

**解決方案：**
1. 為所有關鍵端點加入完整的錯誤處理
2. 確保所有資料庫操作都有 rollback 機制
3. 處理可能的 None 值，避免序列化錯誤
4. 添加全局錯誤處理器捕獲未處理的異常
5. 改善 Socket.IO 連接配置以提升穩定性

#### 影響範圍
- 提升應用程式穩定性
- 避免因未處理異常導致應用崩潰
- 改善錯誤診斷能力
- 減少 502 錯誤的發生
- 改善 WebSocket 連接穩定性

#### 相關檔案
- `app/controllers/rooms.py` - `/members` 端點錯誤處理
- `app/controllers/messages.py` - 訊息端點錯誤處理
- `app/services/socketio.py` - Socket.IO 全局錯誤處理器
- `app/extensions.py` - Socket.IO 連接配置

#### 使用者操作 (User Commands)

**應用此修正後，建議執行以下操作：**

1. **檢查服務器狀態**
   ```bash
   # 檢查 uWSGI 是否運行
   ps aux | grep uwsgi
   
   # 檢查日誌
   tail -50 /tmp/uwsgi.log
   ```

2. **重啟應用服務器**
   ```bash
   # 方法 1: 使用 touch-reload
   touch /tmp/uwsgi.reload
   
   # 方法 2: 完全重啟
   pkill -f uwsgi
   uwsgi --ini uwsgi.ini
   ```

3. **檢查資料庫連接**
   ```bash
   # 確認 MySQL 服務運行
   systemctl status mysql
   # 或
   service mysql status
   ```

4. **測試端點**
   - 測試 `/auth/me`：應返回認證狀態
   - 測試 `/rooms`：應返回房間列表
   - 測試 `/members`：應返回成員列表
   - 測試 Socket.IO 連接：檢查是否正常連接

5. **監控日誌**
   - 持續監控應用日誌以確認錯誤是否解決
   - 檢查是否有新的錯誤訊息

---

## 2025-11-26 (最新修正)

### 前端錯誤處理改進與 Socket.IO 連接優化

#### 問題描述
- Socket.IO 連接持續返回 400 Bad Request 錯誤
- WebSocket 連接在建立前就被關閉
- `/auth/me` 端點可能返回錯誤，但仍嘗試連接 Socket.IO
- `net::ERR_BLOCKED_BY_CLIENT` 錯誤（Cloudflare Insights 被瀏覽器擴展阻止，非應用問題）

#### 修正內容

**1. 認證檢查錯誤處理改進** (`public/index.html`)
- 在調用 `/auth/me` 後檢查 `res.ok`，只有成功時才處理響應
- 認證失敗時不嘗試連接 Socket.IO
- 添加更詳細的日誌訊息以便除錯
- 確保在認證錯誤時不會嘗試 Socket.IO 連接

**2. `loadRooms` 函數改進** (`public/index.html`)
- 添加空房間列表的處理
- 當沒有房間時顯示友好訊息
- 改進錯誤處理邏輯

**3. `loadMembers` 函數改進** (`public/index.html`)
- 改進錯誤處理註釋
- 確保失敗時不會影響其他功能

#### 技術細節

**問題原因：**
1. 即使 `/auth/me` 返回錯誤（如 400 或 500），前端仍嘗試解析 JSON 並可能觸發 Socket.IO 連接
2. 缺少對 HTTP 狀態碼的檢查
3. 錯誤處理不夠嚴格

**解決方案：**
1. 在處理響應前檢查 HTTP 狀態碼
2. 只有認證成功時才嘗試連接 Socket.IO
3. 改進錯誤日誌以便診斷問題
4. 確保所有錯誤情況都被正確處理

#### 關於 `net::ERR_BLOCKED_BY_CLIENT`

這個錯誤通常是由瀏覽器擴展（如廣告攔截器）阻止 Cloudflare Insights 腳本載入造成的，**不是應用程式的問題**。可以安全地忽略此錯誤。

#### 影響範圍
- 避免在認證失敗時嘗試 Socket.IO 連接
- 減少不必要的連接嘗試
- 改善錯誤診斷能力
- 提升用戶體驗

#### 相關檔案
- `public/index.html` - 前端認證檢查和錯誤處理

#### 使用者操作 (User Commands)

**應用此修正後，建議執行以下操作：**

1. **清除瀏覽器快取和 Cookie**
   - 按 `Ctrl + Shift + Delete` (Windows) 或 `Cmd + Shift + Delete` (Mac)
   - 選擇清除快取和 Cookie
   - 或使用無痕模式測試

2. **重新載入應用程式**
   - 如果使用開發模式：重新啟動 Flask 應用
     ```bash
     python wsgi.py
     ```
   - 如果使用 uWSGI 生產模式：重新載入 uWSGI
     ```bash
     touch /tmp/uwsgi.reload
     ```

3. **測試認證流程**
   - 未登入狀態：不應出現 Socket.IO 連接嘗試
   - 登入後：Socket.IO 應正常連接
   - 檢查控制台：不應出現大量 400 錯誤

4. **檢查服務器狀態**
   - 確認 uWSGI 正在運行
   - 檢查應用日誌以確認是否有錯誤

---

