import asyncio
import json
import subprocess
import time
import urllib.request
import websockets
import sys

sys.stdout.reconfigure(encoding='utf-8')

async def test_send_flow():
    chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    profile_dir = r'C:\Users\Keerthi Sridhar\.gemini\antigravity-ide\brain\9fea1111-78b7-4a2e-b9e3-82d55fdb46e6\scratch\chrome_test_profile'
    proc = subprocess.Popen([
        chrome_path,
        '--headless=new',
        '--remote-debugging-port=9223',
        '--disable-gpu',
        '--no-first-run',
        '--no-default-browser-check',
        f'--user-data-dir={profile_dir}',
        'http://127.0.0.1:8000/index.html'
    ])
    time.sleep(2)

    msg_id = 0
    ws = None
    try:
        with urllib.request.urlopen('http://127.0.0.1:9223/json') as r:
            tabs = json.loads(r.read().decode())
        
        page_tab = [t for t in tabs if t.get('type') == 'page'][0]
        ws_url = page_tab['webSocketDebuggerUrl']
        print(f"Connecting to page WS: {ws_url}")

        ws = await websockets.connect(ws_url)

        async def send_cmd(method, params=None):
            nonlocal msg_id
            msg_id += 1
            cmd = {"id": msg_id, "method": method}
            if params:
                cmd["params"] = params
            await ws.send(json.dumps(cmd))
            while True:
                resp = json.loads(await ws.recv())
                if resp.get("id") == msg_id:
                    return resp
                else:
                    if resp.get("method") == "Runtime.consoleAPICalled":
                        args = [a.get("value") for a in resp["params"]["args"]]
                        print(f"[CONSOLE {resp['params']['type']}]:", *args)
                    elif resp.get("method") == "Runtime.exceptionThrown":
                        print(f"[EXCEPTION]:", resp["params"]["exceptionDetails"])

        await send_cmd("Runtime.enable")
        await send_cmd("Page.enable")

        # 1. Login via JS fetch to get session & token
        login_script = """
        (async () => {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: 'victim@mentaura.example', password: 'Mentaura@2026' })
            });
            const data = await res.json();
            if (data.token) {
                localStorage.setItem('mentaura_token', data.token);
                localStorage.setItem('mentaura_user_role', data.verified_role || 'victim');
            }
            return data;
        })()
        """
        res = await send_cmd("Runtime.evaluate", {"expression": login_script, "awaitPromise": True, "returnByValue": True})
        print("Login result:", res.get("result", {}).get("value"))

        # 2. Navigate to checkin.html
        await send_cmd("Page.navigate", {"url": "http://127.0.0.1:8000/checkin.html"})
        await asyncio.sleep(3)

        # 3. Check elements and state
        check_script = """
        (() => {
            const thread = document.getElementById('chatbotThread');
            const input = document.getElementById('chatTextInput');
            const sendBtn = document.getElementById('chatSendBtn');
            const token = localStorage.getItem('mentaura_token');
            return {
                hasThread: !!thread,
                hasInput: !!input,
                hasSendBtn: !!sendBtn,
                sendBtnDisabled: sendBtn ? sendBtn.disabled : null,
                inputValue: input ? input.value : null,
                token: !!token
            };
        })()
        """
        res = await send_cmd("Runtime.evaluate", {"expression": check_script, "returnByValue": True})
        print("Initial DOM check:", json.dumps(res))

        # 4. Type a message into input
        type_script = """
        (() => {
            const input = document.getElementById('chatTextInput');
            input.value = "Hello, I am testing the send button.";
            input.dispatchEvent(new Event('input', { bubbles: true }));
            return input.value;
        })()
        """
        res = await send_cmd("Runtime.evaluate", {"expression": type_script, "returnByValue": True})
        print("Typed input:", json.dumps(res))

        # 5. Click the send button
        click_script = """
        (() => {
            const sendBtn = document.getElementById('chatSendBtn');
            sendBtn.click();
            return "Clicked sendBtn";
        })()
        """
        res = await send_cmd("Runtime.evaluate", {"expression": click_script, "returnByValue": True})
        print("Send click result:", json.dumps(res))

        # Wait 3 seconds to see if response arrives
        await asyncio.sleep(3)

        # 6. Check thread bubbles
        thread_script = """
        (() => {
            const thread = document.getElementById('chatbotThread');
            const bubbles = Array.from(thread.querySelectorAll('.chat-bubble')).map(b => b.textContent.trim().slice(0, 80));
            return bubbles;
        })()
        """
        res = await send_cmd("Runtime.evaluate", {"expression": thread_script, "returnByValue": True})
        print("Thread bubbles after send:", json.dumps(res))

    finally:
        if ws:
            await ws.close()
        proc.terminate()

if __name__ == '__main__':
    asyncio.run(test_send_flow())
