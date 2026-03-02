import os
import re
import glob

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # We want to replace the whole Sync to Markdown section and the Critical rule.
    # We will just do a few specific targeted replacements.
    
    # Replace the headers
    content = re.sub(r'(?:#+)\s*(?:Phase \d+(?:\.\d+)?\s*:?\s*)?Sync to Markdown \(MANDATORY\).*?(?=\n\n#|\Z)', 
        "### Markdown Sync (Automatic)\n\nThe git pre-commit hook automatically exports Beads state to spec.md on commit.\n**CRITICAL:** Do NOT write markers directly to spec.md and do NOT run sync manually.", 
        content, flags=re.DOTALL | re.IGNORECASE)
    
    # Replace in Critical Rules section:
    # "MANDATORY SYNC - Run `/flow-sync` after..."
    content = re.sub(r'\d+\.\s+\*\*MANDATORY SYNC\*\*.*?\n', '', content)
    
    # Some files use "Sync to markdown: run `$flow:sync {flow_id}` (MANDATORY)" in lists
    content = re.sub(r'\d+\.\s+Sync to markdown:.*MANDATORY.*\n', '', content)
    
    with open(filepath, 'w') as f:
        f.write(content)

# Search in templates and commands
for root_dir in ['templates', 'commands']:
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.md') or file.endswith('.toml'):
                process_file(os.path.join(root, file))

print("Completed replacements")
