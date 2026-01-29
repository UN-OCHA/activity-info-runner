import importlib
import inspect
import pkgutil

from aiocache import cached

import scripts.scripts as script_package
from scripts.boundaries import materialize_boundary
from scripts.changeset import generate_changeset
from scripts.script import AIRScript


@cached()
async def get_scripts():
    """
    Return a list of all AIRScript subclasses.
    """
    subclasses = []
    for loader, module_name, is_pkg in pkgutil.iter_modules(script_package.__path__):
        full_module_name = f'scripts.scripts.{module_name}'
        module = importlib.import_module(full_module_name)
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, AIRScript) and obj is not AIRScript:
                subclasses.append(obj)
    return subclasses


def get_script_activities(cls):
    """
    Return a list of Temporal activity method names for the given AIRScript subclass.
    Includes inherited methods.
    """
    activities = []
    instance = cls()
    # Loop over all attributes in the class and base classes
    for name in dir(cls):
        # Get the unbound function from the class (could be inherited)
        method = getattr(instance, name, None)
        if callable(method):
            # Temporal decorator sets __temporal_activity_definition on the original function
            # Check both function and underlying __func__ for methods
            if getattr(method, "__temporal_activity_definition", None) or getattr(getattr(method, "__func__", None),
                                                                                  "__temporal_activity_definition",
                                                                                  None):
                activities.append(method)
    return activities


async def get_activities():
    """
    Returns a list of Temporal activity methods for all AIRScript subclasses.
    """
    # Initialize with generic scripts Gen1 and Gen2
    all_activities = [materialize_boundary, generate_changeset]
    for cls in await get_scripts():
        all_activities.extend(get_script_activities(cls))
    return all_activities
