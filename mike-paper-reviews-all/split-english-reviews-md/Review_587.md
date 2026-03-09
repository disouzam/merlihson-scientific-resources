Review 587: Generative Modeling via Drift Fields
Daily paper review by Niv and Mike, 08.03.26, Review 587
Generative Modeling via Drifting

We are already accustomed to hearing about physical processes in the context of generative modeling. After diffusion models and flow models, is the next thing Drifting models? The reviewed paper presents a new approach to generative modeling, which allows it to reach state-of-the-art performance in single-step image generation.

Single-step generation (one-step-generation) has been a hot research field in recent years, and particularly in the past year, where the primary motivation is reducing the high operational costs of models that generate images and video. The cost reduction potential is at least an order of magnitude relative to currently leading methods that require a large number of steps, around 20 and even up to 50.

Beyond efficiency, drifting models have another interesting property. They allow the integration of knowledge distillation from foundational models into the training process, so the model receives guidance to improve not only the visual quality of the images it produces but also the semantic meaning they carry.

Background on Diffusion and Flow Models

Generally, generative modeling can be formulated as learning a mapping/transformation from an input distribution that is simple to sample (usually Gaussian noise) to a desired output distribution (data). Diffusion models and flow models are the leading approaches today for continuous and multi-dimensional distributions, for example, for image, video, and audio generation tasks. Diffusion and flow models model the mapping from input to output as a multi-stage and autoregressive process i.e., as a series of states, where the first state is a noise sample and the last state is a piece of data (e.g., an image). Usually, each state in the series contains less noise than the previous state.

In the training phase, the model learns the dynamics between one state and the next in the sequence, so that in inference, we can progress step-by-step from noise to data. The difference between diffusion and flow models lies in the type of dynamics learned. Diffusion models learn dynamics inspired by the physical process of "diffusion," similar to the movement of a particle affected by random collisions. In flow models, at least in modern versions like Flow Matching, the learned dynamics are simpler, simulating the movement of a particle moving in a straight line.

Single-step Generation is Not a Simple Problem

If we try to train a diffusion or flow model to perform single-step generation naively, we will encounter a classic problem: from noise alone, it is impossible to infer what the "correct image" is, and therefore under standard loss functions (e.g., regression to a target point), the model will converge to an average solution, meaning we will get a collapse of the generative model.

Single-step methods exist in the literature that succeed in addressing the collapse problem: shortcut models, consistency models, and the like. They are interesting in their own right, and some even present impressive results, but generally speaking, it can be said that their performance is currently at a significant gap compared to multi-step methods.

Drifting Models Reformulate the Task in a Way That Prevents Collapse

This is where the paper's twist comes in. Instead of formulating the task as "given noise, give me a specific image," the paper redefines the training task so that it does not refer to a single sample but to a population of samples. Accordingly, the loss function does not define a target for each image individually, but describes a drift field determined from the interaction between all samples.

How the drift field calculation looks in practice:

Sample a batch of generated samples from the model. We emphasize that the model produces an image (sample) from noise in a single step.

In parallel, sample a batch of real images from the dataset.

Define a drift field composed of two opposing forces:

An attractive force towards the data (attraction)

A repulsive force between the generated samples (repulsion)

The intuition here is simple: the "attractive" force tries to bring the generated samples closer to the data cloud, and the "repulsive" force scatters the generated samples from one another, thereby preventing collapse.

After defining the drift field for the generated samples, the model's training loop can be completed relatively simply:

Update the generated samples by a small step in the direction dictated by the drift field. This step can be thought of as a local "correction" of the samples: the drift field pushes each sample to be closer to the data cloud, but simultaneously to remain scattered relative to the other generated samples.

The new samples serve as target points: freeze them using a stop-grad operation, so that the gradient does not flow through the calculation of the drift field itself.

Calculate the network's loss function as the distance between the samples the model produced and the target points obtained after the drift field update. Training pushes the network so that in the next iteration, it will produce samples closer to the target points. That is, samples that are already located closer to a state that balances attraction towards the data and repulsion between the samples themselves.

After a large number of iterations, the network learns to produce a population of samples in which the drift field becomes zero (stable equilibrium point). Under reasonable mathematical assumptions, this state indicates that the set of generated images "covers" the set of real images from the dataset well.

Knowledge Distillation from Foundation Models and Semantic Consistency

One of the interesting properties of foundation models is their ability to learn strong semantic representations. This is in contrast to generative models, which are often characterized by semantically weaker representations. As a result, many generation methods rely on an external foundation model to guide the image creation process and maintain semantic coherence. However, this reliance is not perfect: sometimes it is unstable during the training of the generative model, and generally, it adds additional complexity to the method and even harms its reliability.

A central research topic today in diffusion and flow-type generative models is how to train a generative model with stronger semantic representations, so that it can operate independently and without dependence on an external foundation model. This is where another interesting property of drifting models comes in: the possibility of projecting the drift field onto semantic spaces as well. The practical meaning is that the attraction of the samples towards the data is not defined only by distance in pixel space, but can also be defined by distance in the representation spaces of foundation models, such as CLIP or DINO.

In other words, instead of relying on a foundation model during generation, the semantic knowledge of such a model can be distilled already during training. The ability to define the drift field in different spaces allows the generative model to match the data not only visually but also in terms of the semantic meaning of the samples it produces. The result is an induction of semantic knowledge into the generative model itself. This may enable future generative models that operate independently of an external foundation model, thereby also creating simpler and more reliable systems.

https://arxiv.org/abs/2602.04770