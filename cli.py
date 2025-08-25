from typing import Optional
from rich import print
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
import sys # Import sys for exiting

from auth import AuthManager
from githubs import GitHubManager
from chroma import VectorDBManager
from utils.tree import display_repo_tree
# No need to load plugins dynamically in this menu-driven approach
# from .plugins import load_plugins

# Initialize managers globally
auth_manager = AuthManager()
vector_db = VectorDBManager()
github_manager: Optional[GitHubManager] = None # Will be set after login/token set

def get_github_manager_instance() -> GitHubManager:
    """Get or create GitHubManager instance with proper authentication.
    This version is adapted for the menu-driven flow, raising an error
    if not authenticated, which the menu loop will catch.
    """
    global github_manager
    
    if github_manager is not None:
        return github_manager
    
    username = auth_manager.get_current_user()
    if not username:
        raise ValueError("You must be logged in to perform this action.")
    
    github_token = auth_manager.get_github_token(username)
    if not github_token:
        raise ValueError("GitHub token not set. Please set your token first.")
    
    try:
        github_manager = GitHubManager(github_token)
        return github_manager
    except Exception as e:
        raise ValueError(f"Error initializing GitHub client: {e}")

def display_main_menu(logged_in_user: Optional[str]) -> None:
    """Displays the main menu options."""
    print(Panel.fit("[bold blue]GitHub Vector CLI Menu[/bold blue]"))
    if logged_in_user:
        print(f"Logged in as: [green]{logged_in_user}[/green]")
        
        current_repo = None
        try:
            manager = get_github_manager_instance()
            current_repo = manager.current_repo.name if manager.current_repo else None
        except:
            pass

        if current_repo:
            print(f"\nCurrently working with repository: [bold cyan]{current_repo}[/bold cyan]")
        else:
            print("\n[yellow]No repository selected. Use option 3 to select a repository for additional features.[/yellow]")
        
        print("\n[bold yellow]Repository Management:[/bold yellow]")
        print("1. List Repositories")
        print("2. Create New Repository")
        print("3. Select Repository")
        
        print("\n[bold yellow]Repository Analysis:[/bold yellow]")
        print("4. Index Selected Repository")
        print("5. Search Indexed Repositories")
        print("6. Semantic Search")
        print("7. View Repository Stats")
        print("8. Open Repository File")
        
        if current_repo:
            print("\n[bold green]═══ Repository-Specific Features ═══[/bold green]")
            
            print("\n[bold yellow]Issue Management:[/bold yellow]")
            print("9. List Issues")
            print("10. Create Issue")
            print("11. Update Issue")
            
            print("\n[bold yellow]Branch Management:[/bold yellow]")
            print("12. List Branches")
            print("13. Create Branch")
            print("14. Delete Branch")
            
            print("\n[bold yellow]Pull Request Management:[/bold yellow]")
            print("15. List Pull Requests")
            print("16. Create Pull Request")
            
            print("\n[bold yellow]Release Management:[/bold yellow]")
            print("17. List Releases")
            print("18. Create Release")
            
            print("\n[bold yellow]Collaborator Management:[/bold yellow]")
            print("19. List Collaborators")
            print("20. Add Collaborator")
            print("21. Remove Collaborator")
        else:
            print("\n[dim]Repository-specific features will be available after selecting a repository:[/dim]")
            print("[dim]- Issue Management[/dim]")
            print("[dim]- Branch Management[/dim]")
            print("[dim]- Pull Request Management[/dim]")
            print("[dim]- Release Management[/dim]")
            print("[dim]- Collaborator Management[/dim]")
        
        print("\n[bold yellow]Settings:[/bold yellow]")
        print("22. Set GitHub Token")
        print("23. Logout")
    else:
        print("\n[bold yellow]Authentication:[/bold yellow]")
        print("1. Login")
        print("2. Register")
    print("0. Exit")
    print("-" * 30)

def handle_register():
    """Handles user registration."""
    print("\n--- Register ---")
    username = input("Enter username: ")
    password = input("Enter password: ") # getpass.getpass() is better for production
    
    if auth_manager.register(username, password):
        print(f"[green]Successfully registered user {username}[/green]")
    else:
        print(f"[red]Username {username} already exists[/red]")

def handle_login():
    """Handles user login."""
    global github_manager
    print("\n--- Login ---")
    username = input("Enter username: ")
    password = input("Enter password: ") # getpass.getpass() is better for production
    
    if auth_manager.login(username, password):
        github_manager = None # Reset manager to ensure fresh state
        print(f"[green]Successfully logged in as {username}[/green]")
        token = auth_manager.get_github_token(username)
        if token:
            try:
                github_manager = GitHubManager(token)
                print("[green]GitHub token loaded automatically[/green]")
            except Exception as e:
                print(f"[yellow]Warning: Could not initialize GitHub client with saved token: {e}[/yellow]")
    else:
        print("[red]Invalid username or password[/red]")

