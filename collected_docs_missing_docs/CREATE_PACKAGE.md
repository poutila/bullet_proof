**ULTRATHINK**
Make plan.
Create PACKAGE_TODO.md
What would be refactoring needs to use this as package for analysing ai coding instructions.
i.e. a module that could be use as a dependency in ai assisted coding projects.
usage would be e.g.
pip install docpipe -e
from docpipe import analyze_project
results = analyze_project("/path/to/markdowns")
print(results.missing_references)
print(results.must_have_files)
.
.
print(results.feedback)
How to construck interface? 

General guide.
   - Think hard before you execute this task. Create a comprehensive plan addressing all requirements.
   - Break down complex tasks into smaller, manageable steps using your PACKAGE_TODO.md.
   - Use the file to create and track your implementation plan.
   - Identify implementation patterns from existing code to follow.
