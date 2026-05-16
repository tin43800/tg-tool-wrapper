# Handler block snippets

Pick the snippet matching `HANDLER_TYPE` from Step 1 and substitute as `{{HANDLER_BLOCK}}` in `bot.py.template`.

Adapt the function call inside each block to the user's tool's actual signature.

---

## photo

```python
@bot.on_photo
def handle_photo(photo_path, message):
    bot.reply(message, "📸 Processing…")
    result = {{USER_FUNCTION}}(photo_path)
    return f"✅ Result:\n{result}"
```

---

## document

```python
@bot.on_document
def handle_document(file_path, filename, message):
    bot.reply(message, f"📄 Processing {filename}…")
    result = {{USER_FUNCTION}}(file_path)
    return f"✅ Result:\n{result}"
```

---

## text

```python
@bot.on_text
def handle_text(text, message):
    result = {{USER_FUNCTION}}(text)
    return f"{result}"
```

---

## command

```python
@bot.on_command("{{COMMAND_NAME}}")
def handle_cmd(args, message):
    if not args:
        return "Usage: /{{COMMAND_NAME}} <arg>"
    result = {{USER_FUNCTION}}(args)
    return f"{result}"
```
