import os
import ast

def check_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"Syntax Error in {filepath}: {e}")
        return

    # Check for undefined names (F821)
    # This is complex with AST, but we can look for specific names
    # Also check for unused imports (F401)
    
    # We'll just look for 'Optional' and 'AWSClientProvider'
    has_optional_import = "Optional" in content and "from typing import" in content
    uses_optional = "Optional[" in content or ": Optional" in content
    
    has_aws_provider_usage = "AWSClientProvider." in content
    has_aws_provider_import = "import AWSClientProvider" in content or "from guardian.aws_client_provider import AWSClientProvider" in content

    if has_optional_import and not uses_optional:
        print(f"F401: 'Optional' imported but unused in {filepath}")
    
    if has_aws_provider_usage and not has_aws_provider_import and "class AWSClientProvider" not in content:
        print(f"F821: Undefined name 'AWSClientProvider' in {filepath}")

for root, dirs, files in os.walk('/Users/younghwa.jin/Documents/backend_loader/lambda/guardian'):
    for file in files:
        if file.endswith('.py'):
            check_file(os.path.join(root, file))
