def name_key(name: str) -> str:
    """The form a name is compared in: surrounding spaces and case are ignored.

    Player names and topic names are both compared this way.
    """
    return name.strip().casefold()
