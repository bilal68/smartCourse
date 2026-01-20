#!/usr/bin/env python3
"""Create dummy course content files in local S3 storage

Usage:
  python create_dummy_content.py                    # Create content for all predefined courses
  python create_dummy_content.py <course_id>        # Create generic content for specific course ID
  python create_dummy_content.py --all-courses      # Fetch all courses from DB and create content
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Storage path from config
STORAGE_PATH = "./storage/s3"


def create_generic_course_content(course_id: str, course_title: str = "Course"):
    """Create generic content for any course ID"""
    
    course_path = Path(STORAGE_PATH) / course_id
    course_path.mkdir(parents=True, exist_ok=True)
    
    modules_data = [
        {
            "title": "Getting Started",
            "content": f"""# Getting Started with {course_title}

Welcome to this comprehensive course! This module will introduce you to the fundamental concepts.

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
"""
        },
        {
            "title": "Core Concepts",
            "content": f"""# Core Concepts of {course_title}

Now that you've completed the introduction, let's dive into the core concepts.

## Key Topics

### Topic 1: Fundamentals
Understanding the fundamental principles is crucial for mastering this subject:
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
Throughout this module, you'll complete hands-on exercises that build practical skills.
"""
        },
        {
            "title": "Project",
            "content": f"""# {course_title} - Final Project

Congratulations on making it to the final module! Time to apply everything you've learned.

## Project Overview
Build a complete project that demonstrates your mastery of the concepts covered.

## Project Requirements
Your project should include:
1. Implementation of core concepts from Module 2
2. Best practices for code organization
3. Proper error handling and validation
4. Comprehensive documentation
5. Testing and quality assurance

## Getting Started

### Step 1: Planning
- Define your project scope and objectives
- Create a project timeline
- Identify required resources

### Step 2: Implementation
- Set up your development environment
- Implement core functionality
- Add error handling
- Write tests for your code

### Step 3: Testing and Refinement
- Run comprehensive tests
- Fix any bugs or issues
- Optimize performance

### Step 4: Documentation
- Write clear documentation
- Include usage examples

## Next Steps
After completing this course:
- Take advanced courses in related topics
- Build your own portfolio projects
- Join community forums and discussions

Congratulations on completing {course_title}!
"""
        }
    ]
    
    # Create module content
    for idx, module_data in enumerate(modules_data):
        module_path = course_path / f"module_{idx + 1}"
        module_path.mkdir(exist_ok=True)
        
        # Save content as markdown
        with open(module_path / "content.md", "w") as f:
            f.write(module_data["content"])
        
        # Save metadata
        with open(module_path / "metadata.json", "w") as f:
            json.dump({
                "title": module_data["title"],
                "order": idx + 1,
                "content_length": len(module_data["content"])
            }, f, indent=2)
    
    # Save course metadata
    with open(course_path / "metadata.json", "w") as f:
        json.dump({
            "course_id": course_id,
            "title": course_title,
            "modules_count": len(modules_data)
        }, f, indent=2)
    
    return course_path, len(modules_data)


def create_dummy_content():
    """Create dummy content files for seeded courses"""
    
    # Create storage directory if it doesn't exist
    os.makedirs(STORAGE_PATH, exist_ok=True)
    
    # Course content structure
    courses_content = {
        "python-basics": {
            "title": "Python Basics",
            "modules": [
                {
                    "title": "Getting Started",
                    "content": """# Getting Started with Python

Python is a high-level, interpreted programming language known for its simplicity and readability.
It was created by Guido van Rossum and first released in 1991.

## Why Python?
- Easy to learn and read
- Versatile - web development, data science, AI, automation
- Large community and extensive libraries
- Great for beginners and professionals

## Installing Python
Python can be downloaded from python.org. Make sure to add it to your PATH during installation.

## Your First Program
```python
print("Hello, World!")
```

This simple program demonstrates how to output text in Python.
The print() function is one of the most commonly used functions for displaying output.
"""
                },
                {
                    "title": "Core Concepts",
                    "content": """# Python Core Concepts

## Variables and Data Types
Python supports various data types:
- int: Integer numbers (1, 2, -5)
- float: Decimal numbers (3.14, 2.5)
- str: Text strings ("Hello", 'World')
- bool: Boolean values (True, False)
- list: Ordered collection [1, 2, 3]
- dict: Key-value pairs {"name": "John", "age": 30}

