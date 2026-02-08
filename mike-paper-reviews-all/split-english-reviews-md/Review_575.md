Review 575: One Model, Infinite Sizes: The Era of Elastic Inference

One Model, Infinite Sizes: The Era of Elastic Inference

MatFormer: Nested Transformers for Elastic InferenceOri and Mike’s Daily Paper Review, 07.02.26, Review 575

Google and the University of Wisconsin-Madison recently released a paper introducing a new Transformer-based architecture that brings innovations giving the model uniqueness starting right from the training phase: MatFormer – Matryoshka Transformer.

Typically, a model is delivered as a single unit; you cannot simply "take a piece" of it because it isn't built for that. In MatFormer, the model is structured as sub-models (the first n_1 neurons form one model, the first n_1 + n_2 neurons form a second, and so on). This nesting primarily operates on the internal dimension of the Feed-Forward Network (FFN) layers, meaning each sub-model utilizes a "slice" of neurons within the FFN layer. The paper shows this principle can also be applied to Attention heads, but focuses on the FFN because it accounts for roughly 60% of the total computational cost. All sub-models share the same embedding table, so a small sub-model produces a "coarse" or more general representation, while a larger sub-model, which contains the smaller one as a subset, produces a richer representation. The granularity of these sub-models allows for high-level control in building sub-models for various purposes.

The model is trained such that in each iteration, a sub-model is randomly selected and undergoes training. Because smaller sub-models are occasionally trained, the total training cost is similar to that of a standard Transformer and the result is hundreds of functional sub-models. Post-training, one can use a "Mix’n’Match" method to build models composed of sub-models of different sizes. This means that beyond the sub-models explicitly trained, you can also "mix" different granularities across layers; for example, choosing a small FFN for the early layers and a larger one for deeper layers.

This yields not just 4 sub-models, but hundreds of combinations, each tailored to a different computational budget without additional training. This allows for the identification of sub-models that perform best without the need for distillation. The paper demonstrates that this approach is more effective than distillation, though the authors note that both approaches can be combined.

In practice, this means you can train one model and deploy a lightweight version for mobile and a full version for a server without paying for separate training for each size. Additionally, these sub-models are uniform (aligned), allowing them to share the Attention Cache, thereby reducing response times and memory usage.

This alignment is also leveraged for Speculative Decoding, where the small sub-model acts as the draft model and the large model validates the output. The authors managed to slightly accelerate inference with negligible quality loss, thanks to the high consistency between sub-models; consistency that does not exist when using a draft model trained separately.

The researchers presented diverse experiments where the proposed architecture was tested for the MatLM 850M model (an 850-million parameter decoder-only model), comparing its performance to a standard Transformer. The paper showed that the sub-models were equal to, and in many cases outperformed, models trained independently at the same size: both in language and vision models, utilizing what is called "Elastic Inference" through clever sub-model exploitation.

The authors observed that models of different sizes point to a similar ratio between size and performance, demonstrating this across various computer vision tasks such as image classification and image retrieval (with the MatViT model). For example, in image retrieval experiments, a smaller MatViT sub-model saved 40% of the computational cost with a drop of less than 0.5% in accuracy, thanks to the preservation of the metric space between sub-models.

Our Take

MatFormer sounds like a very promising idea, and we saw this in their first open experiment with Gemma 3n. There, in addition to the MatFormer implementation, they also integrated PLE (Per-Layer Embeddings), which keeps the embedding table in the CPU memory and pulls only the necessary vectors to the GPU (a minimal runtime cost in exchange for memory savings). We tried running it on the Nvidia Jetson AGX Orin 64GB edge computer; it was a bit slow, but primarily due to the need for infrastructure optimization.

The architecture points toward interesting research directions at Google, and we anticipate parallel training methods where a large model trains smaller models "as it is being trained itself" (somewhat like siblings growing up together, where the older brother teaches the younger one while he learns himself). The proposed architecture also indicates Google's effort to meet all our needs: models in the cloud, on the computer, on the phone, and even on watches and wearables.

Overall, this is a very interesting architecture, and we want to see more models based on it in the future.

Paper: MatFormer: Nested Transformer for Elastic InferenceHugging Face Blog Post: MatFormer in Gemma 3nHugging Face Model Card: Gemma 3n-E4B-it-litert-preview