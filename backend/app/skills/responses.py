from app.skills.errors import SkillError


def success_response(skill: str, data: dict) -> dict:
    """Canonical success shape every Skill.run() should return."""
    return {"skill": skill, "status": "ok", "data": data}


def error_response(skill: str, exc: Exception) -> dict:
    """
    Canonical error shape SkillService returns when a skill raises.
    Any exception is accepted (not just SkillError) so an unexpected
    bug inside a skill still comes back as a normalized, non-retryable
    failure instead of crashing the caller.
    """
    retryable = exc.retryable if isinstance(exc, SkillError) else False
    return {
        "skill": skill,
        "status": "error",
        "error": {
            "type": type(exc).__name__,
            "message": str(exc),
            "retryable": retryable,
        },
    }