## Control Flow
### If Statements
```python
if age >= 18:
    print("You are an adult")
elif age >= 13:
    print("You are a teenager")
else:
    print("You are a child")
```

### Loops
```python
for i in range(5):
    print(i)  # Prints 0 to 4

while count < 10:
    print(count)
    count += 1
```

## Functions
```python
def greet(name):
    return f"Hello, {name}!"

result = greet("Alice")
print(result)  # Output: Hello, Alice!
```

## Error Handling
```python
try:
    x = 10 / 0
except ZeroDivisionError:
    print("Cannot divide by zero!")
finally:
    print("This always runs")
```
"""
                },
                {
                    "title": "Project",
                    "content": """# Python Basics Project

## Calculator Program
Build a simple calculator that can perform addition, subtraction, multiplication, and division.

### Requirements:
1. Create a function for each operation
2. Handle division by zero
3. Accept user input
4. Display results clearly

### Sample Code:
```python
def add(x, y):
    return x + y

def subtract(x, y):
    return x - y

def multiply(x, y):
    return x * y

def divide(x, y):
    if y == 0:
        return "Error: Division by zero"
    return x / y

# Main program
while True:
    print("\\nSimple Calculator")
    print("1. Add")
    print("2. Subtract")
    print("3. Multiply")
    print("4. Divide")
    print("5. Exit")
    
    choice = input("Enter choice: ")
    
    if choice == '5':
        break
    
    x = float(input("Enter first number: "))
    y = float(input("Enter second number: "))
    
    if choice == '1':
        print(f"{x} + {y} = {add(x, y)}")
    elif choice == '2':
        print(f"{x} - {y} = {subtract(x, y)}")
    elif choice == '3':
        print(f"{x} * {y} = {multiply(x, y)}")
    elif choice == '4':
        print(f"{x} / {y} = {divide(x, y)}")
```

### Challenge Extensions:
- Add more operations (modulo, power)
- Save calculation history
- Create a GUI using tkinter
- Implement memory functions (M+, M-, MR)
"""
                }
            ]
        },
        "machine-learning": {
            "title": "Introduction to Machine Learning",
            "modules": [
                {
                    "title": "Getting Started",
                    "content": """# Introduction to Machine Learning

Machine Learning is a subset of Artificial Intelligence that enables systems to learn and improve from experience without being explicitly programmed.

## Types of Machine Learning
1. **Supervised Learning**: Model learns from labeled data
   - Classification: Predicting categories (spam/not spam)
   - Regression: Predicting continuous values (house prices)

2. **Unsupervised Learning**: Model learns from unlabeled data
   - Clustering: Grouping similar items
   - Dimensionality Reduction: Finding patterns

3. **Reinforcement Learning**: Agent learns through interaction
   - Reward-based learning
   - Used in games and robotics

## The Machine Learning Pipeline
1. Data Collection
2. Data Preprocessing
3. Feature Engineering
4. Model Selection
5. Training
6. Evaluation
7. Deployment

## Common ML Algorithms
- Linear Regression
- Logistic Regression
- Decision Trees
- Random Forest
- Support Vector Machines (SVM)
- K-Means Clustering
- Neural Networks
"""
                },
                {
                    "title": "Core Concepts",
                    "content": """# ML Core Concepts

## Supervised Learning - Classification

Classification is the task of predicting which of several categories an example belongs to.

### Example: Email Spam Detection
- Input: Email content
- Output: Spam or Not Spam
- Training: Show model many emails labeled as spam or not

### Common Algorithms:
- Logistic Regression
- Decision Trees
- Random Forests
- Support Vector Machines

## Supervised Learning - Regression

Regression predicts a continuous numerical value.

### Example: House Price Prediction
- Input: Square footage, bedrooms, location
- Output: Predicted price
- Data: Historical house sales

## Evaluation Metrics

### For Classification:
- Accuracy: (TP + TN) / Total
- Precision: TP / (TP + FP)
- Recall: TP / (TP + FN)
- F1-Score: Harmonic mean of precision and recall

### For Regression:
- Mean Absolute Error (MAE)
- Mean Squared Error (MSE)
- Root Mean Squared Error (RMSE)
- R-squared (R²)

