import torch
import torch.nn as nn

class NetworkTransformer(nn.Module):
    def __init__(self, input_dim=8, d_model=32, nhead=4, num_layers=2, num_classes=2):
        super().__init__()
        self.proj = nn.Linear(input_dim, d_model)
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, batch_first=True)
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.classifier = nn.Sequential(
            nn.Linear(d_model, 16),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(16, num_classes)
        )

    def forward(self, x):
        # x: (batch, seq_len, input_dim) or (batch, input_dim)
        if x.dim() == 2:
            x = x.unsqueeze(1)
        x = self.proj(x)
        x = self.encoder(x)
        x = x.mean(dim=1)
        return self.classifier(x)