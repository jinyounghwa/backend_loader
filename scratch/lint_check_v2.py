import os
import re

def find_errors(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                
                # F401: Unused import
                content = "".join(lines)
                if "from typing import" in content and "Optional" in content:
                    # Very crude check: does 'Optional' appear anywhere else?
                    if content.count("Optional") < 2:
                         print(f"F401: Unused Optional in {filepath}")

                # F821: Undefined name
                if "AWSClientProvider." in content:
                    if "import AWSClientProvider" not in content and "from guardian.aws_client_provider import AWSClientProvider" not in content and "class AWSClientProvider" not in content:
                        print(f"F821: Undefined AWSClientProvider in {filepath}")

                # E226: Missing whitespace around arithmetic operator
                for i, line in enumerate(lines):
                    # Check for patterns like a+b, a-b, a*b, a/b where a,b are alphanumeric
                    # and no space around the operator
                    matches = re.finditer(r"[a-zA-Z0-9][+\-*/][a-zA-Z0-9]", line)
                    for match in matches:
                        # Exclude some false positives like f-strings or dates
                        s = match.group()
                        if not re.search(r"\d{4}-\d{2}-\d{2}", line): # Exclude dates
                            print(f"E226 potential: {s} in {filepath}:{i+1}")

                # W391: Blank line at end of file
                if len(lines) > 0 and lines[-1].strip() == "":
                    # Check if the last two lines are blank
                    if len(lines) > 1 and lines[-2].strip() == "":
                        print(f"W391: Blank line at end of {filepath}")

find_errors('/Users/younghwa.jin/Documents/backend_loader/lambda/guardian')
