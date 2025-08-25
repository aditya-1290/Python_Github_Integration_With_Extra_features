from pathlib import Path
import os
from typing import Dict, Any
import yaml
from rich import print

class Config:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.config_dir = Path.home() / ".github_vector_cli"
        self.config_file = self.config_dir / "config.yaml"
        self.data_dir = self.config_dir / "data"
        self.log_dir = self.config_dir / "logs"
        
        # Create necessary directories
        self.config_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)
        
        # Default configuration
        self.defaults = {
            "embedding_model": "all-MiniLM-L6-v2",
            "max_file_size": 1024 * 1024 * 5,  # 5MB
            "supported_file_extensions": [".py", ".js", ".ts", ".java", ".cpp", ".h", ".cs", ".rb", ".go", ".rs", ".php", ".txt", ".md"],
            "max_chunk_size": 2000,
            "cache_ttl": 3600,  # 1 hour
            "rate_limit_attempts": 5,
            "rate_limit_period": 300,  # 5 minutes
            "terminal_colors": {
                "success": "green",
                "error": "red",
                "warning": "yellow",
                "info": "blue"
            }
        }
        
        self.load_config()
    
    def load_config(self):
        """Load configuration from file or create with defaults"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        self.defaults.update(user_config)
            except Exception as e:
                print(f"[red]Error loading config: {e}. Using defaults.[/red]")
        else:
            self.save_config()
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                yaml.safe_dump(self.defaults, f)
        except Exception as e:
            print(f"[red]Error saving config: {e}[/red]")
    
    def get(self, key: str) -> Any:
        """Get configuration value"""
        return self.defaults.get(key)
    
    def set(self, key: str, value: Any):
        """Set configuration value and save"""
        self.defaults[key] = value
        self.save_config()
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values"""
        return self.defaults.copy()
