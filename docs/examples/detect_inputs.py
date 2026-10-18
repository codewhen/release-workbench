"""Read-only discovery example: stdout is one JSON object, never a workflow run."""

import json
import os

print(
    json.dumps(
        {
            "target": [{"value": ".", "label": "Current project", "automatic": True}],
            "workers": [{"value": min(os.cpu_count() or 1, 4), "label": "Suggested worker count"}],
            "profile": [
                {"value": "quick", "label": "Quick checks", "automatic": False},
                {"value": "full", "label": "Full checks", "automatic": False},
            ],
            "warnings": ["Choose a profile. This demonstration does not run test commands."],
        }
    )
)
