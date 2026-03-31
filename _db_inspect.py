import sqlite3
import json

conn = sqlite3.connect('llm_manager.db')
conn.row_factory = sqlite3.Row

# 1. 所有表
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables:", tables)

# 2. channels 表完整数据
for row in conn.execute("SELECT * FROM channels WHERE name IN ('local_deepseek', 'local_kimi')").fetchall():
    print(json.dumps(dict(row), ensure_ascii=False, default=str))

# 3. 如果有 model_configs 表
if 'model_configs' in tables:
    print("\n--- model_configs ---")
    for row in conn.execute("SELECT * FROM model_configs").fetchall():
        print(json.dumps(dict(row), ensure_ascii=False, default=str))

# 4. 如果有 channel_configs 表
if 'channel_configs' in tables:
    print("\n--- channel_configs ---")
    for row in conn.execute("SELECT * FROM channel_configs").fetchall():
        print(json.dumps(dict(row), ensure_ascii=False, default=str))

conn.close()
