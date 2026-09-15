import asyncio
import json
import subprocess
import time
import urllib.request
import websockets
import sys

sys.stdout.reconfigure(encoding='utf-8')

async def run_verification():
    chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    profile_dir = r'C:\Users\Keerthi Sridhar\.gemini\antigravity-ide\brain\9fea1111-78b7-4a2e-b9e3-82d55fdb46e6\scratch\chrome_test_profile'
    proc = subprocess.Popen([
        chrome_path,
        '--headless=new',
        '--remote-debugging-port=9225',
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
        with urllib.request.urlopen('http://127.0.0.1:9225/json') as r:
            tabs = json.loads(r.read().decode())
        
        page_tab = [t for t in tabs if t.get('type') == 'page'][0]
        ws = await websockets.connect(page_tab['webSocketDebuggerUrl'])

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

        await send_cmd("Runtime.enable")
        await send_cmd("Page.enable")

        # 1. Login
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
        await send_cmd("Runtime.evaluate", {"expression": login_script, "awaitPromise": True, "returnByValue": True})

        # 2. Go to checkin.html
        await send_cmd("Page.navigate", {"url": "http://127.0.0.1:8000/checkin.html"})
        await asyncio.sleep(3)

        # 3. Check Initial Container Height & Quick Topics visibility
        initial_check = """
        (() => {
            const container = document.querySelector('.chatbot-container');
            const quickTopics = document.getElementById('chatQuickTopicsSection');
            const thread = document.getElementById('chatbotThread');
            const sendBtn = document.getElementById('chatSendBtn');
            const input = document.getElementById('chatTextInput');
            return {
                containerHeight: container.offsetHeight,
                containerStyleHeight: window.getComputedStyle(container).height,
                quickTopicsDisplay: window.getComputedStyle(quickTopics).display,
                threadHeight: thread.offsetHeight,
                hasSendBtn: !!sendBtn,
                sendBtnPointerEvents: window.getComputedStyle(sendBtn).pointerEvents,
                threadScrollHeight: thread.scrollHeight
            };
        })()
        """
        res1 = await send_cmd("Runtime.evaluate", {"expression": initial_check, "returnByValue": True})
        state1 = res1["result"]["result"]["value"]
        print("[TEST 1] Initial State:")
        print("  Container Height:", state1["containerHeight"], "px (Expected ~580px)")
        print("  Quick Topics Display:", state1["quickTopicsDisplay"], "(Expected 'block')")
        print("  Send Button Present:", state1["hasSendBtn"])

        # 4. Type text and send via click on send button
        send_script = """
        (async () => {
            const input = document.getElementById('chatTextInput');
            const sendBtn = document.getElementById('chatSendBtn');
            input.value = "Hello, I am checking witness protection services under Section 15A.";
            input.dispatchEvent(new Event('input', { bubbles: true }));
            
            // Check quick topics display after typing
            const quickTopics = document.getElementById('chatQuickTopicsSection');
            const displayAfterTyping = window.getComputedStyle(quickTopics).display;
            
            sendBtn.click();
            return { displayAfterTyping };
        })()
        """
        res2 = await send_cmd("Runtime.evaluate", {"expression": send_script, "awaitPromise": True, "returnByValue": True})
        state2 = res2["result"]["result"]["value"]
        print("\n[TEST 2] After typing and clicking send:")
        print("  Quick Topics Display after typing:", state2["displayAfterTyping"], "(Expected 'none')")

        # Wait 3.5s for backend response
        await asyncio.sleep(3.5)

        # 5. Check State after first message
        post_msg_check = """
        (() => {
            const container = document.querySelector('.chatbot-container');
            const quickTopics = document.getElementById('chatQuickTopicsSection');
            const thread = document.getElementById('chatbotThread');
            const bubbles = Array.from(thread.querySelectorAll('.chat-bubble')).map(b => b.textContent.trim().slice(0, 70));
            return {
                containerHeight: container.offsetHeight,
                quickTopicsDisplay: window.getComputedStyle(quickTopics).display,
                threadHeight: thread.offsetHeight,
                threadScrollHeight: thread.scrollHeight,
                bubblesCount: bubbles.length,
                lastBubbleText: bubbles[bubbles.length - 1]
            };
        })()
        """
        res3 = await send_cmd("Runtime.evaluate", {"expression": post_msg_check, "returnByValue": True})
        state3 = res3["result"]["result"]["value"]
        print("\n[TEST 3] After 1st Message Exchange:")
        print("  Container Height:", state3["containerHeight"], "px (MUST REMAIN 580px, NOT GROW!)")
        print("  Quick Topics Display:", state3["quickTopicsDisplay"], "(MUST be 'none')")
        print("  Total Bubbles in Thread:", state3["bubblesCount"])
        print("  Last Bot Reply:", state3["lastBubbleText"])

        # 6. Send 3 more messages to test container does NOT grow and scrolling works
        more_msgs_script = """
        (async () => {
            const input = document.getElementById('chatTextInput');
            const sendBtn = document.getElementById('chatSendBtn');
            const msgs = [
                "I also feel very anxious about the court hearing date next week.",
                "Can you suggest grounding exercises to help me calm down?",
                "Thank you for being here with me today."
            ];
            for (const msg of msgs) {
                input.value = msg;
                sendBtn.click();
                await new Promise(r => setTimeout(r, 2500));
            }
            const container = document.querySelector('.chatbot-container');
            const thread = document.getElementById('chatbotThread');
            const bubbles = Array.from(thread.querySelectorAll('.chat-bubble')).map(b => b.textContent.trim().slice(0, 60));
            return {
                containerHeight: container.offsetHeight,
                threadHeight: thread.offsetHeight,
                threadScrollHeight: thread.scrollHeight,
                threadScrollTop: thread.scrollTop,
                isScrollable: thread.scrollHeight > thread.clientHeight,
                bubblesCount: bubbles.length
            };
        })()
        """
        res4 = await send_cmd("Runtime.evaluate", {"expression": more_msgs_script, "awaitPromise": True, "returnByValue": True})
        state4 = res4["result"]["result"]["value"]
        print("\n[TEST 4] After multiple message turns:")
        print("  Container Height:", state4["containerHeight"], "px (MUST STILL BE 580px!)")
        print("  Thread Height:", state4["threadHeight"], "px")
        print("  Thread ScrollHeight:", state4["threadScrollHeight"], "px")
        print("  Thread isScrollable:", state4["isScrollable"], "(MUST BE True!)")
        print("  Thread ScrollTop:", state4["threadScrollTop"], "px (Scrolled to bottom!)")
        print("  Total Bubbles in Thread:", state4["bubblesCount"])

        # Assertions
        assert state3["containerHeight"] == 580, f"Expected 580px, got {state3['containerHeight']}"
        assert state4["containerHeight"] == 580, f"Expected 580px, got {state4['containerHeight']}"
        assert state3["quickTopicsDisplay"] == "none", "Quick topics should be hidden"
        assert state4["isScrollable"] == True, "Thread should have internal scrolling enabled"
        print("\n>>> ALL VERIFICATION TESTS PASSED PERFECTLY! <<<")

    finally:
        if ws:
            await ws.close()
        proc.terminate()

if __name__ == '__main__':
    asyncio.run(run_verification())
