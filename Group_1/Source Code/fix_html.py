import os

for filename in ['static/login.html', 'static/signup.html']:
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace all backslashes with double quotes. 
    # The files contain things like `<meta charset=\UTF-8\>` which should be `<meta charset="UTF-8">`
    new_content = content.replace('\\', '"')
    
    # Wait, there's one place that was `lang=" en\>`. replacing \ will make it `lang=" en">`. That is correct.
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
print("HTML quotes fixed.")
