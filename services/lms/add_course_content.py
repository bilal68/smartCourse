#!/usr/bin/env python3
"""Add dummy content for a specific course"""

import os
import json
from pathlib import Path

COURSE_ID = "7efb7678-731a-4349-8766-64b410cdf75d"
STORAGE_PATH = "./storage/s3"

# Create course directory
course_path = Path(STORAGE_PATH) / COURSE_ID
course_path.mkdir(parents=True, exist_ok=True)

# Module 1: Getting Started
module1_path = course_path / "module_1"
module1_path.mkdir(exist_ok=True)

with open(module1_path / "content.md", "w") as f:
    f.write("""# Getting Started with the Course

Welcome to this comprehensive course! This module will introduce you to the fundamental concepts and set you up for success.

## What You'll Learn
- Core principles and foundational knowledge
- Best practices and industry standards
- Hands-on exercises and practical applications
- Real-world examples and case studies

## Prerequisites
No prior experience required! We'll start from the basics and build up your knowledge step by step.

## Course Structure
This course is divided into three main modules:
1. Getting Started (this module)
2. Core Concepts
3. Final Project

Let's begin your learning journey!
""")

with open(module1_path / "metadata.json", "w") as f:
    json.dump({"title": "Getting Started", "order": 1}, f, indent=2)

# Module 2: Core Concepts  
module2_path = course_path / "module_2"
module2_path.mkdir(exist_ok=True)

with open(module2_path / "content.md", "w") as f:
    f.write("""# Core Concepts

Now that you've completed the introduction, let's dive into the core concepts that form the foundation of this subject.

## Key Topics

### Topic 1: Fundamentals
Understanding the fundamental principles is crucial for mastering this subject. We'll explore:
- Basic terminology and definitions
- Important frameworks and methodologies
- Common patterns and anti-patterns

### Topic 2: Intermediate Techniques
Once you grasp the basics, we'll move on to more advanced techniques:
- Optimization strategies
- Best practices for production environments
- Performance considerations

### Topic 3: Advanced Patterns
Finally, we'll cover some advanced patterns used by industry experts:
- Design patterns and architecture
- Scalability and maintainability
- Testing and debugging strategies

## Practical Exercises
Throughout this module, you'll complete hands-on exercises that reinforce your learning and build practical skills.

## Summary
By the end of this module, you'll have a solid understanding of the core concepts and be ready to tackle real-world challenges.
""")

with open(module2_path / "metadata.json", "w") as f:
    json.dump({"title": "Core Concepts", "order": 2}, f, indent=2)

# Module 3: Project
module3_path = course_path / "module_3"
module3_path.mkdir(exist_ok=True)

with open(module3_path / "content.md", "w") as f:
    f.write("""# Final Project

Congratulations on making it to the final module! It's time to apply everything you've learned in a comprehensive project.

## Project Overview
In this module, you'll build a complete project from scratch that demonstrates your mastery of the concepts covered in this course.

## Project Requirements
Your project should include:
1. Implementation of core concepts from Module 2
2. Best practices for code organization and structure
3. Proper error handling and validation
4. Comprehensive documentation
5. Testing and quality assurance

## Getting Started
Follow these steps to complete your project:

### Step 1: Planning
- Define your project scope and objectives
- Create a project timeline
- Identify required resources and dependencies

### Step 2: Implementation
- Set up your development environment
- Implement core functionality
- Add error handling and validation
- Write tests for your code

### Step 3: Testing and Refinement
- Run comprehensive tests
- Fix any bugs or issues
- Optimize performance
- Refactor code for clarity

### Step 4: Documentation
- Write clear documentation
- Include usage examples
- Document any assumptions or limitations

## Project Submission
Once you've completed your project:
1. Review the requirements checklist
2. Test all functionality
3. Submit your project for evaluation

## Next Steps
After completing this course, consider:
- Advanced courses in related topics
- Contributing to open-source projects
- Building your own portfolio projects
- Joining community forums and discussions

Congratulations on completing the course! You now have the skills and knowledge to tackle real-world challenges in this field.
""")

with open(module3_path / "metadata.json", "w") as f:
    json.dump({"title": "Project", "order": 3}, f, indent=2)

# Course metadata
with open(course_path / "metadata.json", "w") as f:
    json.dump({
        "course_id": COURSE_ID,
        "modules_count": 3,
        "total_content_files": 3
    }, f, indent=2)

print(f"✅ Created dummy content for course: {COURSE_ID}")
print(f"   Location: {course_path}")
print(f"   Modules: 3")
print(f"   Files created: 3 content files + metadata")
