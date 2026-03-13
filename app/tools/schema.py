TOOLS_SCHEMA = [
    {
        "name": "open_explorer",
        "description": "Open Windows File Explorer. Optionally open a specific filesystem path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Optional path to open in File Explorer"
                }
            },
            "required": []
        }
    },
    {
        "name": "list_dir",
        "description": "List files and folders inside the provided directory path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to inspect"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "create_folder",
        "description": "Create a new folder inside an existing directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Existing parent directory path where the new folder should be created"
                },
                "folder_name": {
                    "type": "string",
                    "description": "Name of the new folder to create"
                }
            },
            "required": ["path", "folder_name"]
        }
    }
]
