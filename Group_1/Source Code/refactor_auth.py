import re

def process_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Get header from organisations.html
    with open('static/organisations.html', 'r', encoding='utf-8') as f:
        org_content = f.read()
    
    header_match = re.search(r'(<header class="header".*?</header>)', org_content, re.DOTALL)
    if not header_match:
        print("Couldn't find header in organisations.html")
        return
    header_html = header_match.group(1)

    # 1. Add styles.css if not there
    if '<link rel="stylesheet" href="styles.css">' not in content:
        content = content.replace('<title>', '<link rel="stylesheet" href="styles.css">\n <title>')

    # 2. Replace old <nav> with standard <header>
    content = re.sub(r'<nav id="navbar">.*?</nav>', header_html, content, flags=re.DOTALL)

    # 3. Strip duplicate CSS. We'll simply remove everything before `.login-container` / `.signup-container` in <style>
    # Note: we need to keep <style> tag
    if 'login.html' in file_path:
        container_class = '.login-container'
    else:
        container_class = '.signup-container'

    style_start = content.find('<style>')
    if style_start != -1:
        start_of_container = content.find(container_class, style_start)
        if start_of_container != -1:
            # We keep <style>\n and then jump to `.login-container`
            content = content[:style_start + 7] + "\n " + content[start_of_container:]

    # 4. In CSS, remove `main { ... }` or `@media` rules that target `nav`
    content = re.sub(r'main\s*\{\s*flex: 1;\s*display: flex;[^\}]*\}\s*', '', content)
    
    # In @media (max-width: 768px), nav {...} nav .logo {...} .nav-links {...}
    content = re.sub(r'nav\s*\{[^\}]*\}\s*', '', content)
    content = re.sub(r'nav\s*\.logo\s*\{[^\}]*\}\s*', '', content)
    content = re.sub(r'\.nav-links\s*\{[^\}]*\}\s*', '', content)
    
    # 5. Add script.js if not there
    if '<script src="script.js?v=2"></script>' not in content and '<script src="script.js"></script>' not in content:
        content = content.replace('</body>', ' <script src="script.js?v=2"></script>\n</body>')

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Refactored {file_path}")

process_file('static/login.html')
process_file('static/signup.html')
