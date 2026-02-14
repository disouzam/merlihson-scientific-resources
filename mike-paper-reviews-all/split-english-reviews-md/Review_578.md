Review 578: Bees, Flowers, Deep in the Web

Bees, Flowers, Deep in the Web

Shlomi and Mike’s Daily Paper, 13.02.26

Interpretability of Graph Neural Networks to Assess Effects of Global Change Drivers on Ecological Networks

This joint review is out of the ordinary, as it deals with a real-world problem existing in nature (in my opinion, the first such case out of the more than 577 reviews I have written). As mentioned, the article addresses a critical ecological issue: the relationship between plants and pollinators. This connection is vital to the world we live in, and the paper proposes the use of Deep Learning for graph-based information. These models are excellent at predicting connections, but it is often unclear which factors influence the prediction and that is the specific problem this paper tackles.

The type of data used to construct the graph is also fascinating. It consists of information collected over years by volunteers who chose to participate in the research. Each participant had to focus on a specific plant for 20 minutes and photograph every insect they saw. Because the participants were "citizen scientists" who tended to document more frequently in specific areas, the data suffers from bias. The authors propose an interesting solution to this problem, which we will address later: the Hilbert-Schmidt Independence Criterion (HSIC). The primary advantage of this method is that the test is sensitive to almost any type of statistical dependence, including non-linear correlations.

The Hilbert-Schmidt Independence Criterion is a type of independence test between random variables. It is important to note that this test can handle non-linear relationships using the "kernel trick" (a common technique in Support Vector Machines where data is mapped to a different space to model non-linear connections). In the paper, they don’t dive deep into the theoretical essence of the method, but rather use it as a term within the loss function to mitigate data bias.

The researchers work with a Bipartite Graph, which consists of two sets of nodes where all edges exist only between the two groups (this is an undirected graph). The model utilized in the paper is a Bipartite Variational Graph Auto-Encoder (Bipartite VGAE).

So, what does the model actually learn? Given a bipartite graph B and feature matrices X1 and X2 (one for each set of nodes), each node learns its representation using its neighbors in the graph (from the opposing group). The input is an Incidence Matrix, along with a feature matrix containing measured environmental variables (temperature, soil type, etc.).

The encoder aggregates information from neighbors in the graph and combines it with the node's initial features. This representation is then passed through Graph Convolutional Network (GCN) layers to obtain an updated latent representation for each node. The decoder calculates connectivity (the likelihood of a connection) between two nodes using an inner product of their representations; a high value indicates high similarity and a high probability of an edge existing between them. Furthermore, there is a constraint forcing the hidden vectors (latent representations) to follow a Gaussian distribution (achieved by adding a KL divergence term to the loss function). Before training, the matrix rows are normalized to 1. The goal is to estimate the expected connections, the probability of an edge between two nodes from different groups.

The rationale is that the "closer" a node from the first group and a node from the second group are in the latent space (the representation space), the higher the chance that an edge connects them. The graph model learns by repeatedly removing edges from the network, requiring the decoder to predict the missing edges using the latent representations learned by the encoder.

An Important Caveat

As noted, the unit of information is not a "plant" but an observation. Each volunteer documents one plant under specific environmental conditions and the pollinators seen on it (the same plant type can be tested by multiple volunteers under different conditions). Therefore, the graph the model is trained on is an Observation–Pollinator graph, where the rows of matrix B represent observations, not plant species.

However, since every observation has a one-to-one mapping to a specific plant, an assignment matrix P can be used to aggregate the output and define connectivity at the Plant–Pollinator level. This "trick" allows the data structure to fit the model without losing environmental granularity.

A further note on pollinator features: In this problem, the features of the pollinators themselves are not examined; only the features of the observations (temperature, location, terrain type, etc.) are used. Consequently, each pollinator is represented by an identity matrix to distinguish one from another. To obtain a matrix representing the relationship between pollinators and plants, the authors multiplied the output by the assignment matrix P, where each row indicates the type of plant examined in that observation. The connectivity formula is adjusted accordingly.

Interpretability: Explaining the Model

After presenting the model and the criteria for explanation, the authors introduce several methods to examine which features influence the probability of an edge between two nodes:

Smooth Grad (or simply Grad): The simplest method. A normally distributed random value is added to each feature to check the resulting effect on the feature's gradient.

GradInput: This method multiplies the Grad value by the feature value. The intuition is that a variable might be influential, but if its value is zero/negligible, it remains unimportant in that context.

Integrated Gradients: Unlike the previous method, this starts from "neutral" values and sums the change in gradients as it progresses toward the actual feature values. The advantage is that it is "complete", summing the changes yields the total difference.

GraphSVX: This is computationally heavy and does not use gradients. It generates samples by "turning off" certain features or replacing them with mean values. It then fits a weighted linear regression to reconstruct the model's output. The regression coefficients reflect how much each feature's presence changes the output, thus representing feature importance.

The authors tested which method best identifies important features through simulations on synthetic data. They created various configurations (e.g., features with positive effects, negative effects, or noise). The conclusion was that to truly understand important features, one must combine Grad (to identify the positive/negative direction of influence) with GradInput and Integrated Gradients (to identify noise).

Despite finding the ideal combination of explanation methods, simulations revealed shared weaknesses. As the number of groups or plant types in the simulation increased, performance dropped drastically. Another weakness was detecting heterogeneous effects, variables that have a positive impact on one group but a negative one on another. None of the tested methods successfully identified the sign of the variable in such cases.

Application on Real Data

In summary, the authors present the variables that were most critical for connectivity:

Plant Identity and Soil Type: The most significant influence on graph connectivity was the identity of the plant relative to the landscape and soil type (agricultural, urban park, etc.).

Temperature: This had a positive effect; as temperature rose, graph connectivity actually improved.

Year: This showed a negative effect on connectivity (likely reflecting the year-over-year decline in insect populations).

https://arxiv.org/abs/2503.15107