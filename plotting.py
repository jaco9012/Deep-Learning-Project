import matplotlib.pyplot as plt
import torch
import numpy as np
import imageio
import torch.nn as nn
import torch.nn.functional as F
from utils import make_env, Storage, orthogonal_init

# plot results
def moving_average(a, n=10) :
    ret = np.cumsum(a, dtype=float)
    ret[n:] = ret[n:] - ret[:-n]
    return ret / n

total_training_reward_baseline = torch.load('trainingResults/training_Reward_proc.pt')
total_training_reward_IMPALA = torch.load('trainingResults/training_Reward_IMPALA_proc.pt')

x_val_baseline = range(8192*2, (len(total_training_reward_baseline)+1)*8192*2, 8192*2)
x_val_IMPALA = range(8192*2, (len(total_training_reward_IMPALA)+1)*8192*2, 8192*2)

plt.figure(figsize=(16,6))
plt.plot(x_val_baseline, total_training_reward_baseline, label='total training reward baseline')
plt.plot(x_val_baseline,moving_average(total_training_reward_baseline), label = 'moving average baseline')
plt.plot(x_val_IMPALA, total_training_reward_IMPALA, label='total training reward IMPALA')
plt.plot(x_val_IMPALA,moving_average(total_training_reward_IMPALA), label = 'moving average IMPALA')
plt.xlabel('time steps'); plt.ylabel('reward')
plt.xlim((0, max(x_val_baseline)*1.05))
plt.legend(loc=4); plt.grid()
plt.tight_layout(); plt.show()



"""Below cell can be used for policy evaluation and saves an episode to mp4 for you to view."""

# obs you need to run the encoder and other stuff from the model it self.
encoder = Encoder(in_channels=3, feature_dim=4096)
policy = Policy(encoder=encoder, feature_dim=4096, num_actions=env.action_space.n)
policy.cuda()
policy.load_state_dict(torch.load('checkpoints/checkpoint.pt'))

# Make evaluation environment
eval_env = make_env(num_envs, start_level=num_levels, num_levels=0, env_name='coinrun')
obs = eval_env.reset()

frames = []
total_reward = []
val_reward = []

# Evaluate policy
policy.eval()
for _ in range(512):

  # Use policy
  action, log_prob, value = policy.act(obs)

  # Take step in environment
  obs, reward, done, info = eval_env.step(action)
  val_reward.append(torch.Tensor(reward))

  # Render environment and store
  frame = (torch.Tensor(eval_env.render(mode='rgb_array'))*255.).byte()
  frames.append(frame)

# Calculate average return
total_reward = torch.stack(val_reward).sum(0).mean(0)
print('Average return:', total_reward)

# Save frames as video
frames = torch.stack(frames)
imageio.mimsave('videos/baselineModel_proc.mp4', frames, fps=25)