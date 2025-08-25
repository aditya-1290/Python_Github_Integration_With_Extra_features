from github import Github, GithubException
from github.Repository import Repository
from github.ContentFile import ContentFile
from typing import List, Dict, Optional
from pathlib import Path
import os
import json
from rich.tree import Tree
from rich import print

class GitHubManager:
    def __init__(self, token: Optional[str] = None, data_dir: str = ".github_vector_cli"):
        self.gh = Github(token) if token else None
        self.data_dir = Path(data_dir)
        self.current_repo: Optional[Repository] = None
        self.repo_state_file = self.data_dir / "selected_repo.json"
        self._load_selected_repo()

    def _load_selected_repo(self) -> None:
        """Load the previously selected repository from file"""
        if self.repo_state_file.exists():
            try:
                state = json.loads(self.repo_state_file.read_text())
                repo_name = state.get("selected_repo")
                if repo_name and self.gh:
                    try:
                        self.current_repo = self.gh.get_user().get_repo(repo_name)
                    except GithubException:
                        # Repository no longer exists or access revoked
                        self.repo_state_file.unlink(missing_ok=True)
            except (json.JSONDecodeError, GithubException):
                # Invalid state file, remove it
                self.repo_state_file.unlink(missing_ok=True)

    def _save_selected_repo(self, repo_name: str) -> None:
        """Save the selected repository to file"""
        self.data_dir.mkdir(exist_ok=True)
        state = {"selected_repo": repo_name}
        self.repo_state_file.write_text(json.dumps(state, indent=2))

    def _clear_selected_repo(self) -> None:
        """Clear the selected repository state"""
        self.repo_state_file.unlink(missing_ok=True)

    def is_authenticated(self) -> bool:
        return self.gh is not None

    def get_repos(self) -> List[Dict[str, any]]:
        """Get basic information about all repositories"""
        if not self.gh:
            raise ValueError("GitHub not authenticated")
        return [{
            "name": repo.name,
            "full_name": repo.full_name,
            "description": repo.description or "No description",
            "created_at": repo.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        } for repo in self.gh.get_user().get_repos()]

    def get_repo_details(self, repo_name: str) -> Dict[str, any]:
        """Get detailed information about a specific repository"""
        if not self.gh:
            raise ValueError("GitHub not authenticated")
        
        repo = self.gh.get_user().get_repo(repo_name)
        return {
            "name": repo.name,
            "full_name": repo.full_name,
            "created_at": repo.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "languages": list(repo.get_languages().keys()),
            "branches": [branch.name for branch in repo.get_branches()],
            "commits_count": repo.get_commits().totalCount,
            "default_branch": repo.default_branch,
            "description": repo.description or "No description",
            "watchers_count": repo.watchers_count,
            "forks_count": repo.forks_count,
            "stars_count": repo.stargazers_count,
            "open_issues_count": repo.open_issues_count,
            "size": repo.size,
            "homepage": repo.homepage or "None",
            "visibility": repo.visibility,
            "updated_at": repo.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        }

    def create_repository(self, name: str, description: str = "", private: bool = False, 
                        has_issues: bool = True, has_wiki: bool = True, 
                        auto_init: bool = True) -> Dict[str, str]:
        """Create a new GitHub repository"""
        if not self.gh:
            raise ValueError("GitHub not authenticated")
        
        try:
            repo = self.gh.get_user().create_repo(
                name=name,
                description=description,
                private=private,
                has_issues=has_issues,
                has_wiki=has_wiki,
                auto_init=auto_init
            )
            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "clone_url": repo.clone_url,
                "html_url": repo.html_url,
                "private": repo.private
            }
        except Exception as e:
            raise ValueError(f"Failed to create repository: {str(e)}")

    def set_current_repo(self, repo_name: str) -> None:
        if not self.gh:
            raise ValueError("GitHub not authenticated")
        self.current_repo = self.gh.get_user().get_repo(repo_name)
        self._save_selected_repo(repo_name)

    def get_repo_tree(self, path: str = "") -> Tree:
        if not self.current_repo:
            raise ValueError("No repository selected")
        
        tree = Tree(f"[bold green]{self.current_repo.name}")
        contents = self.current_repo.get_contents(path)
        
        for content in contents:
            if content.type == "dir":
                branch = tree.add(f"[blue]{content.name}")
                self._add_directory_contents(branch, content.path)
            else:
                tree.add(f"[yellow]{content.name}")
        
        return tree

    def _add_directory_contents(self, tree: Tree, path: str) -> None:
        contents = self.current_repo.get_contents(path)
        for content in contents:
            if content.type == "dir":
                branch = tree.add(f"[blue]{content.name}")
                self._add_directory_contents(branch, content.path)
            else:
                tree.add(f"[yellow]{content.name}")

    def get_file_content(self, file_path: str) -> str:
        if not self.current_repo:
            raise ValueError("No repository selected")
        
        try:
            content = self.current_repo.get_contents(file_path)
            if isinstance(content, list):
                raise ValueError("Path is a directory, not a file")
            return content.decoded_content.decode("utf-8")
        except GithubException as e:
            raise ValueError(f"Error fetching file: {e}")

    def search_repo(self, query: str) -> Dict[str, str]:
        if not self.current_repo:
            raise ValueError("No repository selected")
        
        results = {}
        contents = self._get_all_contents(self.current_repo)
        
        for item in contents:
            if query.lower() in item.path.lower():
                results[item.path] = item.download_url
        
        return results

    def _get_all_contents(self, repo: Repository, path: str = "") -> List[ContentFile]:
        contents = []
        try:
            items = repo.get_contents(path)
            for item in items:
                if item.type == "dir":
                    contents.extend(self._get_all_contents(repo, item.path))
                else:
                    contents.append(item)
            return contents
        except GithubException:
            return []

    # Issue Management
    def create_issue(self, title: str, body: str, labels: List[str] = None) -> Dict[str, any]:
        """Create a new issue in the current repository"""
        if not self.current_repo:
            raise ValueError("No repository selected")
        
        issue = self.current_repo.create_issue(
            title=title,
            body=body,
            labels=labels
        )
        return {
            "number": issue.number,
            "title": issue.title,
            "url": issue.html_url,
            "state": issue.state
        }

    def get_issues(self, state: str = "all") -> List[Dict[str, any]]:
        """Get issues from the current repository"""
        if not self.current_repo:
            raise ValueError("No repository selected")
        
        return [{
            "number": issue.number,
            "title": issue.title,
            "state": issue.state,
            "created_at": issue.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": issue.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "comments": issue.comments,
            "labels": [label.name for label in issue.labels],
            "url": issue.html_url,
            "body": issue.body
        } for issue in self.current_repo.get_issues(state=state)]

    # Branch Management
    def create_branch(self, branch_name: str, from_branch: str = None) -> Dict[str, str]:
        """Create a new branch in the current repository"""
        if not self.current_repo:
            raise ValueError("No repository selected")
        
        if not from_branch:
            from_branch = self.current_repo.default_branch
            
        source_branch = self.current_repo.get_branch(from_branch)
        self.current_repo.create_git_ref(
            ref=f"refs/heads/{branch_name}",
            sha=source_branch.commit.sha
        )
        
        return {
            "name": branch_name,
            "sha": source_branch.commit.sha,
            "source": from_branch
        }

    def delete_branch(self, branch_name: str) -> bool:
        """Delete a branch from the current repository"""
        if not self.current_repo:
            raise ValueError("No repository selected")
        
        if branch_name == self.current_repo.default_branch:
            raise ValueError("Cannot delete default branch")
        
        ref = self.current_repo.get_git_ref(f"heads/{branch_name}")
        ref.delete()
        return True

    # Pull Request Management
    def create_pull_request(self, title: str, body: str, head: str, base: str) -> Dict[str, any]:
        """Create a new pull request"""
        if not self.current_repo:
            raise ValueError("No repository selected")
        
        pr = self.current_repo.create_pull(
            title=title,
            body=body,
            head=head,
            base=base
        )
        
        return {
            "number": pr.number,
            "title": pr.title,
            "url": pr.html_url,
            "state": pr.state,
            "created_at": pr.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_pull_requests(self, state: str = "all") -> List[Dict[str, any]]:
        """Get pull requests from the current repository"""
        if not self.current_repo:
            raise ValueError("No repository selected")
        
        return [{
            "number": pr.number,
            "title": pr.title,
            "state": pr.state,
            "created_at": pr.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": pr.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "user": pr.user.login,
            "head": pr.head.ref,
            "base": pr.base.ref,
            "mergeable": pr.mergeable,
            "url": pr.html_url
        } for pr in self.current_repo.get_pulls(state=state)]

    # Release Management
    def create_release(self, tag: str, title: str, body: str, 
                      prerelease: bool = False) -> Dict[str, any]:
        """Create a new release"""
        if not self.current_repo:
            raise ValueError("No repository selected")
        
        release = self.current_repo.create_git_release(
            tag=tag,
            name=title,
            message=body,
            prerelease=prerelease
        )
        
        return {
            "tag": release.tag_name,
            "title": release.title,
            "url": release.html_url,
            "created_at": release.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "prerelease": release.prerelease
        }

    def get_releases(self) -> List[Dict[str, any]]:
        """Get all releases from the current repository"""
        if not self.current_repo:
            raise ValueError("No repository selected")
        
        return [{
            "tag": release.tag_name,
            "title": release.title,
            "created_at": release.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "prerelease": release.prerelease,
            "url": release.html_url,
            "body": release.body
        } for release in self.current_repo.get_releases()]

    # Collaborator Management
    def add_collaborator(self, username: str, permission: str = "push") -> bool:
        """Add a collaborator to the current repository"""
        if not self.current_repo:
            raise ValueError("No repository selected")
        
        self.current_repo.add_to_collaborators(username, permission=permission)
        return True

    def remove_collaborator(self, username: str) -> bool:
        """Remove a collaborator from the current repository"""
        if not self.current_repo:
            raise ValueError("No repository selected")
        
        self.current_repo.remove_from_collaborators(username)
        return True

    def get_collaborators(self) -> List[Dict[str, any]]:
        """Get all collaborators of the current repository"""
        if not self.current_repo:
            raise ValueError("No repository selected")
        
        return [{
            "login": collab.login,
            "id": collab.id,
            "url": collab.html_url,
            "type": collab.type,
            "permissions": self.current_repo.get_collaborator_permission(collab.login)
        } for collab in self.current_repo.get_collaborators()]
        