# -*- coding: utf-8 -*-

# Network definitions. 
# We have defined a policy network for you in advance. It uses the popular `NatureDQN` encoder architecture (see below),
# while policy and value functions are linear projections from the encodings. There is plenty of opportunity to experiment with architectures,
# so feel free to do that! Perhaps implement the `Impala` encoder from [this paper](https://arxiv.org/pdf/1802.01561.pdf) (perhaps minus the LSTM).


# from math import gamma
from math import sqrt, exp
from random import random, sample
import torch
import torch.nn as nn
import torch.nn.functional as F
from utils import make_env, Storage, orthogonal_init
from labml_nn.rl.ppo import ClippedPPOLoss, ClippedValueFunctionLoss

# Hyperparameters
savename="baseline_v5.pt"
use_background = True
total_steps = 20e6
num_envs = 64
num_levels = 200 # 0 = unlimited levels
num_steps = 256
num_epochs = 3
batch_size = 8
eps = .2
eps_end = 0.05
eps_start = 0.9
eps_decay = 10e6
grad_eps = .5
clip_value = .2
value_coef = .5
entropy_coef = .01
gamma = 0.99

class Flatten(nn.Module):
    def forward(self, x):
        return x.view(x.size(0), -1)

class Encoder(nn.Module):
  def __init__(self, in_channels, feature_dim):
    super().__init__()
    self.layers = nn.Sequential(
        nn.Conv2d(in_channels=in_channels, out_channels=32, kernel_size=8, stride=4), nn.ReLU(),
        nn.Conv2d(in_channels=32, out_channels=64, kernel_size=4, stride=2), nn.ReLU(),
        nn.Conv2d(in_channels=64, out_channels=64, kernel_size=3, stride=1), nn.ReLU(),
        Flatten(),
        nn.Linear(in_features=1024, out_features=feature_dim), nn.ReLU()
    )
    self.apply(orthogonal_init)

  def forward(self, x):
    return self.layers(x)

class Policy(nn.Module):
  def __init__(self, encoder, feature_dim, num_actions):
    super().__init__()
    self.encoder = encoder
    self.policy = orthogonal_init(nn.Linear(feature_dim, num_actions), gain=.01)
    self.value = orthogonal_init(nn.Linear(feature_dim, 1), gain=1.)

  def act(self, x):
    with torch.no_grad():
      x = x.cuda().contiguous()
      dist, value = self.forward(x)
      action = dist.sample()
      log_prob = dist.log_prob(action)    
    return action.cpu(), log_prob.cpu(), value.cpu()

  def act_greedy(self, x):
    with torch.no_grad():
      x = x.cuda().contiguous()
      dist, value = self.forward(x)
      action = torch.argmax(dist.probs,dim=1)
      log_prob = dist.log_prob(action)
    return action.cpu(), log_prob.cpu(), value.cpu()

  def select_act(self, x, eps_end, eps_start, eps_decay, step):
    sample = random()
    eps_threshold = eps_end + (eps_start - eps_end) * exp(-1 * step / eps_decay)
    if sample > eps_threshold:
      return self.act_greedy(x) 
    else:
      return self.act(x)

  def forward(self, x):
    x = self.encoder(x)
    logits = self.policy(x)
    value = self.value(x).squeeze(1)
    dist = torch.distributions.Categorical(logits=logits)

    return dist, value

# Define environment
# check the utils.py file for info on arguments
env = make_env(n_envs=num_envs,env_name='coinrun',num_levels=num_levels)
print('Observation space:', env.observation_space)
print('Action space:', env.action_space.n)


# Define network
encoder = Encoder(in_channels=3, feature_dim=4096)
policy = Policy(encoder=encoder, feature_dim=4096, num_actions=env.action_space.n)
policy.cuda()

# Define optimizer
# these are reasonable values but probably not optimal
optimizer = torch.optim.Adam(policy.parameters(), lr=5e-4, eps=1e-5)

