def generate_output(self, output_type: str, copy_to_clipboard: bool = False):
        """Generate output in the specified format and optionally copy to clipboard."""
        try:
            # Get the current directory path
            current_dir = self.current_path.get()
            if not current_dir:
                messagebox.showerror("Error", "No directory selected")
                return
            
            # Generate the output based on the selected format
            if output_type == "txt":
                output = generate_txt_tree(current_dir)
            elif output_type == "json":
                output = generate_json_tree(current_dir)
            elif output_type == "mermaid":
                output = generate_mermaid_tree(current_dir)
            else:
                raise ValueError(f"Unsupported output type: {output_type}")
            
            # If copy_to_clipboard is True, copy to clipboard
            if copy_to_clipboard:
                self.root.clipboard_clear()
                self.root.clipboard_append(output)
                messagebox.showinfo("Success", "Output copied to clipboard!")
            else:
                # Only save to file if we're not copying to clipboard
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"dir_structure_{timestamp}.{output_type}"
                
                # Get the user's Downloads folder
                downloads_path = os.path.expanduser("~/Downloads")
                filepath = os.path.join(downloads_path, filename)
                
                # Save the file
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(output)
                
                messagebox.showinfo("Success", f"Output saved to:\n{filepath}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate output: {str(e)}")
            print(f"Error generating output: {str(e)}")
            traceback.print_exc()

    def create_output_buttons(self):
        """Create buttons for different output formats."""
        # Create a frame for the output buttons
        output_frame = ttk.LabelFrame(self.root, text="Output Options", padding="5")
        output_frame.pack(fill="x", padx=5, pady=5)
        
        # Create buttons for each format
        formats = [
            ("TXT", "txt"),
            ("JSON", "json"),
            ("Mermaid", "mermaid")
        ]
        
        for i, (label, format_type) in enumerate(formats):
            # Create a frame for each format's buttons
            format_frame = ttk.Frame(output_frame)
            format_frame.pack(fill="x", pady=2)
            
            # Add format label
            ttk.Label(format_frame, text=f"{label}:").pack(side="left", padx=5)
            
            # Download button
            download_btn = ttk.Button(
                format_frame,
                text="Download",
                command=lambda f=format_type: self.generate_output(f, copy_to_clipboard=False)
            )
            download_btn.pack(side="left", padx=5)
            
            # Copy button
            copy_btn = ttk.Button(
                format_frame,
                text="Copy",
                command=lambda f=format_type: self.generate_output(f, copy_to_clipboard=True)
            )
            copy_btn.pack(side="left", padx=5) 