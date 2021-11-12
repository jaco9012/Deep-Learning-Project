{
  "nbformat": 4,
  "nbformat_minor": 0,
  "metadata": {
    "colab": {
      "name": "getting-started-ppo.ipynb",
      "provenance": [],
      "collapsed_sections": [],
      "include_colab_link": true
    },
    "kernelspec": {
      "name": "python3",
      "display_name": "Python 3"
    },
    "accelerator": "GPU"
  },
  "cells": [
    {
      "cell_type": "markdown",
      "metadata": {
        "id": "view-in-github",
        "colab_type": "text"
      },
      "source": [
        "<a href=\"https://colab.research.google.com/github/jaco9012/Deep-Learning-Project/blob/main/getting_started_ppo.py\" target=\"_parent\"><img src=\"https://colab.research.google.com/assets/colab-badge.svg\" alt=\"Open In Colab\"/></a>"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {
        "id": "K1_WKdcrI6w3"
      },
      "source": [
        "# Getting started with PPO and ProcGen"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {
        "id": "z7LP1JU3I-d4"
      },
      "source": [
        "Here's a bit of code that should help you get started on your projects.\n",
        "\n",
        "The cell below installs `procgen` and downloads a small `utils.py` script that contains some utility functions. You may want to inspect the file for more details."
      ]
    },
    {
      "cell_type": "code",
      "metadata": {
        "id": "KdpZ4lmFHtD8"
      },
      "source": [
        "!pip install procgen\n",
        "!wget https://raw.githubusercontent.com/nicklashansen/ppo-procgen-utils/main/utils.py"
      ],
      "execution_count": null,
      "outputs": []
    },
    {
      "cell_type": "markdown",
      "metadata": {
        "id": "Bn2rkllGJPtZ"
      },
      "source": [
        "Hyperparameters. These values should be a good starting point. You can modify them later once you have a working implementation."
      ]
    },
    {
      "cell_type": "code",
      "metadata": {
        "id": "8Z8P1ehENCwc"
      },
      "source": [
        "# Hyperparameters\n",
        "total_steps = 8e6\n",
        "num_envs = 32\n",
        "num_levels = 10\n",
        "num_steps = 256\n",
        "num_epochs = 3\n",
        "batch_size = 512\n",
        "eps = .2\n",
        "grad_eps = .5\n",
        "value_coef = .5\n",
        "entropy_coef = .01"
      ],
      "execution_count": null,
      "outputs": []
    },
    {
      "cell_type": "markdown",
      "metadata": {
        "id": "JxRWy_T9JY4M"
      },
      "source": [
        "Network definitions. We have defined a policy network for you in advance. It uses the popular `NatureDQN` encoder architecture (see below), while policy and value functions are linear projections from the encodings. There is plenty of opportunity to experiment with architectures, so feel free to do that! Perhaps implement the `Impala` encoder from [this paper](https://arxiv.org/pdf/1802.01561.pdf) (perhaps minus the LSTM)."
      ]
    },
    {
      "cell_type": "code",
      "metadata": {
        "id": "yTBV9xpKpEFa"
      },
      "source": [
        "import torch\n",
        "import torch.nn as nn\n",
        "import torch.nn.functional as F\n",
        "from utils import make_env, Storage, orthogonal_init\n",
        "\n",
        "\n",
        "class Flatten(nn.Module):\n",
        "    def forward(self, x):\n",
        "        return x.view(x.size(0), -1)\n",
        "\n",
        "\n",
        "class Encoder(nn.Module):\n",
        "  def __init__(self, in_channels, feature_dim):\n",
        "    super().__init__()\n",
        "    self.layers = nn.Sequential(\n",
        "        nn.Conv2d(in_channels=in_channels, out_channels=32, kernel_size=8, stride=4), nn.ReLU(),\n",
        "        nn.Conv2d(in_channels=32, out_channels=64, kernel_size=4, stride=2), nn.ReLU(),\n",
        "        nn.Conv2d(in_channels=64, out_channels=64, kernel_size=3, stride=1), nn.ReLU(),\n",
        "        Flatten(),\n",
        "        nn.Linear(in_features=1024, out_features=feature_dim), nn.ReLU()\n",
        "    )\n",
        "    self.apply(orthogonal_init)\n",
        "\n",
        "  def forward(self, x):\n",
        "    return self.layers(x)\n",
        "\n",
        "\n",
        "class Policy(nn.Module):\n",
        "  def __init__(self, encoder, feature_dim, num_actions):\n",
        "    super().__init__()\n",
        "    self.encoder = encoder\n",
        "    self.policy = orthogonal_init(nn.Linear(feature_dim, num_actions), gain=.01)\n",
        "    self.value = orthogonal_init(nn.Linear(feature_dim, 1), gain=1.)\n",
        "\n",
        "  def act(self, x):\n",
        "    with torch.no_grad():\n",
        "      x = x.cuda().contiguous()\n",
        "      dist, value = self.forward(x)\n",
        "      action = dist.sample()\n",
        "      log_prob = dist.log_prob(action)\n",
        "    \n",
        "    return action.cpu(), log_prob.cpu(), value.cpu()\n",
        "\n",
        "  def forward(self, x):\n",
        "    x = self.encoder(x)\n",
        "    logits = self.policy(x)\n",
        "    value = self.value(x).squeeze(1)\n",
        "    dist = torch.distributions.Categorical(logits=logits)\n",
        "\n",
        "    return dist, value\n",
        "\n",
        "\n",
        "# Define environment\n",
        "# check the utils.py file for info on arguments\n",
        "env = make_env(num_envs, num_levels=num_levels)\n",
        "print('Observation space:', env.observation_space)\n",
        "print('Action space:', env.action_space.n)\n",
        "\n",
        "# Define network\n",
        "encoder = \n",
        "policy = \n",
        "policy.cuda()\n",
        "\n",
        "# Define optimizer\n",
        "# these are reasonable values but probably not optimal\n",
        "optimizer = torch.optim.Adam(policy.parameters(), lr=5e-4, eps=1e-5)\n",
        "\n",
        "# Define temporary storage\n",
        "# we use this to collect transitions during each iteration\n",
        "storage = Storage(\n",
        "    env.observation_space.shape,\n",
        "    num_steps,\n",
        "    num_envs\n",
        ")\n",
        "\n",
        "# Run training\n",
        "obs = env.reset()\n",
        "step = 0\n",
        "while step < total_steps:\n",
        "\n",
        "  # Use policy to collect data for num_steps steps\n",
        "  policy.eval()\n",
        "  for _ in range(num_steps):\n",
        "    # Use policy\n",
        "    action, log_prob, value = policy.act(obs)\n",
        "    \n",
        "    # Take step in environment\n",
        "    next_obs, reward, done, info = env.step(action)\n",
        "\n",
        "    # Store data\n",
        "    storage.store(obs, action, reward, done, info, log_prob, value)\n",
        "    \n",
        "    # Update current observation\n",
        "    obs = next_obs\n",
        "\n",
        "  # Add the last observation to collected data\n",
        "  _, _, value = policy.act(obs)\n",
        "  storage.store_last(obs, value)\n",
        "\n",
        "  # Compute return and advantage\n",
        "  storage.compute_return_advantage()\n",
        "\n",
        "  # Optimize policy\n",
        "  policy.train()\n",
        "  for epoch in range(num_epochs):\n",
        "\n",
        "    # Iterate over batches of transitions\n",
        "    generator = storage.get_generator(batch_size)\n",
        "    for batch in generator:\n",
        "      b_obs, b_action, b_log_prob, b_value, b_returns, b_advantage = batch\n",
        "\n",
        "      # Get current policy outputs\n",
        "      new_dist, new_value = policy(b_obs)\n",
        "      new_log_prob = new_dist.log_prob(b_action)\n",
        "\n",
        "      # Clipped policy objective\n",
        "      pi_loss = \n",
        "\n",
        "      # Clipped value function objective\n",
        "      value_loss = \n",
        "\n",
        "      # Entropy loss\n",
        "      entropy_loss = \n",
        "\n",
        "      # Backpropagate losses\n",
        "      loss = \n",
        "      loss.backward()\n",
        "\n",
        "      # Clip gradients\n",
        "      torch.nn.utils.clip_grad_norm_(policy.parameters(), grad_eps)\n",
        "\n",
        "      # Update policy\n",
        "      optimizer.step()\n",
        "      optimizer.zero_grad()\n",
        "\n",
        "  # Update stats\n",
        "  step += num_envs * num_steps\n",
        "  print(f'Step: {step}\\tMean reward: {storage.get_reward()}')\n",
        "\n",
        "print('Completed training!')\n",
        "torch.save(policy.state_dict, 'checkpoint.pt')"
      ],
      "execution_count": null,
      "outputs": []
    },
    {
      "cell_type": "markdown",
      "metadata": {
        "id": "RAZrWuVGLTu-"
      },
      "source": [
        "Below cell can be used for policy evaluation and saves an episode to mp4 for you to view."
      ]
    },
    {
      "cell_type": "code",
      "metadata": {
        "id": "2zecOCkd7Jzt"
      },
      "source": [
        "import imageio\n",
        "\n",
        "# Make evaluation environment\n",
        "eval_env = make_env(num_envs, start_level=num_levels, num_levels=num_levels)\n",
        "obs = eval_env.reset()\n",
        "\n",
        "frames = []\n",
        "total_reward = []\n",
        "\n",
        "# Evaluate policy\n",
        "policy.eval()\n",
        "for _ in range(512):\n",
        "\n",
        "  # Use policy\n",
        "  action, log_prob, value = policy.act(obs)\n",
        "\n",
        "  # Take step in environment\n",
        "  obs, reward, done, info = eval_env.step(action)\n",
        "  total_reward.append(torch.Tensor(reward))\n",
        "\n",
        "  # Render environment and store\n",
        "  frame = (torch.Tensor(eval_env.render(mode='rgb_array'))*255.).byte()\n",
        "  frames.append(frame)\n",
        "\n",
        "# Calculate average return\n",
        "total_reward = torch.stack(total_reward).sum(0).mean(0)\n",
        "print('Average return:', total_reward)\n",
        "\n",
        "# Save frames as video\n",
        "frames = torch.stack(frames)\n",
        "imageio.mimsave('vid.mp4', frames, fps=25)"
      ],
      "execution_count": null,
      "outputs": []
    }
  ]
}