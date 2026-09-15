import re
from bs4 import BeautifulSoup

def audit_dom():
    print("--- Auditing distress-trends.html ---")
    with open("distress-trends.html", "r", encoding="utf-8") as f:
        trends_html = f.read()
    
    soup = BeautifulSoup(trends_html, "html.parser")
    
    # 1. Trigger button
    btn = soup.find(id="openDrPriyaChatBtn")
    assert btn is not None, "Missing #openDrPriyaChatBtn in distress-trends.html"
    print("Found #openDrPriyaChatBtn with classes:", btn.get("class"))
    
    # 2. Chat modal
    modal = soup.find(id="counsellorChatModal")
    assert modal is not None, "Missing #counsellorChatModal"
    assert "pulse-modal-backdrop" in modal.get("class", [])
    print("Found #counsellorChatModal")
    
    # 3. Modal elements
    close_btn = soup.find(id="closeCounsellorChatBtn")
    assert close_btn is not None, "Missing #closeCounsellorChatBtn"
    
    container = soup.find(id="counsellorMessagesContainer")
    assert container is not None, "Missing #counsellorMessagesContainer"
    
    form = soup.find(id="counsellorChatForm")
    assert form is not None, "Missing #counsellorChatForm"
    
    inp = soup.find(id="counsellorChatInput")
    assert inp is not None, "Missing #counsellorChatInput"
    
    send_btn = soup.find(id="counsellorChatSendBtn")
    assert send_btn is not None, "Missing #counsellorChatSendBtn"
    print("All Victim Chat Modal DOM elements verified successfully!")

    print("\n--- Auditing counsellor-workspace.html ---")
    with open("counsellor-workspace.html", "r", encoding="utf-8") as f:
        workspace_html = f.read()
        
    ws_soup = BeautifulSoup(workspace_html, "html.parser")
    
    # 1. Direct messages summary counter
    cnt = ws_soup.find(id="cntDirectMessages")
    assert cnt is not None, "Missing #cntDirectMessages in counsellor-workspace.html"
    print("Found summary counter #cntDirectMessages")
    
    # 2. Tab button
    tab_btn = ws_soup.find(id="tabBtnMessages")
    assert tab_btn is not None, "Missing #tabBtnMessages in counsellor-workspace.html"
    assert tab_btn.get("data-tab") == "messages"
    print("Found tab button #tabBtnMessages with data-tab='messages'")
    
    # 3. Tab Badge
    badge = ws_soup.find(id="tabBadgeMessages")
    assert badge is not None, "Missing #tabBadgeMessages"
    
    # 4. Panel container
    panel = ws_soup.find(id="panel-messages")
    assert panel is not None, "Missing #panel-messages"
    assert "queue-panel-container" in panel.get("class", [])
    print("Found panel #panel-messages with class 'queue-panel-container'")
    
    # 5. Conversations list & active chat
    convos_list = ws_soup.find(id="counsellorConvosList")
    assert convos_list is not None, "Missing #counsellorConvosList"
    
    active_name = ws_soup.find(id="activeChatVictimName")
    assert active_name is not None, "Missing #activeChatVictimName"
    
    thread_msgs = ws_soup.find(id="counsellorThreadMessages")
    assert thread_msgs is not None, "Missing #counsellorThreadMessages"
    
    reply_form = ws_soup.find(id="counsellorReplyForm")
    assert reply_form is not None, "Missing #counsellorReplyForm"
    
    reply_text = ws_soup.find(id="counsellorReplyText")
    assert reply_text is not None, "Missing #counsellorReplyText"
    
    reply_btn = ws_soup.find(id="counsellorReplySubmitBtn")
    assert reply_btn is not None, "Missing #counsellorReplySubmitBtn"
    
    print("All Counsellor Direct Messages Workspace DOM elements verified successfully!")
    print("\nALL DOM & MARKUP AUDITS PASSED 100%!")

if __name__ == "__main__":
    audit_dom()
