Review 581: Merging via Lie Algebra: Preserving Manifold Geometry in Deep Model Merging
Mike’s Daily Paper Review: 20.02.26, Review 581
Orthogonal Model Merging

Prepare yourselves for a slightly "tough" experience with this review—mathematically speaking, of course…

This review of an interesting paper is loaded with fairly heavy mathematical concepts (Riemannian manifolds, Lie algebras, and the like). I’ve made an effort to keep the explanation relatively clear even for those who haven’t mastered these topics, though I admit I had to perform some "deep dives" into these areas myself to fully grasp the paper.

The Problem: Euclidean vs. Geometric Weighting

The paper discusses the correct way to combine (merge) pre-trained models. For example, suppose you trained two models for two different tasks and you want to "merge" them into a single model capable of handling both.

Most model merging techniques (including the language models we love so much) treat neural networks as lists of numbers in a flat Euclidean space, where one can simply add them or calculate their average. This paper identifies a fundamental flaw in this logic: weight updates are not just values; they represent geometric transformations.

When calculating the average of weights from two models, one often destroys the "angular relationships" between neurons, a property termed hyperspherical energy, which the model requires to function properly (according to the authors).

The Innovation: OrthoMerge

To overcome this issue, the authors introduce OrthoMerge, a method that shifts the weight-merging process onto the curved Riemannian manifold of the orthogonal group. Simply put, this is the set of all rotations and reflections on a Riemannian manifold.

The technical innovation focuses on orthogonal transformations: essentially, rotations of the model's weight vectors. While rotating weights preserves their internal geometric structure, merging these rotations presents a "geometric dilemma":

If we simply average two rotation matrices, the result will be distorted and will no longer be a valid orthogonal transformation.

Conversely, calculating a perfect mathematical "average" on a curved surface is computationally impossible for giant AI models, as it requires complex matrix computations with an unreasonable runtime, O(n^3) (n is the weight vector dimension).

The Lie Algebra Shortcut

The OrthoMerge method solves this using a clever shortcut via Lie Algebra (essentially a vector space with a specific operation between vectors that results in a vector—unlike an inner product).

Instead of merging directly on the curved manifold, the method uses a logarithmic mapping to "project" these rotations onto a flat tangent vector space. In this flat space, the Lie algebras, rotations are represented as skew-symmetric matrices, where standard linear math (like a weighted average) is indeed valid. After merging the models in this "flat" space, the result is "mapped back" to the curved manifold using the Cayley transform.

This ensures that the final merged model remains a "rigid" orthogonal transformation, perfectly preserving the original geometric energy of the model.

Orthogonal-Residual Decoupling

For standard models not pre-trained with rotations (such as those using LoRA or full fine-tuning), the paper introduces the "Orthogonal-Residual Decoupling" method. This technique assumes that every weight update is a combination of a rotation and a remaining "residual" offset. To separate them, the authors solve the Orthogonal Procrustes problem, the essence of which is finding the single rotation matrix that best fits the model's weight update for a specific task.

By decoupling the update this way, OrthoMerge handles the "rotational" component on the curved manifold and the "residual" component via standard addition. This "dual-track" approach allows the merging to "respect" the model's geometry while accounting for the knowledge the model accumulated during fine-tuning. It effectively shifts model merging from ordinary arithmetic to a geometric integration that preserves its spatial properties.

I hope you survived…

https://arxiv.org/abs/2602.05943