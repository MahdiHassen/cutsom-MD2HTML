import re
import json
import os
import markdown
import tkinter as tk
from tkinter import filedialog, messagebox
import tkinter.font as tkfont

# Use ttkbootstrap for a modern UI.
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# Import tkhtmlview for rendered HTML.
from tkhtmlview import HTMLLabel


class CustomMD2HTML:
    def __init__(self, root):
        self.root = root
        self.root.title("CustomMD2HTML")
        self.root.geometry("900x800")
        
        # Configuration file path.
        self.config_file = "md_converter_config.json"
        # Currently loaded Markdown file.
        self.current_md_filepath = None
        # Document name (default "Untitled")
        self.document_name = "Untitled"
        
        # Default style mappings. Note new keys: "p" and "blockquote".
        self.style_mapping = {
            "bold": "strong",
            "italic": "em",
            "code": "code",
            "h1": "h1",
            "h2": "h2",
            "h3": "h3",
            "h4": "h4",
            "h5": "h5",
            "h6": "h6",
            "br": "br",
            "p": "p",
            "blockquote": "blockquote"
        }
        # Fixed font settings.
        self.font_family = "Segoe UI"
        self.font_size = 14
        self.text_font = tkfont.Font(family=self.font_family, size=self.font_size)
        
        # Control variables.
        self.live_preview = tk.BooleanVar(value=False)
        self.render_preview = tk.BooleanVar(value=True)
        
        # Load configuration.
        self.load_config()
        
        # Create Notebook.
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)
        
        self.create_editor_tab()
        self.create_settings_tab()
        
        # Global key bindings for Markdown file operations.
        self.root.bind("<Control-s>", self.save_markdown)
        self.root.bind("<Control-o>", self.open_markdown)
    
    def create_editor_tab(self):
        # Create the Editor tab.
        self.editor_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.editor_frame, text="Editor")
        
        # Vertical PanedWindow: top = Markdown editor, bottom = preview area.
        self.main_paned = ttk.PanedWindow(self.editor_frame, orient="vertical")
        self.main_paned.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Top pane: Markdown editor area.
        self.editor_area_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.editor_area_frame, weight=3)
        
        # Label shows the document name.
        self.md_label = ttk.Label(self.editor_area_frame, text=self.document_name)
        self.md_label.pack(anchor="w", pady=(5, 0))
        
        self.md_text = tk.Text(self.editor_area_frame, wrap="word", undo=True,
                                font=self.text_font, relief="flat", borderwidth=0, background="white")
        self.md_text.bind("<Control-z>", self.undo_action)
        self.md_text.bind("<Control-Z>", self.undo_action)
        self.md_text.bind("<Control-Shift-z>", self.redo_action)
        self.md_text.bind("<Control-Shift-Z>", self.redo_action)
        self.md_text.pack(expand=True, fill="both", pady=10)
        
        # Bottom pane: Contains controls and preview area.
        self.preview_area_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.preview_area_frame, weight=2)
        
        # Controls frame.
        self.controls_frame = ttk.Frame(self.preview_area_frame)
        self.controls_frame.pack(fill="x", pady=5)
        
        self.convert_button = ttk.Button(self.controls_frame, text="Convert to HTML",
                                         command=self.convert_to_html, bootstyle=PRIMARY)
        self.convert_button.pack(side="left", padx=5)
        
        self.save_html_button = ttk.Button(self.controls_frame, text="Save HTML",
                                           command=self.save_html, bootstyle=SUCCESS)
        self.save_html_button.pack(side="left", padx=5)
        
        self.live_preview_checkbox = ttk.Checkbutton(self.controls_frame, text="Live HTML Preview",
                                                       variable=self.live_preview, command=self.toggle_live_preview)
        self.live_preview_checkbox.pack(side="left", padx=5)
        
        self.render_preview_checkbox = ttk.Checkbutton(self.controls_frame, text="Rendered Preview",
                                                         variable=self.render_preview, command=self.convert_to_html)
        self.render_preview_checkbox.pack(side="left", padx=5)
        
        # Preview container frame.
        self.preview_container_frame = ttk.Frame(self.preview_area_frame)
        self.preview_container_frame.pack(expand=True, fill="both", padx=10, pady=(5, 10))
        
        # Create a dedicated preview area (persistent container).
        self.preview_area = ttk.Frame(self.preview_container_frame)
        self.preview_area.pack(expand=True, fill="both")
        
        # Create preview widgets as children of preview_area.
        self.html_text = tk.Text(self.preview_area, wrap="word",
                                 font=self.text_font, relief="flat", borderwidth=0, background="#f8f8f8")
        self.html_view = HTMLLabel(self.preview_area, html="", background="#f8f8f8", font=self.text_font)
        
        if self.live_preview.get():
            self.md_text.bind("<KeyRelease>", self.on_key_release)
        self.update_editor_mode()
    
    def create_settings_tab(self):
        # Settings tab for style mappings and font size.
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")
        pad = {"padx": 5, "pady": 5}
        row = 0
        
        ttk.Label(self.settings_frame, text="Bold Tag (for **text**):").grid(row=row, column=0, sticky="w", **pad)
        self.bold_entry = ttk.Entry(self.settings_frame)
        self.bold_entry.grid(row=row, column=1, **pad)
        self.bold_entry.insert(0, self.style_mapping.get("bold", "strong"))
        row += 1
        
        ttk.Label(self.settings_frame, text="Italic Tag (for *text*):").grid(row=row, column=0, sticky="w", **pad)
        self.italic_entry = ttk.Entry(self.settings_frame)
        self.italic_entry.grid(row=row, column=1, **pad)
        self.italic_entry.insert(0, self.style_mapping.get("italic", "em"))
        row += 1
        
        ttk.Label(self.settings_frame, text="Code Tag (for `text`):").grid(row=row, column=0, sticky="w", **pad)
        self.code_entry = ttk.Entry(self.settings_frame)
        self.code_entry.grid(row=row, column=1, **pad)
        self.code_entry.insert(0, self.style_mapping.get("code", "code"))
        row += 1
        
        ttk.Label(self.settings_frame, text="Line Break Tag (for <br>):").grid(row=row, column=0, sticky="w", **pad)
        self.br_entry = ttk.Entry(self.settings_frame)
        self.br_entry.grid(row=row, column=1, **pad)
        self.br_entry.insert(0, self.style_mapping.get("br", "br"))
        row += 1
        
        # Headings H1 to H6.
        self.heading_entries = {}
        for i in range(1, 7):
            ttk.Label(self.settings_frame, text=f"H{i} Tag (for {'#'*i} heading):").grid(row=row, column=0, sticky="w", **pad)
            entry = ttk.Entry(self.settings_frame)
            entry.grid(row=row, column=1, **pad)
            entry.insert(0, self.style_mapping.get(f"h{i}", f"h{i}"))
            self.heading_entries[f"h{i}"] = entry
            row += 1
        
        # New: Paragraph tag.
        ttk.Label(self.settings_frame, text="Paragraph Tag (for <p>):").grid(row=row, column=0, sticky="w", **pad)
        self.p_entry = ttk.Entry(self.settings_frame)
        self.p_entry.grid(row=row, column=1, **pad)
        self.p_entry.insert(0, self.style_mapping.get("p", "p"))
        row += 1
        
        # New: Block Quote tag.
        ttk.Label(self.settings_frame, text="Block Quote Tag (for <blockquote>):").grid(row=row, column=0, sticky="w", **pad)
        self.blockquote_entry = ttk.Entry(self.settings_frame)
        self.blockquote_entry.grid(row=row, column=1, **pad)
        self.blockquote_entry.insert(0, self.style_mapping.get("blockquote", "blockquote"))
        row += 1
        
        # Only Font Size is adjustable.
        ttk.Label(self.settings_frame, text="Font Size (Editor & Preview):").grid(row=row, column=0, sticky="w", **pad)
        self.font_size_entry = ttk.Entry(self.settings_frame)
        self.font_size_entry.grid(row=row, column=1, **pad)
        self.font_size_entry.insert(0, str(self.font_size))
        row += 1
        
        self.save_settings_button = ttk.Button(self.settings_frame, text="Save Settings",
                                               command=self.save_settings, bootstyle=INFO)
        self.save_settings_button.grid(row=row, column=0, columnspan=2, pady=10)
        # Bind CTRL+S in the settings tab to save settings.
        self.settings_frame.bind("<Control-s>", lambda event: self.save_settings())
    
    def toggle_live_preview(self):
        if self.live_preview.get():
            self.md_text.bind("<KeyRelease>", self.on_key_release)
        else:
            self.md_text.unbind("<KeyRelease>")
        self.update_editor_mode()
        self.convert_to_html()
    
    def update_editor_mode(self):
        # Remove any existing grid placements from preview_area.
        self.html_text.grid_forget()
        self.html_view.grid_forget()
        
        # In live preview mode, grid both preview widgets side-by-side (resizable).
        if self.live_preview.get():
            self.html_text.grid(row=0, column=0, sticky="nsew")
            self.html_view.grid(row=0, column=1, sticky="nsew")
            self.preview_area.columnconfigure(0, weight=1)
            self.preview_area.columnconfigure(1, weight=1)
        else:
            # In single preview mode, grid only one widget.
            if self.render_preview.get():
                self.html_view.grid(row=0, column=0, sticky="nsew")
            else:
                self.html_text.grid(row=0, column=0, sticky="nsew")
            self.preview_area.columnconfigure(0, weight=1)
    
    def on_key_release(self, event):
        self.convert_to_html()
    
    def undo_action(self, event):
        try:
            self.md_text.edit_undo()
        except tk.TclError:
            pass
        return "break"
    
    def redo_action(self, event):
        try:
            self.md_text.edit_redo()
        except tk.TclError:
            pass
        return "break"
    
    def convert_to_html(self):
        md_content = self.md_text.get("1.0", "end-1c")
        md_content = md_content.replace("\t>", "    >")
        try:
            html_content = markdown.markdown(md_content, extensions=['extra', 'nl2br'])
        except Exception as e:
            messagebox.showerror("Conversion Error", f"Error during markdown conversion:\n{e}")
            return
        html_content = self.post_process_html(html_content)
        if self.live_preview.get():
            self.html_text.delete("1.0", "end")
            self.html_text.insert("1.0", html_content)
            self.html_view.set_html(html_content)
            self.html_view.fit_height()
        else:
            if self.render_preview.get():
                self.html_view.set_html(html_content)
                self.html_view.fit_height()
            else:
                self.html_text.delete("1.0", "end")
                self.html_text.insert("1.0", html_content)
    
    def post_process_html(self, html):
        # Replace bold, italic, code as before.
        bold_tag = self.style_mapping.get("bold", "strong")
        html = html.replace("<strong>", f"<{bold_tag}>").replace("</strong>", f"</{bold_tag}>")
        italic_tag = self.style_mapping.get("italic", "em")
        html = html.replace("<em>", f"<{italic_tag}>").replace("</em>", f"</{italic_tag}>")
        code_tag = self.style_mapping.get("code", "code")
        html = html.replace("<code>", f"<{code_tag}>").replace("</code>", f"</{code_tag}>")
        for i in range(1, 7):
            default_tag = f"h{i}"
            custom_tag = self.style_mapping.get(f"h{i}", default_tag)
            html = re.sub(rf"<{default_tag}(\s*[^>]*)>", rf"<{custom_tag}\1>", html)
            html = re.sub(rf"</{default_tag}>", rf"</{custom_tag}>", html)
        br_tag = self.style_mapping.get("br", "br")
        html = re.sub(r'<br\s*/?>', f"<{br_tag}>", html)
        
        # New: Replace <p> and </p> with custom tag.
        custom_p = self.style_mapping.get("p", "p")
        p_tag_name = custom_p.split()[0]
        html = re.sub(r"<p(\s*[^>]*)>", rf"<{custom_p}\1>", html)
        html = re.sub(r"</p>", rf"</{p_tag_name}>", html)
        
        # New: Replace <blockquote> and </blockquote> with custom tag.
        custom_bq = self.style_mapping.get("blockquote", "blockquote")
        bq_tag_name = custom_bq.split()[0]
        html = re.sub(r"<blockquote(\s*[^>]*)>", rf"<{custom_bq}\1>", html)
        html = re.sub(r"</blockquote>", rf"</{bq_tag_name}>", html)
        
        return html
    
    def save_html(self):
        if self.current_md_filepath:
            base = os.path.basename(self.current_md_filepath)
            default_name = os.path.splitext(base)[0] + ".html"
        else:
            default_name = "untitled.html"
        file_path = filedialog.asksaveasfilename(initialfile=default_name,
                                                 defaultextension=".html",
                                                 filetypes=[("HTML files", "*.html"), ("All files", "*.*")])
        if file_path:
            try:
                if self.live_preview.get():
                    html_content = self.html_text.get("1.0", "end-1c")
                else:
                    if self.render_preview.get():
                        html_content = self.html_view.html
                    else:
                        html_content = self.html_text.get("1.0", "end-1c")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                messagebox.showinfo("Saved", "HTML file saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Error saving HTML file:\n{e}")
    
    def save_markdown(self, event=None):
        # If no file is set or the file doesn't exist, prompt for Save As.
        if self.current_md_filepath is None or not os.path.exists(self.current_md_filepath):
            new_path = filedialog.asksaveasfilename(defaultextension=".md",
                                                    filetypes=[("Markdown files", "*.md"), ("All files", "*.*")])
            if not new_path:
                return "break"
            self.current_md_filepath = new_path
        try:
            with open(self.current_md_filepath, "w", encoding="utf-8") as f:
                f.write(self.md_text.get("1.0", "end-1c"))
            self.document_name = os.path.basename(self.current_md_filepath)
            self.md_label.config(text=self.document_name)
        except Exception as e:
            messagebox.showerror("Error", f"Error saving Markdown file:\n{e}")
        return "break"
    
    def open_markdown(self, event=None):
        file_path = filedialog.askopenfilename(defaultextension=".md",
                                               filetypes=[("Markdown files", "*.md"), ("All files", "*.*")])
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.md_text.delete("1.0", "end")
                self.md_text.insert("1.0", content)
                self.current_md_filepath = file_path
                self.document_name = os.path.basename(file_path)
                self.md_label.config(text=self.document_name)
                self.convert_to_html()
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {e}")
        return "break"
    
    def load_config(self):
        if not os.path.exists(self.config_file):
            default_config = {
                "style_mapping": {
                    "bold": "strong",
                    "italic": "em",
                    "code": "code",
                    "h1": "h1",
                    "h2": "h2",
                    "h3": "h3",
                    "h4": "h4",
                    "h5": "h5",
                    "h6": "h6",
                    "br": "br",
                    "p": "p",
                    "blockquote": "blockquote"
                },
                "font_family": "Segoe UI",
                "font_size": 14
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4)
            config = default_config
        else:
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        self.style_mapping = config.get("style_mapping", self.style_mapping)
        self.font_family = config.get("font_family", self.font_family)
        self.font_size = config.get("font_size", self.font_size)
        self.text_font.config(family=self.font_family, size=self.font_size)
    
    def save_config(self, config):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Error saving config file:\n{e}")
    
    def save_settings(self, event=None):
        new_bold = self.bold_entry.get().strip()
        new_italic = self.italic_entry.get().strip()
        new_code = self.code_entry.get().strip()
        new_br = self.br_entry.get().strip()
        if new_bold:
            self.style_mapping["bold"] = new_bold
        if new_italic:
            self.style_mapping["italic"] = new_italic
        if new_code:
            self.style_mapping["code"] = new_code
        if new_br:
            self.style_mapping["br"] = new_br
        for i in range(1, 7):
            key = f"h{i}"
            entry_val = self.heading_entries[key].get().strip()
            if entry_val:
                self.style_mapping[key] = entry_val
        
        # New settings for paragraph and blockquote tags.
        new_p = self.p_entry.get().strip()
        if new_p:
            self.style_mapping["p"] = new_p
        new_bq = self.blockquote_entry.get().strip()
        if new_bq:
            self.style_mapping["blockquote"] = new_bq
        
        try:
            new_font_size = int(self.font_size_entry.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Font Size", "Please enter a valid integer for font size.")
            return
        self.font_size = new_font_size
        self.text_font.config(size=self.font_size)
        self.md_text.config(font=self.text_font)
        self.html_text.config(font=self.text_font)
        config = {
            "style_mapping": self.style_mapping,
            "font_family": self.font_family,  # fixed
            "font_size": self.font_size
        }
        self.save_config(config)
        messagebox.showinfo("Settings Saved", "Settings have been updated.")
        self.update_editor_mode()
        self.convert_to_html()


if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    app = CustomMD2HTML(root)
    root.mainloop()
