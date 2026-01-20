#!/usr/bin/env python3
"""Create dummy course content files in local S3 storage"""

import os
import json
from pathlib import Path

# Storage path from config
STORAGE_PATH = "./storage/s3"

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

if __name__ == "__main__":
    create_dummy_content()
    print("\n✅ All course content created successfully!")
    print(f"📁 Storage location: {STORAGE_PATH}")
