from __future__ import annotations

import logging
import torch
import numpy as np
from pathlib import Path
from larrak2.gear.manufacturability_limits import PROFILE_NAMES
# We need the model class definition or same structure
import torch.nn as nn

class MachiningSurrogateNet(nn.Module):
    def __init__(self, input_dim, output_dim=4):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, output_dim)
        )
        
    def forward(self, x):
        return self.net(x)

class MachiningInference:
    def __init__(self, model_path: str = "machining_surrogate.pth"):
        self.model = None
        self.model_path = model_path
        self.shape_map = {name: i for i, name in enumerate(PROFILE_NAMES)}
        self.input_dim = 2 + len(PROFILE_NAMES)
        
    def load(self):
        if self.model is None:
            try:
                # Locate model relative to this file
                # self.model_path is default "machining_surrogate.pth" (relative)
                # If it's just a filename, look in same dir as this file.
                p = Path(self.model_path)
                if not p.is_absolute():
                     p = Path(__file__).parent / p.name
                
                if not p.exists():
                     logging.getLogger(__name__).warning(f"Machining surrogate model not found at {p}")
                     return

                self.model = MachiningSurrogateNet(self.input_dim)
                self.model.load_state_dict(torch.load(p, map_location="cpu"))
                self.model.eval()
            except Exception as e:
                logging.getLogger(__name__).warning(f"Failed to load machining surrogate: {e}")
                self.model = None

    def predict(self, duration_deg: float, amplitude: float, shape_name: str):
        if self.model is None:
            self.load()
            if self.model is None:
                return 0.0, 0.0, 0.0, 0.0 # BMax, TMin, HoleD, HoleC
                
        # Normalize
        norm_dur = duration_deg / 360.0
        norm_amp = (amplitude + 1.5) / 5.5
        
        # OneHot
        shape_idx = self.shape_map.get(shape_name, 0)
        one_hot = [0.0] * len(PROFILE_NAMES)
        if shape_idx < len(one_hot):
            one_hot[shape_idx] = 1.0
            
        x = torch.tensor([[norm_dur, norm_amp] + one_hot], dtype=torch.float32)
        
        with torch.no_grad():
            y = self.model(x).numpy()[0]
            
        # TMin, BMax, HoleD, HoleC
        return float(y[0]), float(y[1]), float(y[2]), float(y[3])

_ENGINE = None

def get_machining_engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = MachiningInference()
    return _ENGINE
