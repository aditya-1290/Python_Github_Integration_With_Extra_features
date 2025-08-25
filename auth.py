import json
import os
import hashlib
from datetime import time
from getpass import getpass
from pathlib import Path
from typing import Optional, Dict

class AuthManager:
    def __init__(self, data_dir: str = ".github_vector_cli"):
        self.data_dir = Path(data_dir)
        self.users_file = self.data_dir / "users.json"
        self.sessions_file = self.data_dir / "sessions.json"
        self._ensure_data_dir()
        self.current_user: Optional[str] = None

    def _ensure_data_dir(self) -> None:
        self.data_dir.mkdir(exist_ok=True)
        if not self.users_file.exists():
            self.users_file.write_text("{}")
        if not self.sessions_file.exists():
            self.sessions_file.write_text("{}")

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def register(self, username: str, password: str) -> bool:
        users = self._load_users()
        if username in users:
            return False
        
        users[username] = {
            "password_hash": self._hash_password(password),
            "github_token": None #"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"  # Placeholder token
        }
        self._save_users(users)
        return True

    def login(self, username: str, password: str) -> bool:
        users = self._load_users()
        if username not in users:
            return False
        
        if users[username]["password_hash"] != self._hash_password(password):
            return False
        
        self.current_user = username
        self._create_session(username)
        return True

    def logout(self) -> None:
        self.current_user = None
        self._clear_session()

    def set_github_token(self, username: str, token: str) -> None:
        users = self._load_users()
        if username in users:
            old_token = users[username].get("github_token")
            if old_token and old_token != token:
                # Archive old data when token changes
                self._archive_old_data(username, old_token)
            users[username]["github_token"] = token
            self._save_users(users)
    
    def _archive_old_data(self, username: str, old_token: str) -> None:
        """Archive old repository data when token changes"""
        import shutil
        from pathlib import Path
        
        # Create archive directory
        archive_dir = self.data_dir / "archives"
        archive_dir.mkdir(exist_ok=True)
        
        # Create unique archive name based on token hash
        token_hash = hashlib.md5(old_token.encode()).hexdigest()[:8]
        timestamp = str(int(time.time()))
        archive_name = f"{username}_{token_hash}_{timestamp}"
        archive_path = archive_dir / archive_name
        
        # Archive vector database
        vector_db_path = self.data_dir
        if vector_db_path.exists():
            archive_path.mkdir(exist_ok=True)
            
            # Archive ChromaDB data
            chroma_path = vector_db_path / "chroma.sqlite3"
            if chroma_path.exists():
                shutil.copy2(chroma_path, archive_path / "chroma.sqlite3")
            
            # Archive selected repo state
            selected_repo_path = self.data_dir / "selected_repo.json"
            if selected_repo_path.exists():
                shutil.copy2(selected_repo_path, archive_path / "selected_repo.json")
            
            print(f"[green]Archived old repository data to: {archive_path}[/green]")

    def get_github_token(self, username: str) -> Optional[str]:
        users = self._load_users()
        return users.get(username, {}).get("github_token")

    def _load_users(self) -> Dict:
        return json.loads(self.users_file.read_text())

    def _save_users(self, users: Dict) -> None:
        self.users_file.write_text(json.dumps(users, indent=2))

    def _create_session(self, username: str) -> None:
        sessions = {username: True}
        self.sessions_file.write_text(json.dumps(sessions, indent=2))

    def _clear_session(self) -> None:
        self.sessions_file.write_text("{}")

    def get_current_user(self) -> Optional[str]:
        if self.sessions_file.exists():
            sessions = json.loads(self.sessions_file.read_text())
            return next(iter(sessions.keys()), None)
        return None
    
    