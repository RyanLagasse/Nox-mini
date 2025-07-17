import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import openai
import threading
import os

class NOXPopup:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.setup_ui()
        self.load_api_key()
        self.total_cost = 0.00
        
    def load_api_key(self):
        """Load API key from api_key.txt"""
        try:
            with open('api_key.txt', 'r') as f:
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
        
        # Disable send button during processing
        self.send_button.config(state=tk.DISABLED, text="Thinking...")
        
        # Send to GPT in separate thread
        threading.Thread(target=self.get_gpt_response, args=(message,), daemon=True).start()
        
    def get_gpt_response(self, message):
        """Get response from GPT-4o Mini"""
        try:
            client = openai.OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are NOX, a helpful personal assistant. Keep responses concise and helpful."},
                    {"role": "user", "content": message}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            reply = response.choices[0].message.content
            
            # Calculate cost (rough estimate for gpt-4o-mini)
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            # GPT-4o-mini pricing (approximate)
            input_cost = input_tokens * 0.00015 / 1000  # $0.15 per 1K tokens
            output_cost = output_tokens * 0.0006 / 1000  # $0.6 per 1K tokens
            total_cost = input_cost + output_cost
            
            self.total_cost += total_cost
            
            # Update UI in main thread
            self.root.after(0, self.handle_gpt_response, reply)
            
        except Exception as e:
            self.root.after(0, self.handle_gpt_error, str(e))
            
    def handle_gpt_response(self, reply):
        """Handle GPT response in main thread"""
        self.add_to_chat(f"NOX: {reply}")
        self.cost_label.config(text=f"Cost: ${self.total_cost:.4f}")
        self.send_button.config(state=tk.NORMAL, text="Send")
        
    def handle_gpt_error(self, error):
        """Handle GPT error in main thread"""
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