"""Small CPU-only research challenger; never imported by ordinary ScanWeave."""
import torch
from torch import nn
from torch.nn import functional as functional


class Encoder(nn.Module):
    def __init__(self):
        super().__init__()
        layers, previous = [], 1
        for channels, stride in [(16, 1), (32, 2), (64, 2), (64, 2)]:
            layers.extend([nn.Conv2d(previous, channels, 3, stride=stride, padding=1),
                           nn.GroupNorm(4, channels), nn.ReLU()])
            previous = channels
        self.features = nn.Sequential(*layers, nn.AdaptiveAvgPool2d(1))
        self.project = nn.Linear(64, 48)

    def forward(self, images):
        return functional.normalize(self.project(self.features(images).flatten(1)), dim=1)


def training_loss(embeddings, logits, targets, characters, weights):
    ce = (functional.cross_entropy(logits, targets, reduction='none')*weights).mean()
    similarity = embeddings @ embeddings.T/.1
    diagonal = torch.eye(len(embeddings), dtype=torch.bool)
    positive = (targets[:, None] == targets[None, :]) & (characters[:, None] != characters[None, :]) & ~diagonal
    probability = similarity.masked_fill(diagonal, -1e9).log_softmax(dim=1)
    denominator = positive.sum(1)
    valid = denominator > 0
    contrast = -(probability*positive).sum(1)[valid]/denominator[valid]
    return ce + .2*(contrast.mean() if valid.any() else embeddings.sum()*0)
