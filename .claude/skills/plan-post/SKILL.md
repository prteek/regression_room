---
name: plan-post
description: "Create high level plan for the post by interactively gathering information and documenting it"
disable-model-invocation: true
---

When asked to plan a post do the following:

1. Ask questions about the analysis **one by one and interactively** from @.claude/skills/plan-post/QUESTIONS.md
2. Do not start exploring data sources or tables at this stage and do not define technical or implementation details
3. After relevant questions have been answered and information about analysis is agreed upon, document the analysis plan using @.claude/skills/plan-post/DOCUMENTATION.md
4. Show the plan document to the user and get approval
5. Once the plan document is approved, create a post directory and save the plan there
6. Add instructions in the plab for a subagent to work in the post directory wihin Quarto markdown to carry out the analysis