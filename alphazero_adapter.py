"""Optional compatibility adapter for a legacy 3x3 Keras/HDF5 checkpoint.

The main path now uses the project's own PyTorch checkpoint. This adapter stays
available for users who already have a compatible legacy HDF5 file and do not
want to install TensorFlow.
"""

from pathlib import Path


_model = None
_device = None


def _find_model_path():
    root = Path(__file__).resolve().parent
    candidates = [
        root / "models" / "best-25eps-25sim-10epch.pth.tar",
        root / "models" / "best-25eps-25sim-10epch.h5",
        root / "models" / "tictactoe_alphazero.h5",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("没有找到可选的3x3兼容模型")


def _read_weight(h5_file, layer_name, suffix):
    """从Keras HDF5层组中递归读取一个数据集。"""
    group = h5_file[layer_name]
    matches = []

    def visit(name, item):
        if hasattr(item, "shape") and name.endswith(suffix):
            matches.append(item[()])

    group.visititems(visit)
    if len(matches) != 1:
        raise ValueError(f"无法唯一读取权重: {layer_name}/{suffix}")
    return matches[0]


def _build_model():
    """按AlphaZero General的Tic-Tac-Toe网络结构建立推理模型。"""
    import h5py
    import torch
    from torch import nn

    class AlphaZeroNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = nn.Conv2d(1, 512, 3, padding=1)
            self.bn1 = nn.BatchNorm2d(512)
            self.conv2 = nn.Conv2d(512, 512, 3, padding=1)
            self.bn2 = nn.BatchNorm2d(512)
            self.conv3 = nn.Conv2d(512, 512, 3, padding=1)
            self.bn3 = nn.BatchNorm2d(512)
            self.conv4 = nn.Conv2d(512, 512, 3)
            self.bn4 = nn.BatchNorm2d(512)
            self.fc1 = nn.Linear(512, 1024)
            self.bn5 = nn.BatchNorm1d(1024)
            self.fc2 = nn.Linear(1024, 512)
            self.bn6 = nn.BatchNorm1d(512)
            self.policy = nn.Linear(512, 10)
            self.value = nn.Linear(512, 1)

        def forward(self, x):
            x = torch.relu(self.bn1(self.conv1(x)))
            x = torch.relu(self.bn2(self.conv2(x)))
            x = torch.relu(self.bn3(self.conv3(x)))
            x = torch.relu(self.bn4(self.conv4(x)))
            x = torch.flatten(x, 1)
            x = torch.relu(self.bn5(self.fc1(x)))
            x = torch.relu(self.bn6(self.fc2(x)))
            policy = torch.softmax(self.policy(x), dim=1)
            value = torch.tanh(self.value(x))
            return policy, value

    model = AlphaZeroNet()
    with h5py.File(_find_model_path(), "r") as checkpoint:
        convolution_layers = [
            (model.conv1, model.bn1, "conv2d_5", "batch_normalization_7"),
            (model.conv2, model.bn2, "conv2d_6", "batch_normalization_8"),
            (model.conv3, model.bn3, "conv2d_7", "batch_normalization_9"),
            (model.conv4, model.bn4, "conv2d_8", "batch_normalization_10"),
        ]
        for convolution, batch_norm, conv_name, bn_name in convolution_layers:
            kernel = _read_weight(checkpoint, conv_name, "kernel:0")
            bias = _read_weight(checkpoint, conv_name, "bias:0")
            convolution.weight.data.copy_(
                torch.from_numpy(kernel).permute(3, 2, 0, 1)
            )
            convolution.bias.data.copy_(torch.from_numpy(bias))
            batch_norm.weight.data.copy_(
                torch.from_numpy(_read_weight(checkpoint, bn_name, "gamma:0"))
            )
            batch_norm.bias.data.copy_(
                torch.from_numpy(_read_weight(checkpoint, bn_name, "beta:0"))
            )
            batch_norm.running_mean.data.copy_(
                torch.from_numpy(_read_weight(checkpoint, bn_name, "moving_mean:0"))
            )
            batch_norm.running_var.data.copy_(
                torch.from_numpy(
                    _read_weight(checkpoint, bn_name, "moving_variance:0")
                )
            )

        dense_layers = [
            (model.fc1, "dense_3"),
            (model.fc2, "dense_4"),
            (model.policy, "pi"),
            (model.value, "v"),
        ]
        for layer, layer_name in dense_layers:
            kernel = _read_weight(checkpoint, layer_name, "kernel:0")
            bias = _read_weight(checkpoint, layer_name, "bias:0")
            layer.weight.data.copy_(torch.from_numpy(kernel).transpose(0, 1))
            layer.bias.data.copy_(torch.from_numpy(bias))

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return model.to(device).eval(), device


def model_move(board, mark):
    """编码棋盘，调用兼容模型，并返回概率最高的合法动作。"""
    global _model, _device
    import torch

    if _model is None:
        _model, _device = _build_model()

    encoded = []
    for cell in board:
        if cell == mark:
            encoded.append(1.0)
        elif cell == " ":
            encoded.append(0.0)
        else:
            encoded.append(-1.0)

    tensor = torch.tensor(encoded, dtype=torch.float32, device=_device).reshape(
        1, 1, 3, 3
    )
    legal_moves = [index for index, cell in enumerate(board) if cell == " "]
    if not legal_moves:
        raise ValueError("当前棋盘没有合法动作")
    with torch.no_grad():
        policy, _ = _model(tensor)
    return max(legal_moves, key=lambda move: float(policy[0, move].item()))