# Define temporary storage
# we use this to collect transitions during each iteration
storage = Storage(
    env.observation_space.shape,
    num_steps,
    num_envs,
    gamma=gamma
)

clipped_PPO_loss = ClippedPPOLoss()
clipped_value_loss = ClippedValueFunctionLoss()

# Run training
obs = env.reset()
step = 0
total_training_reward = []
total_val_reward = []

while step < total_steps:
  train_reward = []
  # Use policy to collect data for num_steps steps
  policy.eval()
  for _ in range(num_steps):
    # Use policy
    action, log_prob, value = policy.act(obs) #,eps_end=eps_end,eps_start=eps_start, eps_decay=eps_decay,step=step)
    
    # Take step in environment
    next_obs, reward, done, info = env.step(action)
    train_reward.append(torch.Tensor(reward))

    # Store data
    storage.store(obs, action, reward, done, info, log_prob, value)
    
    # Update current observation
    obs = next_obs

  # Add the last observation to collected data
  _, _, value = policy.act(obs) #,eps_end=eps_end,eps_start=eps_start, eps_decay=eps_decay,step=step)
  storage.store_last(obs, value)

  # Compute return and advantage
  storage.compute_return_advantage()

  # Optimize policy
  policy.train()
  for epoch in range(num_epochs):

    # Iterate over batches of transitions
    generator = storage.get_generator(batch_size)
    for batch in generator:
      b_obs, b_action, b_log_prob, b_value, b_returns, b_advantage = batch

      # Get current policy outputs
      new_dist, new_value = policy(b_obs)
      new_log_prob = new_dist.log_prob(b_action)

      # Clipped policy objective
      pi_loss = clipped_PPO_loss(log_pi=new_log_prob, sampled_log_pi=b_log_prob, advantage=b_advantage, clip=clip_value)
      
      # Clipped value function objective
      value_loss = clipped_value_loss(value=new_value, sampled_value=b_value, sampled_return=b_returns, clip=clip_value)

      # Entropy loss
      entropy_loss = new_dist.entropy()
      entropy_loss = entropy_loss.mean()

      # Backpropagate losses
      loss = (pi_loss + value_coef * value_loss - entropy_coef * entropy_loss) 
      loss.backward()

      # Clip gradients
      torch.nn.utils.clip_grad_norm_(policy.parameters(), grad_eps)

      # Update policy
      optimizer.step()
      optimizer.zero_grad()

  # Update stats
  total_training_reward.append(torch.stack(train_reward).sum(0).mean(0))
  step += num_envs * num_steps

  if(step % 196608 == 0): # we save every 1e6 ish timesteps
    # Make evaluation environment
    eval_env = make_env(num_envs, num_levels=0, env_name='coinrun', use_backgrounds=use_background)
    eval_obs = eval_env.reset()

    val_reward = []
    # Evaluate policy
    policy.eval()
    for _ in range(512):

      # Use policy
      eval_action, eval_log_prob, eval_value = policy.act(eval_obs)

      # Take step in environment
      eval_obs, eval_reward, eval_done, eval_info = eval_env.step(eval_action)
      val_reward.append(torch.Tensor(eval_reward))

    # Calculate average return
    total_val_reward.append(torch.stack(val_reward).sum(0).mean(0))
    print('Step:', step, ' Average return:', total_val_reward)
  if(step % 999424 == 0): # we save every 1e6 ish timesteps
    torch.save(policy.state_dict(), 'checkpoints/' + savename)
    torch.save(total_training_reward, 'trainingResults/training_Reward_' + savename)
    torch.save(total_val_reward, 'trainingResults/validation_Reward_' + savename)

print('Completed training!')

torch.save(policy.state_dict(), 'checkpoints/' + savename)
torch.save(total_training_reward, 'trainingResults/training_Reward_' + savename)
torch.save(total_val_reward, 'trainingResults/validation_Reward_' + savename)