"""
"""
__all__ = (
    "simplify_labels",
)

def simplify_labels(full_labels: list = None, keywords: list | dict = None):
    """
    """
    Simplified_Labels = []
    for label in full_labels:
        # Avoid error with upper/lower letters
        Lower_Label = label.lower()

        # Add the new label and its units if keywords is a dict
        if isinstance(keywords, dict):
            Match = next(
                ("{} {}".format(key, units) for key, units in keywords.items() if key.lower() in Lower_Label), label
            )

        # Add only the new label if keywords is a list
        else:
            Match = next(
                (key for key in keywords if key.lower() in Lower_Label), label
            )

        # Append the label
        Simplified_Labels.append(Match)

    # Return the list of simplified labels
    return Simplified_Labels