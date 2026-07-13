from typing import Optional

import torch
from torch import Tensor, nn
from torch.optim import SGD


class SimpleNet(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 64, num_classes: int = 2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x: Tensor) -> Tensor:
        return self.net(x)

    def get_flattened_grad(self) -> Tensor:
        grads = []
        for p in self.parameters():
            if p.grad is not None:
                grads.append(p.grad.data.flatten())
        if not grads:
            return torch.zeros(0)
        return torch.cat(grads)

    def flattened_params(self) -> Tensor:
        return torch.cat([p.data.flatten() for p in self.parameters()])

    def set_flattened_params(self, flat: Tensor):
        idx = 0
        for p in self.parameters():
            n = p.numel()
            p.data.copy_(flat[idx:idx + n].reshape(p.shape))
            idx += n

    def num_params(self) -> int:
        return sum(p.numel() for p in self.parameters())


class SingleModel:
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 64,
        num_classes: int = 2,
        learning_rate: float = 1e-2,
        device: Optional[torch.device] = None,
    ):
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.device = device or torch.device("cpu")
        self.model = SimpleNet(input_dim, hidden_dim, num_classes).to(self.device)
        self.learning_rate = learning_rate

    def train(
        self,
        features: Tensor,
        labels: Tensor,
        epochs: int = 100,
        verbose: bool = False,
    ):
        self.model.train()
        optimizer = SGD(self.model.parameters(), lr=self.learning_rate, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()
        features, labels = features.to(self.device), labels.to(self.device)

        for epoch in range(epochs):
            optimizer.zero_grad()
            outputs = self.model(features)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

    def predict(self, features: Tensor) -> Tensor:
        self.model.eval()
        with torch.no_grad():
            logits = self.model(features.to(self.device))
            return logits.softmax(dim=-1).argmax(dim=-1)

    def predict_proba(self, features: Tensor) -> Tensor:
        self.model.eval()
        with torch.no_grad():
            logits = self.model(features.to(self.device))
            return logits.softmax(dim=-1)

    def predict_logits(self, features: Tensor) -> Tensor:
        self.model.eval()
        with torch.no_grad():
            return self.model(features.to(self.device))

    def hessian_diag(self, features: Tensor, labels: Tensor) -> Tensor:
        self.model.train()
        features, labels = features.to(self.device), labels.to(self.device)
        outputs = self.model(features)
        loss = nn.CrossEntropyLoss(reduction="none")(outputs, labels)
        grads = []
        for l in loss:
            self.model.zero_grad()
            l.backward(retain_graph=True)
            g = self.model.get_flattened_grad().clone()
            grads.append(g)
        stacked = torch.stack(grads)
        hessian_diag = (stacked ** 2).sum(dim=0)
        return hessian_diag

    def influence_scores(
        self,
        train_features: Tensor,
        train_labels: Tensor,
        target_features: Tensor,
        target_labels: Tensor,
        damping: float = 1e-4,
    ) -> Tensor:
        self.model.train()
        train_features, train_labels = train_features.to(self.device), train_labels.to(self.device)
        target_features, target_labels = target_features.to(self.device), target_labels.to(self.device)

        train_outputs = self.model(train_features)
        train_losses = nn.CrossEntropyLoss(reduction="none")(train_outputs, train_labels)

        target_outputs = self.model(target_features)
        target_losses = nn.CrossEntropyLoss(reduction="none")(target_outputs, target_labels)

        train_grads = []
        for loss in train_losses:
            self.model.zero_grad()
            loss.backward(retain_graph=True)
            train_grads.append(self.model.get_flattened_grad().clone())

        target_grads = []
        for loss in target_losses:
            self.model.zero_grad()
            loss.backward(retain_graph=True)
            target_grads.append(self.model.get_flattened_grad().clone())

        train_grads_t = torch.stack(train_grads)
        target_grads_t = torch.stack(target_grads)

        ggn_matrix = train_grads_t.T @ train_grads_t / len(train_losses)
        reg_ggn = ggn_matrix + damping * torch.eye(ggn_matrix.size(0), device=self.device)

        try:
            inv_ggn = torch.linalg.inv(reg_ggn)
        except RuntimeError:
            inv_ggn = torch.linalg.pinv(reg_ggn)

        influences = []
        for tg in target_grads_t:
            influence = tg @ inv_ggn @ train_grads_t.T
            influences.append(influence)
        return torch.stack(influences).mean(dim=1)
