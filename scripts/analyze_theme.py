import os
from bs4 import BeautifulSoup

def analyze_theme(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # We use html.parser instead of xml to be lenient with Blogger's pseudo-XML
    soup = BeautifulSoup(content, 'html.parser')
    
    scripts = soup.find_all('script')
    
    print(f"Total scripts found: {len(scripts)}")
    
    external_scripts = []
    inline_scripts = []
    
    for i, script in enumerate(scripts):
        src = script.get('src')
        if src:
            external_scripts.append((i, src, script.get('defer'), script.get('async')))
        else:
            inline_content = script.string if script.string else ""
            inline_scripts.append((i, len(inline_content), inline_content[:100].replace('\n', ' ')))
            
    print("\n--- EXTERNAL SCRIPTS ---")
    for i, src, defer, is_async in external_scripts:
        print(f"[{i}] {src} (defer: {defer}, async: {is_async})")
        
    print("\n--- INLINE SCRIPTS (Preview) ---")
    for i, length, preview in inline_scripts:
        print(f"[{i}] Length: {length} bytes | Preview: {preview}")

if __name__ == "__main__":
    analyze_theme('optimized-blogger-theme.xml')
