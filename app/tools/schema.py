TOOLS_SCHEMA = [
    {
        "name": "open_explorer",
        "description": "Open Windows File Explorer. Optionally open a specific filesystem path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Optional path to open in File Explorer",
                }
            },
            "required": [],
        },
    },
    {
        "name": "list_dir",
        "description": "List folders and files inside the provided directory path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to inspect",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "create_folder",
        "description": "Create a new folder inside an existing directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Existing parent directory path where the new folder should be created",
                },
                "folder_name": {
                    "type": "string",
                    "description": "Name of the new folder to create",
                },
            },
            "required": ["path", "folder_name"],
        },
    },
    {
        "name": "read_text_file",
        "description": "Read a text file and return its contents or a preview.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the text file",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Optional character limit for large files",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_text_file",
        "description": "Create or overwrite a UTF-8 text file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to create or overwrite",
                },
                "content": {
                    "type": "string",
                    "description": "Text content to write",
                },
                "overwrite": {
                    "type": "boolean",
                    "description": "Whether an existing file may be overwritten",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "append_text_file",
        "description": "Append text to a file, creating it if necessary.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the target file",
                },
                "content": {
                    "type": "string",
                    "description": "Text content to append",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "copy_path",
        "description": "Copy a file or folder to another location.",
        "parameters": {
            "type": "object",
            "properties": {
                "source_path": {
                    "type": "string",
                    "description": "Existing file or folder path to copy",
                },
                "destination_path": {
                    "type": "string",
                    "description": "New destination path",
                },
            },
            "required": ["source_path", "destination_path"],
        },
    },
    {
        "name": "move_path",
        "description": "Move or rename a file or folder.",
        "parameters": {
            "type": "object",
            "properties": {
                "source_path": {
                    "type": "string",
                    "description": "Existing file or folder path to move",
                },
                "destination_path": {
                    "type": "string",
                    "description": "New destination path",
                },
            },
            "required": ["source_path", "destination_path"],
        },
    },
    {
        "name": "open_url",
        "description": "Open a website in the default browser.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Website URL to open",
                }
            },
            "required": ["url"],
        },
    },
    {
        "name": "open_app",
        "description": "Open one desktop application chosen from the installed Windows app catalog. The assistant should match exactly one app from the available app list before calling this tool.",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Exact application name from the available app catalog or a known alias",
                },
                "target": {
                    "type": "string",
                    "description": "Optional path or argument for the application",
                },
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "list_available_apps",
        "description": "List discovered launchable desktop applications from the Windows app catalog.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Optional maximum number of app names to return",
                }
            },
            "required": [],
        },
    },
]