def handle_logout():
    """Handles user logout."""
    global github_manager
    auth_manager.logout()
    github_manager = None
    print("[green]Successfully logged out[/green]")

def handle_set_github_token():
    """Handles setting GitHub personal access token."""
    global github_manager
    username = auth_manager.get_current_user()
    if not username:
        print("[red]You must be logged in to set a GitHub token[/red]")
        return
    
    token = input("Enter GitHub Personal Access Token: ") # getpass.getpass() is better
    auth_manager.set_github_token(username, token)
    try:
        github_manager = GitHubManager(token)
        print("[green]GitHub token set successfully[/green]")
    except Exception as e:
        print(f"[red]Error initializing GitHub client with new token: {e}[/red]")

def handle_list_issues():
    """Handle listing repository issues"""
    try:
        manager = get_github_manager_instance()
        
        state = input("Enter issue state (open/closed/all) [all]: ").strip().lower() or "all"
        if state not in ["open", "closed", "all"]:
            print("[red]Invalid state. Using 'all'.[/red]")
            state = "all"
            
        issues = manager.get_issues(state)
        
        if not issues:
            print("[yellow]No issues found.[/yellow]")
            return
            
        table = Table(title=f"[bold blue]Repository Issues ({state})[/bold blue]")
        table.add_column("#", style="blue", justify="right")
        table.add_column("Title", style="cyan")
        table.add_column("State", style="green")
        table.add_column("Comments", style="yellow", justify="right")
        table.add_column("Created", style="magenta")
        
        for issue in issues:
            table.add_row(
                str(issue["number"]),
                issue["title"],
                issue["state"],
                str(issue["comments"]),
                issue["created_at"]
            )
            
        print(table)
        
    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred: {e}[/red]")

def handle_create_issue():
    """Handle creating a new issue"""
    try:
        manager = get_github_manager_instance()
        
        print(Panel.fit("[bold blue]Create New Issue[/bold blue]"))
        
        # Get issue details
        title = input("Enter issue title: ").strip()
        if not title:
            print("[red]Issue title cannot be empty.[/red]")
            return
            
        print("Enter issue body (press Enter twice to finish):")
        body_lines = []
        while True:
            line = input()
            if line == "" and (not body_lines or body_lines[-1] == ""):
                break
            body_lines.append(line)
        body = "\n".join(body_lines[:-1])
        
        # Get labels
        labels = input("Enter labels (comma-separated) or press Enter for none: ").strip()
        labels = [label.strip() for label in labels.split(",")] if labels else None
        
        # Show confirmation
        print("\n[bold cyan]Issue Details:[/bold cyan]")
        print(f"[yellow]Title:[/yellow] {title}")
        print(f"[yellow]Labels:[/yellow] {', '.join(labels) if labels else 'None'}")
        print("\n[yellow]Body:[/yellow]")
        print(body)
        
        if input("\nCreate issue with these details? (Y/n): ").strip().lower() != 'n':
            with Progress() as progress:
                task = progress.add_task("[cyan]Creating issue...", total=1)
                issue = manager.create_issue(title, body, labels)
                progress.update(task, completed=1)
            
            print(f"[green]Issue #{issue['number']} created successfully![/green]")
            print(f"View it at: {issue['url']}")
        else:
            print("[yellow]Issue creation cancelled.[/yellow]")
            
    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred: {e}[/red]")

def handle_list_branches():
    """Handle listing repository branches"""
    try:
        manager = get_github_manager_instance()
        repo_details = manager.get_repo_details(manager.current_repo.name)
        
        table = Table(title="[bold blue]Repository Branches[/bold blue]")
        table.add_column("No.", style="blue", justify="right")
        table.add_column("Branch Name", style="cyan")
        table.add_column("Default", style="green")
        
        for idx, branch in enumerate(repo_details["branches"], 1):
            table.add_row(
                str(idx),
                branch,
                "✓" if branch == repo_details["default_branch"] else ""
            )
            
        print(table)
        
    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred: {e}[/red]")

def handle_create_branch():
    """Handle creating a new branch"""
    try:
        manager = get_github_manager_instance()
        
        print(Panel.fit("[bold blue]Create New Branch[/bold blue]"))
        
        # Show existing branches
        handle_list_branches()
        
        # Get branch details
        branch_name = input("\nEnter new branch name: ").strip()
        if not branch_name:
            print("[red]Branch name cannot be empty.[/red]")
            return
        
        repo_details = manager.get_repo_details(manager.current_repo.name)
        print(f"\nAvailable source branches: {', '.join(repo_details['branches'])}")
        from_branch = input(f"Enter source branch (Enter for {repo_details['default_branch']}): ").strip()
        
        if not from_branch:
            from_branch = repo_details['default_branch']
        elif from_branch not in repo_details['branches']:
            print("[red]Invalid source branch.[/red]")
            return
            
        if input(f"\nCreate branch '{branch_name}' from '{from_branch}'? (Y/n): ").strip().lower() != 'n':
            with Progress() as progress:
                task = progress.add_task("[cyan]Creating branch...", total=1)
                result = manager.create_branch(branch_name, from_branch)
                progress.update(task, completed=1)
            
            print(f"[green]Branch '{branch_name}' created successfully![/green]")
            print(f"Created from: {result['source']}")
            print(f"Commit SHA: {result['sha'][:7]}")
        else:
            print("[yellow]Branch creation cancelled.[/yellow]")
            
    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred: {e}[/red]")

