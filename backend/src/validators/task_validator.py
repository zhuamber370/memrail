from src.schemas import TaskPatch


def ensure_patch_has_fields(payload: TaskPatch) -> None:
    if not payload.model_dump(exclude_unset=True):
        raise ValueError("at least one field must be provided")
