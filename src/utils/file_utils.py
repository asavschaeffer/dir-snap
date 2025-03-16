import os

def get_file_icon(filename):
    """Return appropriate emoji based on file extension."""
    ext = os.path.splitext(filename)[1].lower()
    
    # Images
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.tiff', '.webp']:
        return "🖼️", "image"
    
    # Documents
    elif ext in ['.doc', '.docx', '.odt', '.rtf', '.pdf', '.txt', '.md', '.csv', '.xlsx', '.xls', '.pptx', '.ppt']:
        if ext == '.pdf':
            return "📕", "document"
        elif ext in ['.xlsx', '.xls', '.csv']:
            return "📊", "document"
        elif ext in ['.pptx', '.ppt']:
            return "📑", "document"
        elif ext in ['.md', '.txt']:
            return "📝", "document"
        else:
            return "📄", "document"
    
    # Code & Scripts
    elif ext in ['.py', '.js', '.html', '.css', '.java', '.c', '.cpp', '.h', '.php', '.sh', '.bat', '.ps1', '.rb', '.go', '.ts', '.json', '.xml']:
        if ext == '.py':
            return "🐍", "code"
        elif ext == '.js':
            return "📜", "code"
        elif ext in ['.html', '.css']:
            return "🌐", "code"
        elif ext == '.json' or ext == '.xml':
            return "🔧", "code"
        else:
            return "📜", "code"
    
    # Archives
    elif ext in ['.zip', '.rar', '.tar', '.gz', '.7z']:
        return "🗜️", "archive"
    
    # Audio
    elif ext in ['.mp3', '.wav', '.ogg', '.flac', '.m4a']:
        return "🔊", "file"
    
    # Video
    elif ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
        return "🎬", "file"
    
    # Executable
    elif ext in ['.exe', '.app', '.dll', '.so']:
        return "⚙️", "file"
    
    # Default
    else:
        return "📄", "file" 