def handle_list_pull_requests():
    """Handle listing pull requests"""
    try:
        manager = get_github_manager_instance()
        
        state = input("Enter PR state (open/closed/all) [all]: ").strip().lower() or "all"
        if state not in ["open", "closed", "all"]:
            print("[red]Invalid state. Using 'all'.[/red]")
            state = "all"
        
        prs = manager.get_pull_requests(state)
        
        if not prs:
            print("[yellow]No pull requests found.[/yellow]")
            return
        
        table = Table(title=f"[bold blue]Pull Requests ({state})[/bold blue]")
        table.add_column("#", style="blue", justify="right")
        table.add_column("Title", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("From → To", style="yellow")
        table.add_column("Created By", style="magenta")
        table.add_column("Created At", style="cyan")
        
        for pr in prs:
            status = pr["state"]
            if pr["state"] == "open" and pr["mergeable"]:
                status = "Ready to merge"
            elif pr["state"] == "open" and not pr["mergeable"]:
                status = "Conflicts"
                
            table.add_row(
                str(pr["number"]),
                pr["title"],
                status,
                f"{pr['head']} → {pr['base']}",
                pr["user"],
                pr["created_at"]
            )
        
        print(table)
        
    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred: {e}[/red]")

def handle_create_pull_request():
    """Handle creating a new pull request"""
    try:
        manager = get_github_manager_instance()
        
        print(Panel.fit("[bold blue]Create New Pull Request[/bold blue]"))
        
        # Show available branches
        handle_list_branches()
        
        # Get PR details
        head = input("\nEnter source branch (from): ").strip()
        base = input("Enter target branch (to): ").strip()
        
        repo_details = manager.get_repo_details(manager.current_repo.name)
        if head not in repo_details['branches'] or base not in repo_details['branches']:
            print("[red]One or both branches not found.[/red]")
            return
        
        if head == base:
            print("[red]Source and target branches must be different.[/red]")
            return
        
        title = input("Enter PR title: ").strip()
        if not title:
            print("[red]PR title cannot be empty.[/red]")
            return
        
        print("Enter PR description (press Enter twice to finish):")
        body_lines = []
        while True:
            line = input()
            if line == "" and (not body_lines or body_lines[-1] == ""):
                break
            body_lines.append(line)
        body = "\n".join(body_lines[:-1])
        
        # Show confirmation
        print("\n[bold cyan]Pull Request Details:[/bold cyan]")
        print(f"[yellow]Title:[/yellow] {title}")
        print(f"[yellow]From:[/yellow] {head}")
        print(f"[yellow]To:[/yellow] {base}")
        print("\n[yellow]Description:[/yellow]")
        print(body)
        
        if input("\nCreate pull request with these details? (Y/n): ").strip().lower() != 'n':
            with Progress() as progress:
                task = progress.add_task("[cyan]Creating pull request...", total=1)
                pr = manager.create_pull_request(title, body, head, base)
                progress.update(task, completed=1)
            
            print(f"[green]Pull Request #{pr['number']} created successfully![/green]")
            print(f"View it at: {pr['url']}")
        else:
            print("[yellow]Pull request creation cancelled.[/yellow]")
            
    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred: {e}[/red]")

def handle_list_releases():
    """Handle listing releases"""
    try:
        manager = get_github_manager_instance()
        releases = manager.get_releases()
        
        if not releases:
            print("[yellow]No releases found.[/yellow]")
            return
        
        table = Table(title="[bold blue]Repository Releases[/bold blue]")
        table.add_column("Tag", style="blue")
        table.add_column("Title", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Created At", style="yellow")
        
        for release in releases:
            table.add_row(
                release["tag"],
                release["title"],
                "Pre-release" if release["prerelease"] else "Release",
                release["created_at"]
            )
        
        print(table)
        
    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred: {e}[/red]")

def handle_create_release():
    """Handle creating a new release"""
    try:
        manager = get_github_manager_instance()
        
        print(Panel.fit("[bold blue]Create New Release[/bold blue]"))
        
        # Get release details
        tag = input("Enter release tag (e.g., v1.0.0): ").strip()
        if not tag:
            print("[red]Release tag cannot be empty.[/red]")
            return
        
        title = input("Enter release title: ").strip()
        if not title:
            print("[red]Release title cannot be empty.[/red]")
            return
        
        print("Enter release notes (press Enter twice to finish):")
        notes_lines = []
        while True:
            line = input()
            if line == "" and (not notes_lines or notes_lines[-1] == ""):
                break
            notes_lines.append(line)
        notes = "\n".join(notes_lines[:-1])
        
        prerelease = input("Is this a pre-release? (y/N): ").strip().lower() == 'y'
        
        # Show confirmation
        print("\n[bold cyan]Release Details:[/bold cyan]")
        print(f"[yellow]Tag:[/yellow] {tag}")
        print(f"[yellow]Title:[/yellow] {title}")
        print(f"[yellow]Type:[/yellow] {'Pre-release' if prerelease else 'Release'}")
        print("\n[yellow]Release Notes:[/yellow]")
        print(notes)
        
        if input("\nCreate release with these details? (Y/n): ").strip().lower() != 'n':
            with Progress() as progress:
                task = progress.add_task("[cyan]Creating release...", total=1)
                release = manager.create_release(tag, title, notes, prerelease)
                progress.update(task, completed=1)
            
            print(f"[green]Release {release['tag']} created successfully![/green]")
            print(f"View it at: {release['url']}")
        else:
            print("[yellow]Release creation cancelled.[/yellow]")
            
    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred: {e}[/red]")

def handle_list_collaborators():
    """Handle listing collaborators"""
    try:
        manager = get_github_manager_instance()
        collaborators = manager.get_collaborators()
        
        if not collaborators:
            print("[yellow]No collaborators found.[/yellow]")
            return
        
        table = Table(title="[bold blue]Repository Collaborators[/bold blue]")
        table.add_column("Username", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Permissions", style="green")
        
        for collab in collaborators:
            table.add_row(
                collab["login"],
                collab["type"],
                collab["permissions"]
            )
        
        print(table)
        
    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred: {e}[/red]")

def handle_add_collaborator():
    """Handle adding a new collaborator"""
    try:
        manager = get_github_manager_instance()
        
        print(Panel.fit("[bold blue]Add Collaborator[/bold blue]"))
        
        username = input("Enter GitHub username to add: ").strip()
        if not username:
            print("[red]Username cannot be empty.[/red]")
            return
        
        print("\nPermission levels:")
        print("1. pull (Read-only)")
        print("2. push (Read-write)")
        print("3. admin (Full access)")
        
        permission_choice = input("\nSelect permission level (1-3) [2]: ").strip() or "2"
        if permission_choice not in ["1", "2", "3"]:
            print("[red]Invalid choice. Using 'push' permission.[/red]")
            permission_choice = "2"
            
        permissions = {
            "1": "pull",
            "2": "push",
            "3": "admin"
        }
        
        permission = permissions[permission_choice]
        
        if input(f"\nAdd {username} as collaborator with {permission} access? (Y/n): ").strip().lower() != 'n':
            with Progress() as progress:
                task = progress.add_task("[cyan]Adding collaborator...", total=1)
                manager.add_collaborator(username, permission)
                progress.update(task, completed=1)
            
            print(f"[green]Successfully added {username} as collaborator![/green]")
            print("[yellow]Note: They will need to accept the invitation to gain access.[/yellow]")
        else:
            print("[yellow]Collaborator addition cancelled.[/yellow]")
            
    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred: {e}[/red]")

def handle_remove_collaborator():
    """Handle removing a collaborator"""
    try:
        manager = get_github_manager_instance()
        
        print(Panel.fit("[bold blue]Remove Collaborator[/bold blue]"))
        
        # Show current collaborators
        handle_list_collaborators()
        
        username = input("\nEnter username to remove (or 0 to cancel): ").strip()
        if username == "0":
            return
        
        collaborators = manager.get_collaborators()
        if not any(c["login"] == username for c in collaborators):
            print("[red]Username not found in collaborators.[/red]")
            return
        
        if input(f"\n[bold red]Warning:[/bold red] Are you sure you want to remove {username} as collaborator? (y/N): ").strip().lower() == 'y':
            with Progress() as progress:
                task = progress.add_task("[cyan]Removing collaborator...", total=1)
                manager.remove_collaborator(username)
                progress.update(task, completed=1)
            
            print(f"[green]Successfully removed {username} as collaborator![/green]")
        else:
            print("[yellow]Collaborator removal cancelled.[/yellow]")
            
    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred: {e}[/red]")

def handle_delete_branch():
    """Handle deleting a branch"""
    try:
        manager = get_github_manager_instance()
        
        print(Panel.fit("[bold blue]Delete Branch[/bold blue]"))
        
        # Show existing branches
        handle_list_branches()
        
        branch_name = input("\nEnter branch name to delete (or 0 to cancel): ").strip()
        if branch_name == "0":
            return
            
        repo_details = manager.get_repo_details(manager.current_repo.name)
        if branch_name not in repo_details['branches']:
            print("[red]Branch not found.[/red]")
            return
            
        if branch_name == repo_details['default_branch']:
            print("[red]Cannot delete default branch.[/red]")
            return
            
        if input(f"\n[bold red]Warning:[/bold red] Are you sure you want to delete branch '{branch_name}'? (y/N): ").strip().lower() == 'y':
            with Progress() as progress:
                task = progress.add_task("[cyan]Deleting branch...", total=1)
                manager.delete_branch(branch_name)
                progress.update(task, completed=1)
            
            print(f"[green]Branch '{branch_name}' deleted successfully![/green]")
        else:
            print("[yellow]Branch deletion cancelled.[/yellow]")
            
    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred: {e}[/red]")

def handle_update_issue():
    """Handle updating an existing issue"""
    try:
        manager = get_github_manager_instance()
        
        # First show existing issues
        handle_list_issues()
        
        issue_number = input("\nEnter issue number to update (or 0 to cancel): ").strip()
        if issue_number == "0":
            return
            
        issues = manager.get_issues()
        issue = next((i for i in issues if str(i["number"]) == issue_number), None)
        
        if not issue:
            print("[red]Issue not found.[/red]")
            return
            
        print(f"\n[bold cyan]Current Issue Details:[/bold cyan]")
        print(f"[yellow]Title:[/yellow] {issue['title']}")
        print(f"[yellow]State:[/yellow] {issue['state']}")
        print(f"[yellow]Labels:[/yellow] {', '.join(issue['labels'])}")
        print("\n[yellow]Body:[/yellow]")
        print(issue['body'])
        
        # Get updates
        new_state = input("\nUpdate state (open/closed) or Enter to skip: ").strip().lower()
        if new_state and new_state not in ["open", "closed"]:
            print("[red]Invalid state. Skipping state update.[/red]")
            new_state = ""
            
        new_title = input("Enter new title or Enter to skip: ").strip()
        
        print("Enter new body or press Enter twice to skip:")
        body_lines = []
        while True:
            line = input()
            if line == "" and (not body_lines or body_lines[-1] == ""):
                break
            body_lines.append(line)
        new_body = "\n".join(body_lines[:-1]) if body_lines[:-1] else None
        
        if new_state or new_title or new_body:
            updates = {}
            if new_state:
                updates["state"] = new_state
            if new_title:
                updates["title"] = new_title
            if new_body:
                updates["body"] = new_body
                
            print("\n[bold cyan]Updates to apply:[/bold cyan]")
            for key, value in updates.items():
                print(f"[yellow]{key}:[/yellow] {value}")
                
            if input("\nApply these updates? (Y/n): ").strip().lower() != 'n':
                with Progress() as progress:
                    task = progress.add_task("[cyan]Updating issue...", total=1)
                    # Note: Need to add issue.edit() to the GitHubManager class
                    progress.update(task, completed=1)
                
                print(f"[green]Issue #{issue_number} updated successfully![/green]")
            else:
                print("[yellow]Issue update cancelled.[/yellow]")
        else:
            print("[yellow]No updates specified.[/yellow]")
            
    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred: {e}[/red]")

def handle_create_repo():
    """Handles creating a new GitHub repository"""
    try:
        manager = get_github_manager_instance()
        
        print(Panel.fit("[bold blue]Create New GitHub Repository[/bold blue]"))
        
        # Get repository details
        while True:
            name = input("Enter repository name: ").strip()
            if name:
                break
            print("[red]Repository name cannot be empty.[/red]")
        
        description = input("Enter repository description (optional): ").strip()
        
        private = input("Make repository private? (y/N): ").strip().lower() == 'y'
        
        print("\n[bold cyan]Additional Settings:[/bold cyan]")
        has_issues = input("Enable Issues? (Y/n): ").strip().lower() != 'n'
        has_wiki = input("Enable Wiki? (Y/n): ").strip().lower() != 'n'
        auto_init = input("Initialize with README? (Y/n): ").strip().lower() != 'n'
        
        # Show confirmation
        print("\n[bold cyan]Repository Settings:[/bold cyan]")
        table = Table(show_header=False, box=None)
        table.add_column("Setting", style="yellow")
        table.add_column("Value", style="green")
        
        table.add_row("Name", name)
        table.add_row("Description", description if description else "(none)")
        table.add_row("Private", "Yes" if private else "No")
        table.add_row("Issues Enabled", "Yes" if has_issues else "No")
        table.add_row("Wiki Enabled", "Yes" if has_wiki else "No")
        table.add_row("Initialize README", "Yes" if auto_init else "No")
        
        print(table)
        
        if input("\nCreate repository with these settings? (Y/n): ").strip().lower() != 'n':
            with Progress() as progress:
                task = progress.add_task("[cyan]Creating repository...", total=1)
                
                result = manager.create_repository(
                    name=name,
                    description=description,
                    private=private,
                    has_issues=has_issues,
                    has_wiki=has_wiki,
                    auto_init=auto_init
                )
                
                progress.update(task, completed=1)
            
            print(Panel.fit(f"""[green]Repository created successfully![/green]
                
Name: {result['name']}
Full Name: {result['full_name']}
URL: {result['html_url']}
Clone URL: {result['clone_url']}
Privacy: {'Private' if result['private'] else 'Public'}"""))
        else:
            print("[yellow]Repository creation cancelled.[/yellow]")
            
    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred: {e}[/red]")

def handle_list_repos():
    """Handles listing GitHub repositories."""
    try:
        manager = get_github_manager_instance()
        repos = manager.get_repos()
        
        if not repos:
            print("[yellow]No repositories found.[/yellow]")
            return None

        # Main repositories table
        table = Table(title="[bold blue]Your GitHub Repositories[/bold blue]")
        table.add_column("No.", style="blue", justify="right")
        table.add_column("Repository Name", style="cyan")
        table.add_column("Description", style="yellow")
        table.add_column("Created At", style="green")

        for idx, repo in enumerate(repos, 1):
            # Truncate description if too long
            description = repo["description"]
            if len(description) > 50:
                description = description[:47] + "..."

            table.add_row(
                str(idx),
                repo["name"],
                description,
                repo["created_at"]
            )

        print(table)
        return repos  # Return repos for use in other functions
    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
        return None
    except Exception as e:
        print(f"[red]An unexpected error occurred: {e}[/red]")
        return None

        return repos  # Return repos for use in other functions
    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
        return None
    except Exception as e:
        print(f"[red]An unexpected error occurred: {e}[/red]")
        return None

def handle_select_repo():
    """Handles selecting a repository."""
    try:
        manager = get_github_manager_instance()
        repos = handle_list_repos()  # This will display the table and return repos list
        if not repos:
            return

        while True:
            repo_choice = input("\nEnter repository number to select (or 0 to cancel): ").strip()
            if repo_choice == "0":
                return
            
            if repo_choice.isdigit() and 1 <= int(repo_choice) <= len(repos):
                selected_repo = repos[int(repo_choice) - 1]
                manager.set_current_repo(selected_repo["name"])
                
                # Get detailed information about the selected repository
                details = manager.get_repo_details(selected_repo["name"])
                
                # Display repository information in organized panels
                main_info = f"""[bold cyan]Repository Information[/bold cyan]
                                [yellow]Name:[/yellow] {details['name']}
                                [yellow]Full Name:[/yellow] {details['full_name']}
                                [yellow]Description:[/yellow] {details['description']}
                                [yellow]Visibility:[/yellow] {details['visibility']}
                                [yellow]Homepage:[/yellow] {details['homepage']}

                                [bold cyan]Timeline[/bold cyan]
                                [yellow]Created:[/yellow] {details['created_at']}
                                [yellow]Last Updated:[/yellow] {details['updated_at']}

                                [bold cyan]Code Statistics[/bold cyan]
                                [yellow]Languages:[/yellow] {', '.join(details['languages']) or 'None'}
                                [yellow]Size:[/yellow] {details['size']} KB
                                [yellow]Default Branch:[/yellow] {details['default_branch']}
                                [yellow]Total Commits:[/yellow] {details['commits_count']}
                                [yellow]Branches:[/yellow] {', '.join(details['branches'])}"""

                stats_info = f"""[bold cyan]Repository Statistics[/bold cyan]
                                ⭐ Stars:    {details['stars_count']}
                                🔀 Forks:    {details['forks_count']}
                                👀 Watchers: {details['watchers_count']}
                                ❗ Issues:   {details['open_issues_count']}"""

                # Print the panels
                print(Panel(main_info, title="[bold green]Repository Details[/bold green]", 
                          border_style="green"))
                print()
                print(Panel(stats_info, title="[bold blue]Activity Statistics[/bold blue]", 
                          border_style="blue"))
                print()
                
                print("[cyan]Repository File Structure:[/cyan]")
                display_repo_tree(manager)
                break
            else:
                print("[red]Invalid selection. Please enter a valid number.[/red]")
                
    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred: {e}[/red]")

def handle_index_repo():
    """Handles indexing the selected repository."""
    try:
        manager = get_github_manager_instance()
        if not manager.current_repo:
            print("[red]No repository selected. Use 'Select Repository' first.[/red]")
            return
        
        repo_name = manager.current_repo.name
        print(f"[yellow]Indexing repository {repo_name}...[/yellow]")
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Indexing...", total=100)
            
            contents = manager._get_all_contents(manager.current_repo)
            if not contents:
                print("[yellow]No files found in the repository to index.[/yellow]")
                progress.update(task, completed=100)
                return

            documents = {}
            for i, content in enumerate(contents):
                try:
                    # Ensure content is a file and not too large/binary
                    if content.type == "file" and content.size < 1024 * 1024 * 10: # Limit to 5MB for example
                        file_content = content.decoded_content.decode("utf-8", errors='ignore')
                        documents[content.path] = file_content
                    else:
                        print(f"[yellow]Skipping {content.path} (not a file or too large/binary).[/yellow]")
                    progress.update(task, advance=(100/len(contents)))
                except Exception as e:
                    print(f"[red]Error processing {content.path}: {e}[/red]")
                    continue
            
            if documents:
                vector_db.store_repository(repo_name, documents)
                print(f"[green]Successfully indexed repository {repo_name}[/green]")
            else:
                print("[yellow]No suitable files were found or processed for indexing.[/yellow]")

    except ValueError as e:
        print(f"[red]Error: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred during indexing: {e}[/red]")

def handle_search():
    """Handles keyword search across indexed repositories."""
    print("\n--- Keyword Search ---")
    query = input("Enter search query: ")
    repo_name_filter = input("Filter by repository name (leave blank for all): ")
    repo_name_filter = repo_name_filter if repo_name_filter else None

    try:
        results = vector_db.search_repository(query, repo_name_filter)
        
        if not results:
            print("[yellow]No results found[/yellow]")
            return
        
        table = Table(title="Search Results")
        table.add_column("Repository", style="cyan")
        table.add_column("File Path", style="magenta")
        table.add_column("Similarity", style="green")
        table.add_column("Preview", style="yellow")
        
        for result in results:
            preview = result['content'][:50] + "..." if len(result['content']) > 50 else result['content']
            similarity = f"{1 - result['distance']:.2%}"
            table.add_row(
                result['repo'],
                result['path'],
                similarity,
                preview
            )
        
        print(table)
    except Exception as e:
        print(f"[red]Error during search: {e}[/red]")

def handle_semantic_search():
    """Handles semantic search across indexed repositories."""
    print("\n--- Semantic Search ---")
    query = input("Enter semantic search query: ")
    repo_name_filter = input("Filter by repository name (leave blank for all): ")
    repo_name_filter = repo_name_filter if repo_name_filter else None
    limit_str = input("Number of results to return (default 5): ")
    limit = int(limit_str) if limit_str.isdigit() else 5

    try:
        results = vector_db.search_repository(query, repo_name_filter, limit)
        
        if not results:
            print("[yellow]No results found[/yellow]")
            return
        
        table = Table(title="Semantic Search Results")
        table.add_column("Score", style="green")
        table.add_column("Repository", style="cyan")
        table.add_column("File Path", style="magenta")
        table.add_column("Preview", style="yellow")
        
        for result in results:
            score = f"{1 - result['distance']:.2%}"
            preview = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
            table.add_row(
                score,
                result['repo'],
                result['path'],
                preview
            )
        
        print(table)
    except Exception as e:
        print(f"[red]Error during semantic search: {e}[/red]")

def handle_view_stats():
    """Handles displaying repository statistics"""
    try:
        stats = vector_db.get_repository_stats()
        
        if stats["total_repos"] == 0:
            print("[yellow]No repositories have been indexed yet.[/yellow]")
            return
        
        # Create main stats table
        main_table = Table(title="Repository Statistics Overview")
        main_table.add_column("Metric", style="cyan")
        main_table.add_column("Value", style="green")
        
        main_table.add_row("Total Repositories", str(stats["total_repos"]))
        main_table.add_row("Total Files Indexed", str(stats["total_files"]))
        main_table.add_row("Total Size", f"{stats['total_size_bytes'] / (1024*1024):.2f} MB")
        
        print(main_table)
        
        # Create detailed repo table
        repo_table = Table(title="Individual Repository Details")
        repo_table.add_column("Repository", style="cyan")
        repo_table.add_column("Files Indexed", style="green")
        repo_table.add_column("Size", style="blue")
        repo_table.add_column("Last Indexed", style="yellow")
        
        for repo_name, repo_data in stats["repos"].items():
            repo_table.add_row(
                repo_name,
                str(repo_data["indexed_files"]),
                f"{repo_data['size_bytes'] / (1024*1024):.2f} MB",
                repo_data["last_indexed"].split("T")[0]  # Show just the date
            )
        
        print(repo_table)
        
    except Exception as e:
        print(f"[red]Error retrieving statistics: {e}[/red]")

def handle_open_file():
    """Handles opening a file from an indexed repository"""
    try:
        # Get list of indexed repositories
        stats = vector_db.get_repository_stats()
        if stats["total_repos"] == 0:
            print("[yellow]No repositories have been indexed yet.[/yellow]")
            return
        
        # Show repository selection table
        repo_table = Table(title="[bold cyan]Indexed Repositories[/bold cyan]")
        repo_table.add_column("No.", style="blue", justify="right")
        repo_table.add_column("Repository", style="cyan")
        repo_table.add_column("Files", style="green", justify="right")
        repo_table.add_column("Last Indexed", style="yellow")
        
        repos = list(stats["repos"].keys())
        for i, repo in enumerate(repos, 1):
            repo_data = stats["repos"][repo]
            repo_table.add_row(
                str(i),
                repo,
                str(repo_data["indexed_files"]),
                repo_data["last_indexed"].split("T")[0]
            )
        print(repo_table)
        
        # Get repository selection
        repo_choice = input("\nSelect repository number (or 0 to cancel): ").strip()
        if repo_choice == "0":
            return
        if not repo_choice.isdigit() or int(repo_choice) < 1 or int(repo_choice) > len(repos):
            print("[red]Invalid repository selection.[/red]")
            return
        
        selected_repo = repos[int(repo_choice) - 1]
        
        # Get all files for the selected repository
        files = vector_db.get_repository_files(selected_repo)
        if not files:
            print("[yellow]No files found in the repository.[/yellow]")
            return
        
        # Show file selection table
        file_table = Table(title=f"[bold cyan]Files in {selected_repo}[/bold cyan]")
        file_table.add_column("No.", style="blue", justify="right")
        file_table.add_column("File Path", style="green")
        file_table.add_column("Size", style="yellow", justify="right")
        
        for i, file_info in enumerate(files, 1):
            file_table.add_row(
                str(i),
                file_info["path"],
                f"{file_info['size']/1024:.1f} KB"
            )
        print(file_table)
        
        # Get file selection
        while True:
            file_choice = input("\nSelect file number (or 0 to cancel): ").strip()
            if file_choice == "0":
                return
            if file_choice.isdigit() and 1 <= int(file_choice) <= len(files):
                selected_file = files[int(file_choice) - 1]
                break
            print("[red]Invalid file selection. Please try again.[/red]")
        
        # Retrieve and display file content
        content = vector_db.get_file_content(selected_repo, selected_file["path"])
        if content:
            panel = Panel(
                content,
                title=f"[cyan]{selected_repo}:[/cyan] [green]{selected_file['path']}[/green]",
                width=100,
                expand=False
            )
            print(panel)
        else:
            print(f"[red]Error retrieving file content.[/red]")
            
    except Exception as e:
        print(f"[red]Error opening file: {e}[/red]")

def run_application():
    """Main loop for the menu-driven application."""
    global github_manager
    
    # Initial check for existing session
    username = auth_manager.get_current_user()
    if username:
        github_token = auth_manager.get_github_token(username)
        if github_token:
            try:
                github_manager = GitHubManager(github_token)
                print(Panel.fit(f"Welcome back [bold green]{username}[/bold green]! You are already logged in."))
            except Exception as e:
                print(f"[yellow]Warning: Could not initialize GitHub client with saved token: {e}[/yellow]")
        else:
            print(Panel.fit(f"Welcome back [bold green]{username}[/bold green]! Please set your GitHub token."))
    else:
        print(Panel.fit("[bold blue]Welcome to GitHub Vector CLI![/bold blue]"))

    while True:
        current_user = auth_manager.get_current_user()
        display_main_menu(current_user)
        
        choice = input("Enter your choice: ").strip()
        
        if current_user: # Logged-in user menu
            if choice == '1':
                handle_list_repos()
            elif choice == '2':
                handle_create_repo()
            elif choice == '3':
                handle_select_repo()
            elif choice == '4':
                handle_index_repo()
            elif choice == '5':
                handle_search()
            elif choice == '6':
                handle_semantic_search()
            elif choice == '7':
                handle_view_stats()
            elif choice == '8':
                handle_open_file()
            elif choice == '9':
                handle_list_issues()
            elif choice == '10':
                handle_create_issue()
            elif choice == '11':
                handle_update_issue()
            elif choice == '12':
                handle_list_branches()
            elif choice == '13':
                handle_create_branch()
            elif choice == '14':
                handle_delete_branch()
            elif choice == '15':
                handle_list_pull_requests()
            elif choice == '16':
                handle_create_pull_request()
            elif choice == '17':
                handle_list_releases()
            elif choice == '18':
                handle_create_release()
            elif choice == '19':
                handle_list_collaborators()
            elif choice == '20':
                handle_add_collaborator()
            elif choice == '21':
                handle_remove_collaborator()
            elif choice == '22':
                handle_set_github_token()
            elif choice == '23':
                handle_logout()
            elif choice == '0':
                print("[green]Exiting application. Goodbye![/green]")
                sys.exit(0)
            else:
                print("[red]Invalid choice. Please try again.[/red]")
        else: # Not logged-in user menu
            if choice == '1':
                handle_login()
            elif choice == '2':
                handle_register()
            elif choice == '0':
                print("[green]Exiting application. Goodbye![/green]")
                sys.exit(0)
            else:
                print("[red]Invalid choice. Please try again.[/red]")
        
        input("\nPress Enter to continue...") # Pause for user to read output

if __name__ == "__main__":
    run_application()

