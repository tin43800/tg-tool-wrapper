# tg-tool-wrapper

把任何 Python 函式包成 Telegram bot — owner-lock、decorator-based、Docker 部署。

設計給「個人自動化工具想丟上 Telegram 用」的場景：翻譯小工具、查詢腳本……都能一鍵變成你私人的 Telegram bot。

## 特性

- **Sync API**（pyTelegramBotAPI）— 比 async 簡單
- **Long-polling** — 本機跑，不需要公開 IP / webhook
- **Owner lock** — 第一個發訊息的人自動成為 owner，其他人被拒絕
- **Decorator handlers** — `@bot.on_photo` / `@bot.on_document` / `@bot.on_command('start')` / `@bot.on_text`
- **Truststore 整合** — 自動處理 Avast / Zscaler 等企業 SSL 攔截
- **Docker friendly** — 跨平台、背景跑、易於部署

## 安裝

```bash
pip install git+https://github.com/tin43800/tg-tool-wrapper.git
```

或 editable install（開發用）：

```bash
git clone https://github.com/tin43800/tg-tool-wrapper.git
pip install -e ./tg-tool-wrapper
```

## 快速範例

```python
import os
from tg_tool_wrapper import TelegramBot

bot = TelegramBot(token=os.environ['TELEGRAM_BOT_TOKEN'])

@bot.on_command('start')
def cmd_start(args, message):
    return "Hi! Send me an image."

@bot.on_photo
def handle_photo(photo_path, message):
    # photo_path 是暫存路徑，handler 結束後自動刪除
    return f"收到圖片: {photo_path}"

@bot.on_document
def handle_doc(file_path, filename, message):
    return f"收到檔案: {filename}"

bot.run()
```

## Handler 回傳值

- `return "text"` → 自動 reply
- `return None` → 不 reply
- handler 中可以用 `bot.reply(message, "...")` 中途回覆進度

## Owner lock

第一次跑 bot 時，第一個發訊息的 Telegram user 會被存到 `telegram_owner.json`（`owner_file` 參數可指定路徑）。之後其他人發訊息會被忽略。

要換 owner，刪掉 `telegram_owner.json` 即可。

## 取得 Bot Token

1. Telegram 搜 `@BotFather`
2. 傳 `/newbot`
3. 給名字 + username（必須以 `bot` 結尾）
4. 收到 token：`1234567890:ABCdef...`
5. 寫進 `.env`：`TELEGRAM_BOT_TOKEN=1234567890:ABCdef...`

## 配套工具：telegram-deployer skill

如果你想「把現有 Python 工具一鍵打包成 Telegram bot」，搭配 [`telegram-deployer`](https://github.com/tin43800/tg-tool-wrapper/tree/main/skill) Claude Code skill 使用——在你的 Claude Code 說「幫我把 `parse_salary.py` 部署到 telegram」，它會自動產出 Dockerfile / docker-compose / bot.py 並啟動。

## License

MIT
