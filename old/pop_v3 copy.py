import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font
import openai
import threading
import os
import json
import uuid
import random
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
    
    def complete_task_in_json(self, task_identifier: str) -> bool:
        """Mark a task as completed in the JSON file. Accepts UUID, title, or index."""
        tasks = self.load_tasks()
        task_to_complete = None
        
        # Try to find task by UUID first
        for task in tasks:
            if task["id"] == task_identifier and not task["completed"]:
                task_to_complete = task
                break
        
        # If not found by UUID, try by title (partial match, case insensitive)
        if not task_to_complete:
            for task in tasks:
                if not task["completed"] and task_identifier.lower() in task["title"].lower():
                    task_to_complete = task
                    break
        
        # If still not found, try by index (1-based)
        if not task_to_complete:
            try:
                index = int(task_identifier) - 1  # Convert to 0-based
                active_tasks = [t for t in tasks if not t["completed"]]
                if 0 <= index < len(active_tasks):
                    task_to_complete = active_tasks[index]
            except ValueError:
                pass
        
        if task_to_complete:
            task_to_complete["completed"] = True
            task_to_complete["completed_at"] = datetime.now().isoformat()
            return self.save_tasks(tasks)
        
        return False
    
    def get_tasks_summary(self) -> str:
        """Get a formatted summary of current tasks with IDs for GPT"""
        tasks = self.load_tasks()
        
        if not tasks:
            return "No tasks found."
        
        active_tasks = [t for t in tasks if not t["completed"]]
        completed_tasks = [t for t in tasks if t["completed"]]
        
        summary = f"Active Tasks ({len(active_tasks)}):\n"
        for i, task in enumerate(active_tasks, 1):
            priority_indicator = "🔴" if task["priority"] == "high" else "🟡" if task["priority"] == "medium" else "🟢"
            timeline_str = f" | Due: {task['timeline']}" if task["timeline"] else ""
            # Include both display number and actual ID for GPT
            summary += f"{i}. {priority_indicator} {task['title']}{timeline_str} [ID: {task['id']}]\n"
        
        if completed_tasks:
            summary += f"\nCompleted Tasks ({len(completed_tasks)}):\n"
            for i, task in enumerate(completed_tasks[-3:], 1):  # Show last 3 completed
                summary += f"{i}. ✅ {task['title']} [ID: {task['id']}]\n"
        
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
                "description": "Mark a task as completed. Can accept task ID, task title (partial match), or task number from the list.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_identifier": {
                            "type": "string",
                            "description": "The task to complete. Can be: UUID, partial title match, or number from active task list (e.g., '1', '2')"
                        }
                    },
                    "required": ["task_identifier"]
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
                task_identifier = arguments.get("task_identifier", arguments.get("task_id", ""))
                if self.complete_task_in_json(task_identifier):
                    # Find the completed task for better feedback
                    tasks = self.load_tasks()
                    completed_task = None
                    for task in tasks:
                        if (task["id"] == task_identifier or 
                            task_identifier.lower() in task["title"].lower() or
                            task["completed"] and task["completed_at"]):
                            completed_task = task
                            break
                    
                    if completed_task:
                        return {"success": True, "message": f"Task '{completed_task['title']}' marked as completed"}
                    else:
                        return {"success": True, "message": f"Task completed successfully"}
                else:
                    return {"success": False, "message": f"Could not find active task matching '{task_identifier}'. Check task ID, title, or number."}
            
            else:
                return {"success": False, "message": f"Unknown function: {function_name}"}
                
        except Exception as e:
            return {"success": False, "message": f"Error executing {function_name}: {str(e)}"}
        
    def load_api_key(self):
        """Load API key from ../api_key.txt with professional error handling"""
        try:
            with open('../api_key.txt', 'r', encoding='utf-8') as f:
                self.api_key = f.read().strip()
                openai.api_key = self.api_key
                self.add_to_chat("✓ API key loaded successfully", "debug_message")
                self.add_welcome_message()
        except FileNotFoundError:
            self.api_key = None
            self.add_to_chat("⚠ Please create ../api_key.txt with your OpenAI API key", "debug_message")
            if hasattr(self, 'status_indicator'):
                self.status_indicator.config(fg=self.colors['error'])
        except Exception as e:
            self.api_key = None
            self.add_to_chat(f"✗ Error loading API key: {e}", "debug_message")
            if hasattr(self, 'status_indicator'):
                self.status_indicator.config(fg=self.colors['error'])
            
    def add_welcome_message(self):
        """Add professional welcome message"""
        welcome_text = """Hello! I'm NOX, your personal AI assistant.

I can help you with:
• Task management and organization
• Breaking down complex projects
• General questions and assistance

I'll automatically save tasks to a local JSON file that you can inspect. Try saying something like "Add a task to review the project documentation by tomorrow" to get started."""
        
        self.add_to_chat(welcome_text, "assistant_message")
        
    def setup_window(self):
        """Configure the main window with enterprise-grade styling"""
        self.root.title("NOX")
        self.root.geometry("520x720")
        self.root.resizable(False, False)
        
        # Professional color palette
        self.colors = {
            'bg_primary': '#0f0f0f',
            'bg_secondary': '#1a1a1a',
            'bg_tertiary': '#2a2a2a',
            'accent_primary': '#2563eb',
            'accent_hover': '#3b82f6',
            'text_primary': '#ffffff',
            'text_secondary': '#a1a1aa',
            'text_muted': '#71717a',
            'border': '#27272a',
            'success': '#10b981',
            'warning': '#f59e0b',
            'error': '#ef4444',
            'gradient_start': '#4c1d95',
            'gradient_end': '#1e40af'
        }
        
        # Create gradient background
        self.setup_gradient_background()
        
        # Configure modern font stack
        self.fonts = {
            'title': ('Segoe UI', 18, 'bold'),
            'subtitle': ('Segoe UI', 14, 'normal'),
            'body': ('Segoe UI', 11, 'normal'),
            'body_medium': ('Segoe UI', 11, 'bold'),
            'code': ('Consolas', 10, 'normal'),
            'caption': ('Segoe UI', 9, 'normal')
        }
        
        # Always on top and centered
        self.root.attributes('-topmost', True)
        self.center_window()
        
    def setup_gradient_background(self):
        """Create optimized violet-to-blue gradient background"""
        # Pre-calculate gradient colors for performance
        self.gradient_colors = self._generate_gradient_palette()
        
        # Create canvas for gradient
        self.gradient_canvas = tk.Canvas(
            self.root,
            width=520,
            height=720,
            highlightthickness=0,
            borderwidth=0
        )
        self.gradient_canvas.place(x=0, y=0)
        
        # Draw optimized gradient
        self.draw_optimized_gradient()
        
    def _generate_gradient_palette(self) -> List[str]:
        """Pre-compute gradient colors for better performance"""
        height = 720
        colors = []
        
        # Gradient endpoints
        start_r, start_g, start_b = 0x4c, 0x1d, 0x95  # Deep violet
        end_r, end_g, end_b = 0x1e, 0x40, 0xaf        # Deep blue
        
        for i in range(height):
            ratio = i / height
            
            # Linear interpolation
            r = int(start_r + (end_r - start_r) * ratio)
            g = int(start_g + (end_g - start_g) * ratio)
            b = int(start_b + (end_b - start_b) * ratio)
            
            colors.append(f"#{r:02x}{g:02x}{b:02x}")
            
        return colors
        
    def draw_optimized_gradient(self):
        """Draw gradient using optimized rectangle method"""
        self.gradient_canvas.delete("all")
        
        # Draw gradient in chunks for better performance
        chunk_size = 8
        
        for i in range(0, 720, chunk_size):
            if i < len(self.gradient_colors):
                color = self.gradient_colors[i]
                
                # Draw rectangle chunk instead of individual lines
                self.gradient_canvas.create_rectangle(
                    0, i, 520, min(i + chunk_size, 720),
                    fill=color,
                    outline=color
                )
        
        # Add subtle texture overlay
        self._add_optimized_texture()
        
    def _add_optimized_texture(self):
        """Add performance-optimized texture overlay"""
        # Pre-generate texture points
        texture_points = []
        for _ in range(100):
            x = random.randint(0, 520)
            y = random.randint(0, 720)
            texture_points.append((x, y))
        
        # Draw texture in batch
        for x, y in texture_points:
            self.gradient_canvas.create_oval(
                x, y, x+2, y+2,
                fill="#ffffff",
                outline="",
                stipple="gray12"
            )
            
    def get_blended_color(self, bg_hex: str, alpha: float, gradient_pos: float) -> str:
        """Calculate properly blended color with correct alpha math"""
        # Clamp inputs
        alpha = max(0.0, min(1.0, alpha))
        gradient_pos = max(0.0, min(1.0, gradient_pos))
        
        # Get gradient color at position
        if hasattr(self, 'gradient_colors') and self.gradient_colors:
            gradient_index = int(gradient_pos * (len(self.gradient_colors) - 1))
            gradient_color = self.gradient_colors[gradient_index]
        else:
            # Fallback if gradient not ready
            gradient_color = self.colors['gradient_start']
        
        # Parse colors safely
        try:
            # Gradient color
            grad_hex = gradient_color.lstrip('#')
            grad_r = int(grad_hex[0:2], 16)
            grad_g = int(grad_hex[2:4], 16) 
            grad_b = int(grad_hex[4:6], 16)
            
            # Background color
            bg_hex = bg_hex.lstrip('#')
            bg_r = int(bg_hex[0:2], 16)
            bg_g = int(bg_hex[2:4], 16)
            bg_b = int(bg_hex[4:6], 16)
            
            # Correct alpha blending: result = bg * alpha + gradient * (1 - alpha)
            final_r = int(bg_r * alpha + grad_r * (1.0 - alpha))
            final_g = int(bg_g * alpha + grad_g * (1.0 - alpha))
            final_b = int(bg_b * alpha + grad_b * (1.0 - alpha))
            
            # Clamp to valid range
            final_r = max(0, min(255, final_r))
            final_g = max(0, min(255, final_g))
            final_b = max(0, min(255, final_b))
            
            return f"#{final_r:02x}{final_g:02x}{final_b:02x}"
            
        except (ValueError, IndexError):
            # Fallback to solid color on parse error
            return bg_hex
        
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def setup_ui(self):
        """Create enterprise-grade UI with pre-calculated gradient-aware colors"""
        # Pre-calculate blended colors for performance
        self._cache_ui_colors()
        
        # Main container - transparent background to show gradient
        main_container = tk.Frame(self.root, bg='')
        main_container.place(x=0, y=0, width=520, height=720)
        
        # Setup UI components
        self.setup_header(main_container)
        self.setup_chat_area(main_container)
        self.setup_input_section(main_container)
        self.setup_footer(main_container)
        
    def _cache_ui_colors(self):
        """Pre-calculate UI colors for performance optimization"""
        self.ui_colors = {
            'header_bg': self.get_blended_color('#1a1a1a', 0.85, 0.15),
            'chat_bg': self.get_blended_color('#1a1a1a', 0.85, 0.50),
            'input_bg': self.get_blended_color('#2a2a2a', 0.90, 0.85),
            'footer_bg': self.get_blended_color('#2a2a2a', 0.80, 0.95)
        }
        
    def setup_header(self, parent):
        """Professional header using cached gradient-aware colors"""
        header_frame = tk.Frame(parent, bg=self.ui_colors['header_bg'], height=80)
        header_frame.pack(fill=tk.X, padx=20, pady=(20, 0))
        header_frame.pack_propagate(False)
        
        # Inner header with padding
        header_content = tk.Frame(header_frame, bg=self.ui_colors['header_bg'])
        header_content.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)
        
        # Brand section
        brand_frame = tk.Frame(header_content, bg=self.ui_colors['header_bg'])
        brand_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        # NOX logo/title
        title_label = tk.Label(
            brand_frame,
            text="NOX",
            bg=self.ui_colors['header_bg'],
            fg=self.colors['text_primary'],
            font=self.fonts['title']
        )
        title_label.pack(side=tk.LEFT, pady=(0, 2))
        
        # Subtitle
        subtitle_label = tk.Label(
            brand_frame,
            text="Personal AI Assistant",
            bg=self.ui_colors['header_bg'],
            fg=self.colors['text_muted'],
            font=self.fonts['caption']
        )
        subtitle_label.pack(side=tk.LEFT, padx=(12, 0), pady=(2, 0))
        
        # Metrics section
        metrics_frame = tk.Frame(header_content, bg=self.ui_colors['header_bg'])
        metrics_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status indicator
        self.status_indicator = tk.Label(
            metrics_frame,
            text="●",
            bg=self.ui_colors['header_bg'],
            fg=self.colors['success'],
            font=('Segoe UI', 12, 'normal')
        )
        self.status_indicator.pack(side=tk.RIGHT, padx=(8, 0))
        
        # Cost display
        self.cost_label = tk.Label(
            metrics_frame,
            text="$0.000000",
            bg=self.ui_colors['header_bg'],
            fg=self.colors['text_secondary'],
            font=self.fonts['body']
        )
        self.cost_label.pack(side=tk.RIGHT, pady=(2, 0))
        
        cost_prefix = tk.Label(
            metrics_frame,
            text="Session cost: ",
            bg=self.ui_colors['header_bg'],
            fg=self.colors['text_muted'],
            font=self.fonts['caption']
        )
        cost_prefix.pack(side=tk.RIGHT)
        
    def setup_chat_area(self, parent):
        """Chat interface using cached gradient-aware colors"""
        chat_container = tk.Frame(parent, bg='')
        chat_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Chat history with optimized styling
        self.chat_history = scrolledtext.ScrolledText(
            chat_container,
            wrap=tk.WORD,
            bg=self.ui_colors['chat_bg'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['accent_primary'],
            font=self.fonts['body'],
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=1,
            highlightcolor=self.colors['accent_primary'],
            highlightbackground=self.colors['border'],
            padx=24,
            pady=20,
            spacing1=4,
            spacing2=2,
            spacing3=8
        )
        self.chat_history.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for message styling
        self.chat_history.tag_configure(
            "user_message",
            foreground=self.colors['text_primary'],
            font=self.fonts['body_medium'],
            spacing1=6,
            spacing3=4
        )
        
        self.chat_history.tag_configure(
            "assistant_message", 
            foreground=self.colors['text_primary'],
            font=self.fonts['body'],
            spacing1=6,
            spacing3=4
        )
        
        self.chat_history.tag_configure(
            "debug_message",
            foreground=self.colors['text_muted'],
            font=self.fonts['caption'],
            spacing1=2,
            spacing3=2
        )
        
        self.chat_history.tag_configure(
            "loading_message",
            foreground=self.colors['accent_primary'],
            font=self.fonts['body'],
            spacing1=4,
            spacing3=4
        )
        
    def setup_input_section(self, parent):
        """Input area using cached gradient-aware colors"""
        input_container = tk.Frame(parent, bg='')
        input_container.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Input frame with elevated styling
        input_frame = tk.Frame(
            input_container,
            bg=self.ui_colors['input_bg'],
            relief=tk.FLAT,
            bd=1
        )
        input_frame.pack(fill=tk.X, ipady=4)
        
        # Input text area
        self.chat_input = tk.Text(
            input_frame,
            height=3,
            bg=self.ui_colors['input_bg'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['accent_primary'],
            font=self.fonts['body'],
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            padx=20,
            pady=16,
            wrap=tk.WORD
        )
        self.chat_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Send button
        button_frame = tk.Frame(input_frame, bg=self.ui_colors['input_bg'])
        button_frame.pack(side=tk.RIGHT, padx=(0, 16), pady=12)
        
        self.send_button = tk.Button(
            button_frame,
            text="Send",
            command=self.send_message,
            bg=self.colors['accent_primary'],
            fg=self.colors['text_primary'],
            font=self.fonts['body_medium'],
            relief=tk.FLAT,
            borderwidth=0,
            padx=24,
            pady=8,
            cursor='hand2'
        )
        self.send_button.pack()
        
        # Hover effects
        self.send_button.bind('<Enter>', lambda e: self.send_button.config(bg=self.colors['accent_hover']))
        self.send_button.bind('<Leave>', lambda e: self.send_button.config(bg=self.colors['accent_primary']))
        
        # Keyboard shortcuts
        self.chat_input.bind('<Return>', self.handle_enter)
        self.chat_input.bind('<Shift-Return>', lambda e: None)
        
        # Placeholder functionality
        self.setup_input_placeholder()
        
    def setup_input_placeholder(self):
        """Add placeholder text functionality to input field"""
        placeholder_text = "Message NOX..."
        
        def on_focus_in(event):
            current_text = self.chat_input.get(1.0, tk.END).strip()
            if current_text == placeholder_text:
                self.chat_input.delete(1.0, tk.END)
                self.chat_input.config(fg=self.colors['text_primary'])
        
        def on_focus_out(event):
            current_text = self.chat_input.get(1.0, tk.END).strip()
            if not current_text:
                self.chat_input.insert(1.0, placeholder_text)
                self.chat_input.config(fg=self.colors['text_muted'])
        
        # Initialize with placeholder
        self.chat_input.insert(1.0, placeholder_text)
        self.chat_input.config(fg=self.colors['text_muted'])
        
        # Bind focus events
        self.chat_input.bind('<FocusIn>', on_focus_in)
        self.chat_input.bind('<FocusOut>', on_focus_out)
        
    def setup_footer(self, parent):
        """Footer using cached gradient-aware colors"""
        footer_frame = tk.Frame(parent, bg='')
        footer_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        footer_content = tk.Frame(footer_frame, bg='')
        footer_content.pack(fill=tk.X)
        
        # Version info
        version_label = tk.Label(
            footer_content,
            text="NOX v1.0",
            bg='black',
            fg=self.colors['text_muted'],
            font=self.fonts['caption']
        )
        version_label.pack(side=tk.LEFT)
        
        # Close button
        close_button = tk.Button(
            footer_content,
            text="Close",
            command=self.close_window,
            bg=self.ui_colors['footer_bg'],
            fg=self.colors['text_secondary'],
            font=self.fonts['body'],
            relief=tk.FLAT,
            borderwidth=0,
            padx=16,
            pady=6,
            cursor='hand2'
        )
        close_button.pack(side=tk.RIGHT)
        
        # Hover effects
        close_button.bind('<Enter>', lambda e: close_button.config(bg=self.colors['error'], fg=self.colors['text_primary']))
        close_button.bind('<Leave>', lambda e: close_button.config(bg=self.ui_colors['footer_bg'], fg=self.colors['text_secondary']))
        
    def handle_enter(self, event):
        """Handle Enter key with proper placeholder text handling"""
        # Check if placeholder text is present
        current_text = self.chat_input.get(1.0, tk.END).strip()
        if current_text == "Message NOX..." or not current_text:
            return "break"
        
        if event.state & 0x1:  # Shift key held
            return  # Allow newline
        else:
            self.send_message()
            return "break"
            
    def send_message(self):
        """Handle sending chat messages with proper placeholder management"""
        current_text = self.chat_input.get(1.0, tk.END).strip()
        
        # Skip if placeholder text or empty
        if current_text == "Message NOX..." or not current_text:
            return
            
        if not self.api_key:
            self.add_to_chat("NOX: Please add your API key to ../api_key.txt", "assistant_message")
            return
            
        # Add user message
        self.add_to_chat(f"You: {current_text}", "user_message")
        
        # Clear input and restore placeholder
        self.chat_input.delete(1.0, tk.END)
        self.chat_input.insert(1.0, "Message NOX...")
        self.chat_input.config(fg=self.colors['text_muted'])
        
        # Show loading state
        self.add_to_chat("NOX: Thinking...", "loading_message")
        
        # Update button state
        self.send_button.config(
            state=tk.DISABLED, 
            text="Thinking...",
            bg=self.colors['text_muted']
        )
        
        # Update status indicator
        self.status_indicator.config(fg=self.colors['warning'])
        
        # Process message in background
        threading.Thread(
            target=self.get_gpt_response, 
            args=(current_text,), 
            daemon=True
        ).start()
        
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
            self.root.after(0, lambda: self.handle_gpt_error(str(e)))
            
    def handle_gpt_response(self, reply, function_results=None):
        """Handle GPT response with improved styling and state management"""
        # Remove loading message
        self.remove_loading_message()
        
        # Add assistant response
        self.add_to_chat(f"NOX: {reply}", "assistant_message")
        
        # Add debug information if functions were called
        if function_results:
            for result in function_results:
                if result.get("success"):
                    debug_msg = f"✓ {result.get('message', 'Function executed successfully')}"
                    self.add_to_chat(debug_msg, "debug_message")
                else:
                    debug_msg = f"✗ {result.get('message', 'Function execution failed')}"
                    self.add_to_chat(debug_msg, "debug_message")
        
        # Update cost display
        self.cost_label.config(text=f"${self.total_cost:.6f}")
        
        # Reset button state
        self.send_button.config(
            state=tk.NORMAL, 
            text="Send",
            bg=self.colors['accent_primary']
        )
        
        # Reset status indicator
        self.status_indicator.config(fg=self.colors['success'])
        
    def handle_gpt_error(self, error):
        """Handle GPT errors with proper styling"""
        # Remove loading message
        self.remove_loading_message()
        
        # Add error message
        error_msg = f"NOX: Error - {error}"
        self.add_to_chat(error_msg, "assistant_message")
        
        # Reset button state
        self.send_button.config(
            state=tk.NORMAL, 
            text="Send",
            bg=self.colors['accent_primary']
        )
        
        # Set error status
        self.status_indicator.config(fg=self.colors['error'])
        
    def remove_loading_message(self):
        """Remove the thinking/loading message from chat"""
        content = self.chat_history.get(1.0, tk.END)
        lines = content.split('\n')
        
        # Filter out loading messages
        filtered_lines = []
        for line in lines:
            if not (line.strip() == "NOX: Thinking..." or 
                   line.strip().startswith("NOX: Thinking")):
                filtered_lines.append(line)
        
        # Update chat history
        self.chat_history.delete(1.0, tk.END)
        self.chat_history.insert(1.0, '\n'.join(filtered_lines))
        
    def add_to_chat(self, message: str, tag: str = "assistant_message"):
        """Add styled message to chat history"""
        self.chat_history.insert(tk.END, message + "\n\n", tag)
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