## Overfitting and Underfitting

**Overfitting**: Model performs well on training data but poorly on new data
- Solution: Use regularization, more training data, simpler model

**Underfitting**: Model performs poorly on both training and new data
- Solution: Use more complex model, add features, train longer
"""
                },
                {
                    "title": "Project",
                    "content": """# ML Project: Iris Classification

## Dataset
The Iris dataset contains measurements of iris flowers and their species.
- 150 samples
- 4 features: sepal length, sepal width, petal length, petal width
- 3 classes: setosa, versicolor, virginica

## Objective
Build a classifier to predict iris species from measurements.

## Implementation Steps

### 1. Load Data
```python
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

iris = load_iris()
X = iris.data
y = iris.target
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
```

### 2. Choose and Train Model
```python
from sklearn.ensemble import RandomForestClassifier

model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)
```

### 3. Evaluate
```python
from sklearn.metrics import accuracy_score, classification_report

y_pred = model.predict(X_test)
print(f"Accuracy: {accuracy_score(y_test, y_pred)}")
print(classification_report(y_test, y_pred))
```

### 4. Make Predictions
```python
new_sample = [[5.1, 3.5, 1.4, 0.2]]
prediction = model.predict(new_sample)
print(f"Predicted species: {iris.target_names[prediction[0]]}")
```

## Expected Results
- Accuracy: 95-100% on test set
- All three species classified with high precision and recall
"""
                }
            ]
        },
        "fastapi-intro": {
            "title": "FastAPI Introduction",
            "modules": [
                {
                    "title": "Getting Started",
                    "content": """# FastAPI Introduction

FastAPI is a modern, fast web framework for building APIs with Python 3.7+.

## Key Features
- **Fast**: Very high performance, comparable to Node.js and Go
- **Fast to code**: 2-3x faster development
- **Fewer bugs**: About 40% fewer bugs
- **Intuitive**: Great editor support with autocomplete
- **Easy**: Designed to be easy to use and learn
- **Standards-based**: Based on OpenAPI and JSON Schema

## Installation
```bash
pip install fastapi uvicorn
```

## Your First API
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
```

Run with:
```bash
uvicorn main:app --reload
```

## Documentation
FastAPI automatically generates interactive API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
"""
                },
                {
                    "title": "Core Concepts",
                    "content": """# FastAPI Core Concepts

## Path Parameters
```python
@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"user_id": user_id}
```

## Query Parameters
```python
@app.get("/items/")
def list_items(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}
```

## Request Body
```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool = None

@app.post("/items/")
def create_item(item: Item):
    return item
```

## HTTP Methods
```python
@app.get("/items/{item_id}")
def read_item(item_id: int):
    pass

@app.post("/items/")
def create_item(item: Item):
    pass

@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    pass

@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    pass
```

## Dependency Injection
```python
from fastapi import Depends

async def get_query(skip: int = 0, limit: int = 100):
    return {"skip": skip, "limit": limit}

@app.get("/items/")
async def list_items(common: dict = Depends(get_query)):
    return common
```

## Error Handling
```python
from fastapi import HTTPException

@app.get("/items/{item_id}")
def read_item(item_id: int):
    if item_id < 0:
        raise HTTPException(status_code=400, detail="Invalid item ID")
    return {"item_id": item_id}
```
"""
                },
                {
                    "title": "Project",
                    "content": """# FastAPI Project: Todo API

## Overview
Build a complete TODO API with CRUD operations.

## Features
- Create todos
- Read all todos or a specific todo
- Update todos
- Delete todos
- Mark todos as complete

## Implementation

### 1. Define Models
```python
from pydantic import BaseModel
from typing import Optional

