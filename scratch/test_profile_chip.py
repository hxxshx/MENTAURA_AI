with open('distress-trends.html', 'r', encoding='utf-8') as f:
    html = f.read()

with open('js/trends.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Assert HTML elements
assert 'id="userProfileBtn"' in html, "Missing userProfileBtn in HTML"
assert 'id="navUserName"' in html, "Missing navUserName in HTML"
assert 'id="userProfilePopover"' in html, "Missing userProfilePopover in HTML"
assert 'nav-user-chip' in html, "Missing nav-user-chip class in HTML"
assert 'nav-user-chevron' in html, "Missing nav-user-chevron class in HTML"
assert 'id="popoverCloseBtn"' in html, "Missing popoverCloseBtn"
assert 'id="popoverCloseActionBtn"' in html, "Missing popoverCloseActionBtn"
assert 'id="popoverName"' in html, "Missing popoverName"
assert 'id="headerLogoutBtn"' in html, "Missing headerLogoutBtn"

# Assert CSS rules
assert '.nav-user-chip' in html, "Missing .nav-user-chip CSS"
assert '.user-profile-popover' in html, "Missing .user-profile-popover CSS"
assert '.user-profile-wrapper' in html, "Missing .user-profile-wrapper CSS"

# Assert JS functions
assert 'initUserProfilePopover' in js, "Missing initUserProfilePopover in js"
assert 'fetchUserDataForPopover' in js, "Missing fetchUserDataForPopover in js"

print("PROFILE CHIP & POPOVER TEST PASSED WITH 100% INTEGRITY!")
