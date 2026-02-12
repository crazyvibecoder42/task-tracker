"""
Project-level permission checking utilities.

This module provides functions for checking whether a user has permission to access
or modify specific projects based on their role and project membership.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models import User, Project

logger = logging.getLogger(__name__)


def check_project_permission(
    user: User, project_id: int, required_role: str, db: Session
) -> bool:
    """
    Check if a user has the required role for a specific project.

    Permission sources (in order):
    1. Global admin role (bypasses all checks)
    2. Team-based role (if project belongs to a team)
       - Team admin → Project owner
       - Team member → Project editor
    3. Direct project membership (for personal projects)

    Args:
        user: User object to check permissions for
        project_id: ID of the project to check access for
        required_role: Minimum role required ('viewer', 'editor', 'owner', 'admin')
        db: Database session

    Returns:
        True if user has permission, False otherwise

    Example:
        >>> has_access = check_project_permission(user, 42, "editor", db)
        >>> if not has_access:
        ...     raise HTTPException(status_code=403, detail="Access denied")
    """
    logger.debug(
        f"Checking project permission for user {user.id}, "
        f"project {project_id}, required_role: {required_role}"
    )

    # Import here to avoid circular dependency
    from models import ProjectMember, TeamMember

    # Admin users have access to all projects
    user_role = getattr(user, "role", "editor")
    if user_role == "admin":
        logger.debug(f"User {user.id} is admin, granting access")
        return True

    # Role hierarchy for project permissions
    role_hierarchy = {"viewer": 0, "editor": 1, "owner": 2, "admin": 3}
    required_level = role_hierarchy.get(required_role, 0)

    # Check if project belongs to a team
    project = db.query(Project).filter(Project.id == project_id).first()
    if project and project.team_id:
        # Team-based permission check (EXCLUSIVE - no ProjectMember fallback)
        team_membership = (
            db.query(TeamMember)
            .filter(
                TeamMember.team_id == project.team_id,
                TeamMember.user_id == user.id
            )
            .first()
        )

        if not team_membership:
            # For team projects, no team membership = no access
            logger.info(f"User {user.id} is not a member of team {project.team_id}, access denied to project {project_id}")
            return False

        # Map team role to project role
        # Team admin → Project owner
        # Team member → Project editor
        team_role_mapping = {
            "admin": "owner",
            "member": "editor"
        }
        effective_project_role = team_role_mapping.get(team_membership.role, "editor")
        member_level = role_hierarchy.get(effective_project_role, 0)

        has_permission = member_level >= required_level

        if has_permission:
            logger.debug(
                f"User {user.id} has team role '{team_membership.role}' "
                f"(effective project role: '{effective_project_role}') via team {project.team_id}, "
                f"permission granted for required role '{required_role}'"
            )
        else:
            logger.info(
                f"User {user.id} has team role '{team_membership.role}' "
                f"(effective project role: '{effective_project_role}') via team {project.team_id}, "
                f"but '{required_role}' is required"
            )

        return has_permission

    # Fallback to direct project membership (personal projects)
    membership = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user.id
        )
        .first()
    )

    if membership is None:
        logger.info(f"User {user.id} has no membership in project {project_id}")
        return False

    member_level = role_hierarchy.get(membership.role, 0)
    has_permission = member_level >= required_level

    if has_permission:
        logger.debug(
            f"User {user.id} has role '{membership.role}' in project {project_id}, "
            f"permission granted for required role '{required_role}'"
        )
    else:
        logger.info(
            f"User {user.id} has role '{membership.role}' in project {project_id}, "
            f"but '{required_role}' is required"
        )

    return has_permission


def has_project_access(user: User, project_id: int, db: Session) -> bool:
    """
    Check if a user has any access to a project (minimum viewer role).

    This is a convenience wrapper around check_project_permission for the common case
    of checking whether a user can view a project.

    Args:
        user: User object to check permissions for
        project_id: ID of the project to check access for
        db: Database session

    Returns:
        True if user has any access level, False otherwise

    Example:
        >>> if not has_project_access(user, project_id, db):
        ...     raise HTTPException(status_code=404, detail="Project not found")
    """
    logger.debug(f"Checking if user {user.id} has access to project {project_id}")
    return check_project_permission(user, project_id, "viewer", db)


def require_project_permission(
    user: User, project_id: int, required_role: str, db: Session
) -> None:
    """
    Require a user to have a specific role for a project, or raise an exception.

    This is a convenience function that checks permissions and raises HTTPException
    if the check fails.

    Args:
        user: User object to check permissions for
        project_id: ID of the project to check access for
        required_role: Minimum role required ('viewer', 'editor', 'owner', 'admin')
        db: Database session

    Raises:
        HTTPException: 404 if project not found or user has no access
        HTTPException: 403 if user has access but insufficient role

    Example:
        >>> require_project_permission(user, project_id, "editor", db)
        >>> # If we get here, user has editor or higher role
    """
    logger.debug(
        f"Requiring {required_role} permission for user {user.id} on project {project_id}"
    )

    # First check if project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        logger.info(f"Project {project_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    # Check if user has any access
    if not has_project_access(user, project_id, db):
        logger.info(
            f"User {user.id} has no access to project {project_id}, returning 404"
        )
        # Return 404 instead of 403 to avoid leaking project existence
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    # Check if user has required role
    if not check_project_permission(user, project_id, required_role, db):
        logger.info(
            f"User {user.id} has insufficient permissions for project {project_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required role: {required_role}",
        )

    logger.debug(f"Permission check passed for user {user.id} on project {project_id}")


def get_user_projects(user: User, db: Session) -> list:
    """
    Get all projects that a user has access to via direct membership OR team membership.

    Args:
        user: User object to get projects for
        db: Database session

    Returns:
        List of project IDs the user has access to

    Example:
        >>> project_ids = get_user_projects(user, db)
        >>> tasks = db.query(Task).filter(Task.project_id.in_(project_ids)).all()
    """
    logger.debug(f"Getting projects for user {user.id}")

    # Import here to avoid circular dependency
    from models import ProjectMember, TeamMember

    # Admin users have access to all projects
    user_role = getattr(user, "role", "editor")
    if user_role == "admin":
        logger.debug(f"User {user.id} is admin, returning all projects")
        all_projects = db.query(Project.id).all()
        return [p.id for p in all_projects]

    project_ids = set()

    # Source 1: Direct project membership (personal projects)
    direct_memberships = (
        db.query(ProjectMember.project_id)
        .filter(ProjectMember.user_id == user.id)
        .all()
    )
    project_ids.update([m.project_id for m in direct_memberships])
    logger.debug(f"User {user.id} has {len(direct_memberships)} direct project memberships")

    # Source 2: Team membership (team projects - auto-join)
    user_team_ids = (
        db.query(TeamMember.team_id)
        .filter(TeamMember.user_id == user.id)
        .all()
    )
    team_ids = [tm.team_id for tm in user_team_ids]

    if team_ids:
        team_projects = (
            db.query(Project.id)
            .filter(Project.team_id.in_(team_ids))
            .all()
        )
        project_ids.update([p.id for p in team_projects])
        logger.debug(f"User {user.id} has access to {len(team_projects)} team projects via {len(team_ids)} teams")

    logger.debug(f"User {user.id} has access to {len(project_ids)} total projects")
    return list(project_ids)


def check_team_permission(
    user: User, team_id: int, required_role: str, db: Session
) -> bool:
    """
    Check if a user has the required role for a specific team.

    Args:
        user: User object to check permissions for
        team_id: ID of the team to check access for
        required_role: Minimum role required ('member' or 'admin')
        db: Database session

    Returns:
        True if user has permission, False otherwise

    Example:
        >>> has_access = check_team_permission(user, 5, "admin", db)
        >>> if not has_access:
        ...     raise HTTPException(status_code=403, detail="Admin access required")
    """
    logger.debug(
        f"Checking team permission for user {user.id}, "
        f"team {team_id}, required_role: {required_role}"
    )

    # Import here to avoid circular dependency
    from models import TeamMember

    # Admin users have access to all teams
    user_role = getattr(user, "role", "editor")
    if user_role == "admin":
        logger.debug(f"User {user.id} is global admin, granting access")
        return True

    # Check team membership
    membership = (
        db.query(TeamMember)
        .filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user.id
        )
        .first()
    )

    if membership is None:
        logger.info(f"User {user.id} has no membership in team {team_id}")
        return False

    # Role hierarchy for team permissions
    role_hierarchy = {"member": 0, "admin": 1}

    member_level = role_hierarchy.get(membership.role, 0)
    required_level = role_hierarchy.get(required_role, 0)

    has_permission = member_level >= required_level

    if has_permission:
        logger.debug(
            f"User {user.id} has role '{membership.role}' in team {team_id}, "
            f"permission granted for required role '{required_role}'"
        )
    else:
        logger.info(
            f"User {user.id} has role '{membership.role}' in team {team_id}, "
            f"but '{required_role}' is required"
        )

    return has_permission


def require_team_permission(
    user: User, team_id: int, required_role: str, db: Session
) -> None:
    """
    Require a user to have a specific role for a team, or raise an exception.

    Args:
        user: User object to check permissions for
        team_id: ID of the team to check access for
        required_role: Minimum role required ('member' or 'admin')
        db: Database session

    Raises:
        HTTPException: 404 if team not found or user has no access
        HTTPException: 403 if user has access but insufficient role

    Example:
        >>> require_team_permission(user, team_id, "admin", db)
        >>> # If we get here, user has admin role in team
    """
    logger.debug(
        f"Requiring {required_role} permission for user {user.id} on team {team_id}"
    )

    # Import here to avoid circular dependency
    from models import Team

    # First check if team exists
    team = db.query(Team).filter(Team.id == team_id).first()
    if team is None:
        logger.info(f"Team {team_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )

    # Check if user has any access
    if not check_team_permission(user, team_id, "member", db):
        logger.info(
            f"User {user.id} has no access to team {team_id}, returning 404"
        )
        # Return 404 instead of 403 to avoid leaking team existence
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )

    # Check if user has required role
    if not check_team_permission(user, team_id, required_role, db):
        logger.info(
            f"User {user.id} has insufficient permissions for team {team_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required role: {required_role}",
        )

    logger.debug(f"Permission check passed for user {user.id} on team {team_id}")
