"""Сервер-посредник. Запускается на VPS: python server.py
Нужно: pip install websockets
"""
import asyncio
import json
import os
import websockets

# Ключ берётся из переменной окружения TEACHER_KEY (на хостинге), иначе из текста ниже
TEACHER_KEY = os.environ.get("TEACHER_KEY", "change-me-please")
PORT = int(os.environ.get("PORT", 8765))   # хостинг сам задаёт порт

teachers = set()
students = {}  # имя -> websocket


async def to_teachers(obj):
    data = json.dumps(obj)
    for t in list(teachers):
        try:
            await t.send(data)
        except Exception:
            teachers.discard(t)


async def handler(ws):
    role, name = None, None
    try:
        hello = json.loads(await ws.recv())
        if hello.get("role") == "teacher" and hello.get("key") == TEACHER_KEY:
            role = "teacher"
            teachers.add(ws)
            for n in students:
                await ws.send(json.dumps({"type": "join", "name": n}))
        elif hello.get("role") == "student":
            role = "student"
            name = str(hello.get("name", "pc"))[:30]
            base, i = name, 2
            while name in students:
                name = f"{base}-{i}"
                i += 1
            students[name] = ws
            await to_teachers({"type": "join", "name": name})
        else:
            return

        async for raw in ws:
            msg = json.loads(raw)
            if role == "student" and msg.get("type") == "screen":
                await to_teachers({"type": "screen", "name": name, "img": msg["img"]})
            elif role == "teacher" and msg.get("type") == "cmd":
                out = json.dumps({"cmd": msg["cmd"], "text": msg.get("text", "")})
                targets = list(students.values()) if msg.get("to") == "*" \
                    else [students.get(msg.get("to"))]
                for s in targets:
                    if s:
                        try:
                            await s.send(out)
                        except Exception:
                            pass
    except Exception:
        pass
    finally:
        if role == "teacher":
            teachers.discard(ws)
        elif role == "student" and name:
            students.pop(name, None)
            await to_teachers({"type": "leave", "name": name})


async def main():
    async with websockets.serve(handler, "0.0.0.0", PORT, max_size=5_000_000):
        print("Сервер запущен, порт", PORT)
        await asyncio.Future()


asyncio.run(main())