class TodoBase(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False

class Todo(TodoBase):
    id: int
```

### 2. In-Memory Database
```python
todos_db = {}
next_id = 1
```

### 3. Create Endpoints
```python
@app.post("/todos/", response_model=Todo)
def create_todo(todo: TodoBase):
    global next_id
    todos_db[next_id] = {**todo.dict(), "id": next_id}
    next_id += 1
    return todos_db[next_id - 1]

@app.get("/todos/")
def list_todos():
    return list(todos_db.values())

@app.get("/todos/{todo_id}", response_model=Todo)
def get_todo(todo_id: int):
    if todo_id not in todos_db:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todos_db[todo_id]

@app.put("/todos/{todo_id}", response_model=Todo)
def update_todo(todo_id: int, todo: TodoBase):
    if todo_id not in todos_db:
        raise HTTPException(status_code=404, detail="Todo not found")
    todos_db[todo_id].update(todo.dict())
    return todos_db[todo_id]

@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int):
    if todo_id not in todos_db:
        raise HTTPException(status_code=404, detail="Todo not found")
    del todos_db[todo_id]
    return {"deleted": todo_id}
```

## Testing
Use the built-in docs at /docs to test all endpoints!

## Next Steps
- Add database (PostgreSQL)
- Add authentication
- Add tests
- Deploy to production
"""
                }
            ]
        }
    }
    
    # Create course content directories and files
    for course_slug, course_data in courses_content.items():
        course_path = Path(STORAGE_PATH) / course_slug
        course_path.mkdir(exist_ok=True)
        
        # Save course metadata
        metadata = {
            "title": course_data["title"],
            "modules_count": len(course_data["modules"])
        }
        with open(course_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Save module content
        for idx, module in enumerate(course_data["modules"]):
            module_path = course_path / f"module_{idx + 1}"
            module_path.mkdir(exist_ok=True)
            
            # Save as markdown file
            with open(module_path / "content.md", "w") as f:
                f.write(module["content"])
            
            # Save metadata
            module_meta = {
                "title": module["title"],
                "order": idx + 1,
                "content_length": len(module["content"])
            }
            with open(module_path / "metadata.json", "w") as f:
                json.dump(module_meta, f, indent=2)
        
        print(f"✅ Created content for: {course_data['title']}")
        print(f"   - Location: {course_path}")
        print(f"   - Modules: {len(course_data['modules'])}")


def main():
    parser = argparse.ArgumentParser(
        description="Create dummy course content in local S3 storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create content for all predefined courses
  python create_dummy_content.py
  
  # Create generic content for a specific course ID
  python create_dummy_content.py 7efb7678-731a-4349-8766-64b410cdf75d
  
  # Create content for a course with custom title
  python create_dummy_content.py 7efb7678-731a-4349-8766-64b410cdf75d --title "Advanced Python"
  
  # Fetch courses from database and create content
  python create_dummy_content.py --all-courses
        """
    )
    parser.add_argument('course_id', nargs='?', help='Course ID to create content for')
    parser.add_argument('--title', help='Course title (for custom course ID)')
    parser.add_argument('--all-courses', action='store_true', help='Create content for all courses in database')
    
    args = parser.parse_args()
    
    if args.all_courses:
        # Fetch all courses from database
        try:
            os.environ.setdefault('PYTHONPATH', os.getcwd())
            from app.db.session import SessionLocal
            from app.modules.courses.models import Course
            
            db = SessionLocal()
            try:
                courses = db.query(Course).all()
                print(f"Found {len(courses)} courses in database")
                
                for course in courses:
                    course_path, module_count = create_generic_course_content(
                        str(course.id), 
                        course.title
                    )
                    print(f"✅ Created content for: {course.title}")
                    print(f"   - ID: {course.id}")
                    print(f"   - Location: {course_path}")
                    print(f"   - Modules: {module_count}")
                
                print(f"\n✅ All course content created successfully!")
                print(f"📁 Storage location: {STORAGE_PATH}")
            finally:
                db.close()
        except Exception as e:
            print(f"❌ Error fetching courses from database: {e}")
            print("   Make sure you're in the LMS directory and database is accessible")
            sys.exit(1)
            
    elif args.course_id:
        # Create content for specific course ID
        course_title = args.title or "Course"
        course_path, module_count = create_generic_course_content(args.course_id, course_title)
        print(f"✅ Created content for: {course_title}")
        print(f"   - ID: {args.course_id}")
        print(f"   - Location: {course_path}")
        print(f"   - Modules: {module_count}")
        print(f"\n📁 Storage location: {STORAGE_PATH}")
    else:
        # Create predefined course content
        create_dummy_content()
        print("\n✅ All predefined course content created successfully!")
        print(f"📁 Storage location: {STORAGE_PATH}")


if __name__ == "__main__":
    main()
