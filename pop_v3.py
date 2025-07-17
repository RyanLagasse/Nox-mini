import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import openai
import threading
import os
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

class NOXPopup:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.setup_ui()
        self.load_api_key()
        self.total_cost = 0.00
        self.tasks_file = "tasks.json"
        self.initialize_tasks_file()
        
    def initialize_tasks_file(self):
        """Initialize tasks JSON file if it doesn't exist"""
        if not os.path.exists(self.tasks_file):
            self.save_tasks([])
            
    def load_tasks(self) -> List[Dict[str, Any]]:
        """Load tasks from JSON file"""
        try:
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading tasks: {e}")
            return []
    
    def save_tasks(self, tasks: List[Dict[str, Any]]) -> bool:
        """Save tasks to JSON file"""
        try:
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving tasks: {e}")
            return False
    
    def add_task_to_json(self, title: str, description: str = "", timeline: str = "", priority: str = "medium", notes: str = "") -> Dict[str, Any]:
        """Add a new task to the JSON file"""
        task = {
            "id": str(uuid.uuid4()),
            "title": title.strip(),
            "description": description.strip(),
            "timeline": timeline.strip(),
            "priority": priority.lower(),
            "notes": notes.strip(),
            "completed": False,
            "created_at": datetime.now().isoformat(),
            "completed_at": None
        }
        
        tasks = self.load_tasks()
        tasks.append(task)
        
        if self.save_tasks(tasks):
            return task
        else:
            raise Exception("Failed to save task to file")
    
    def complete_task_in_json(self, task_id: str) -> bool:
        """Mark a task as completed in the JSON file"""
        tasks = self.load_tasks()
        
        for task in tasks:
            if task["id"] == task_id:
                task["completed"] = True
                task["completed_at"] = datetime.now().isoformat()
                return self.save_tasks(tasks)
        
        return False
    
    def get_tasks_summary(self) -> str:
        """Get a formatted summary of current tasks"""
        tasks = self.load_tasks()
        
        if not tasks:
            return "No tasks found."
        
        active_tasks = [t for t in tasks if not t["completed"]]
        completed_tasks = [t for t in tasks if t["completed"]]
        
        summary = f"Active Tasks ({len(active_tasks)}):\n"
        for i, task in enumerate(active_tasks, 1):
            priority_indicator = "🔴" if task["priority"] == "high" else "🟡" if task["priority"] == "medium" else "🟢"
            timeline_str = f" | Due: {task['timeline']}" if task["timeline"] else ""
            summary += f"{i}. {priority_indicator} {task['title']}{timeline_str}\n"
        
        if completed_tasks:
            summary += f"\nCompleted Tasks ({len(completed_tasks)}):\n"
            for i, task in enumerate(completed_tasks[-3:], 1):  # Show last 3 completed
                summary += f"{i}. ✅ {task['title']}\n"
        
        return summary
        
    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """Define functions that GPT can call for task management"""
        return [
            {
                "name": "add_task",
                "description": "Add a new task to the user's task list",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The main title/name of the task"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of what needs to be done"
                        },
                        "timeline": {
                            "type": "string",
                            "description": "When this should be done (e.g., 'today', 'next week', '2024-01-15')"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": "Priority level of the task"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Additional notes or context about the task"
                        }
                    },
                    "required": ["title"]
                }
            },
            {
                "name": "get_tasks",
                "description": "Get the current list of tasks",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "complete_task",
                "description": "Mark a task as completed",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The unique ID of the task to complete"
                        }
                    },
                    "required": ["task_id"]
                }
            }
        ]
    
    def execute_function_call(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function call from GPT"""
        try:
            if function_name == "add_task":
                task = self.add_task_to_json(
                    title=arguments.get("title", ""),
                    description=arguments.get("description", ""),
                    timeline=arguments.get("timeline", ""),
                    priority=arguments.get("priority", "medium"),
                    notes=arguments.get("notes", "")
                )
                return {"success": True, "task": task, "message": f"Task '{task['title']}' added successfully"}
            
            elif function_name == "get_tasks":
                tasks = self.load_tasks()
                return {"success": True, "tasks": tasks, "summary": self.get_tasks_summary()}
            
            elif function_name == "complete_task":
                task_id = arguments.get("task_id")
                if self.complete_task_in_json(task_id):
                    return {"success": True, "message": f"Task {task_id} marked as completed"}
                else:
                    return {"success": False, "message": f"Task {task_id} not found"}
            
            else:
                return {"success": False, "message": f"Unknown function: {function_name}"}
                
        except Exception as e:
            return {"success": False, "message": f"Error executing {function_name}: {str(e)}"}
        
    def load_api_key(self):
        """Load API key from api_key.txt"""
        try:
            with open('../api_key.txt', 'r') as f:
                self.api_key = f.read().strip()
                openai.api_key = self.api_key
                self.add_to_chat("NOX: API key loaded successfully!")
        except FileNotFoundError:
            self.add_to_chat("NOX: Please create api_key.txt with your OpenAI API key")
            self.api_key = None
        except Exception as e:
            self.add_to_chat(f"NOX: Error loading API key: {e}")
            self.api_key = None
        
    def setup_window(self):
        """Configure the main window with clean, modern styling"""
        self.root.title("NOX Mini Assistant")
        self.root.geometry("500x600")
        self.root.resizable(False, False)
        
        # Modern color scheme
        self.colors = {
            'bg': '#1a1a1a',
            'surface': '#2d2d2d', 
            'primary': '#007acc',
            'text': '#ffffff',
            'text_secondary': '#b0b0b0',
            'accent': '#4a9eff'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # Always on top and centered
        self.root.attributes('-topmost', True)
        self.center_window()
        
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def setup_ui(self):
        """Create the main UI components"""
        # Main container
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header
        header_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = tk.Label(
            header_frame, 
            text="NOX Mini", 
            bg=self.colors['bg'], 
            fg=self.colors['text'], 
            font=('Segoe UI', 16, 'bold')
        )
        title_label.pack(side=tk.LEFT)
        
        # Cost display
        self.cost_label = tk.Label(
            header_frame, 
            text="Cost: $0.00", 
            bg=self.colors['bg'], 
            fg=self.colors['text_secondary'], 
            font=('Segoe UI', 10)
        )
        self.cost_label.pack(side=tk.RIGHT)
        
        # Chat history
        self.chat_history = scrolledtext.ScrolledText(
            main_frame, 
            wrap=tk.WORD, 
            height=20,
            bg=self.colors['surface'],
            fg=self.colors['text'],
            insertbackground=self.colors['text'],
            font=('Segoe UI', 10)
        )
        self.chat_history.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Input frame
        input_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Chat input
        self.chat_input = tk.Text(
            input_frame, 
            height=3,
            bg=self.colors['surface'],
            fg=self.colors['text'],
            insertbackground=self.colors['text'],
            font=('Segoe UI', 10)
        )
        self.chat_input.pack(fill=tk.X, side=tk.LEFT, padx=(0, 10))
        
        # Send button
        self.send_button = tk.Button(
            input_frame, 
            text="Send", 
            command=self.send_message,
            bg=self.colors['primary'],
            fg=self.colors['text'],
            font=('Segoe UI', 10),
            relief=tk.FLAT,
            padx=20
        )
        self.send_button.pack(side=tk.RIGHT)
        
        # Bind Enter key (Ctrl+Enter for new line)
        self.chat_input.bind('<Return>', self.handle_enter)
        
        # Bottom controls
        bottom_frame = tk.Frame(self.root, bg=self.colors['bg'])
        bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        close_button = tk.Button(
            bottom_frame, 
            text="Close", 
            command=self.close_window,
            bg=self.colors['surface'],
            fg=self.colors['text'],
            font=('Segoe UI', 10),
            relief=tk.FLAT,
            padx=20
        )
        close_button.pack(side=tk.RIGHT)
        
    def handle_enter(self, event):
        """Handle Enter key - send message unless Ctrl+Enter"""
        if event.state & 0x4:  # Ctrl key
            return  # Allow newline
        else:
            self.send_message()
            return "break"  # Prevent newline
            
    def send_message(self):
        """Handle sending chat messages"""
        message = self.chat_input.get(1.0, tk.END).strip()
        if not message:
            return
            
        if not self.api_key:
            self.add_to_chat("NOX: Please add your API key to api_key.txt")
            return
            
        self.add_to_chat(f"You: {message}")
        self.chat_input.delete(1.0, tk.END)
        
        # Show loading message
        self.add_to_chat("NOX: Thinking...")
        
        # Disable send button during processing
        self.send_button.config(state=tk.DISABLED, text="Thinking...")
        
        # Send to GPT in separate thread
        threading.Thread(target=self.get_gpt_response, args=(message,), daemon=True).start()
        
    def get_gpt_response(self, message):
        """Get response from GPT-4o Mini with function calling support"""
        try:
            client = openai.OpenAI(api_key=self.api_key)
            
            # Get current tasks for context
            current_tasks = self.get_tasks_summary()
            
            system_prompt = f"""You are NOX, a helpful personal assistant. You can manage tasks for the user.

Current tasks:
{current_tasks}

You have access to task management functions. Use them when:
- User asks to add a task or mentions something they need to do
- User asks about their current tasks
- User wants to mark something as complete
- User asks you to break down a complex task into smaller ones

Keep responses concise and helpful. When you use functions, explain what you did."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                tools=[{"type": "function", "function": func} for func in self.get_function_definitions()],
                tool_choice="auto",
                max_tokens=500,
                temperature=0.7
            )
            
            # Handle tool calls (modern API)
            response_message = response.choices[0].message
            function_results = []
            
            if response_message.tool_calls:
                # Execute the function call
                tool_call = response_message.tool_calls[0]  # Handle first tool call
                function_name = tool_call.function.name
                
                try:
                    function_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    self.root.after(0, lambda: self.handle_gpt_error(f"Invalid function arguments: {e}"))
                    return
                
                result = self.execute_function_call(function_name, function_args)
                function_results.append(result)
                
                # Get a follow-up response that incorporates the function result
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": response_message.content, "tool_calls": response_message.tool_calls},
                    {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)}
                ]
                
                follow_up = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    max_tokens=300,
                    temperature=0.7
                )
                
                final_reply = follow_up.choices[0].message.content
                
                # Calculate total cost for both calls
                total_input_tokens = response.usage.prompt_tokens + follow_up.usage.prompt_tokens
                total_output_tokens = response.usage.completion_tokens + follow_up.usage.completion_tokens
                
            else:
                final_reply = response_message.content
                total_input_tokens = response.usage.prompt_tokens
                total_output_tokens = response.usage.completion_tokens
            
            # Calculate cost (GPT-4o-mini pricing: $0.15 per 1M input tokens, $0.6 per 1M output tokens)
            input_cost = total_input_tokens * 0.00000015
            output_cost = total_output_tokens * 0.0000006
            total_cost = input_cost + output_cost
            
            self.total_cost += total_cost
            
            # Update UI in main thread
            self.root.after(0, lambda: self.handle_gpt_response(final_reply, function_results))
            
        except Exception as e:
            self.root.after(0, self.handle_gpt_error, str(e))
            
    def handle_gpt_response(self, reply, function_results=None):
        """Handle GPT response in main thread"""
        # Remove the "Thinking..." message
        content = self.chat_history.get(1.0, tk.END)
        if "NOX: Thinking..." in content:
            lines = content.split('\n')
            filtered_lines = [line for line in lines if line.strip() != "NOX: Thinking..."]
            self.chat_history.delete(1.0, tk.END)
            self.chat_history.insert(1.0, '\n'.join(filtered_lines))
        
        self.add_to_chat(f"NOX: {reply}")
        
        # If there were function calls, add debug info
        if function_results:
            for result in function_results:
                if result.get("success"):
                    self.add_to_chat(f"[DEBUG] Function executed successfully: {result.get('message', 'No message')}")
                else:
                    self.add_to_chat(f"[DEBUG] Function failed: {result.get('message', 'Unknown error')}")
        
        self.cost_label.config(text=f"Cost: ${self.total_cost:.6f}")
        self.send_button.config(state=tk.NORMAL, text="Send")
        
    def handle_gpt_error(self, error):
        """Handle GPT error in main thread"""
        # Remove the "Thinking..." message
        content = self.chat_history.get(1.0, tk.END)
        if "NOX: Thinking..." in content:
            lines = content.split('\n')
            filtered_lines = [line for line in lines if line.strip() != "NOX: Thinking..."]
            self.chat_history.delete(1.0, tk.END)
            self.chat_history.insert(1.0, '\n'.join(filtered_lines))
        
        self.add_to_chat(f"NOX: Error - {error}")
        self.send_button.config(state=tk.NORMAL, text="Send")
        
    def add_to_chat(self, message):
        """Add message to chat history"""
        self.chat_history.insert(tk.END, message + "\n\n")
        self.chat_history.see(tk.END)
        
    def close_window(self):
        """Close the application"""
        self.root.destroy()
        
    def show(self):
        """Show the popup window"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    # Test the popup
    popup = NOXPopup()
    popup.run()