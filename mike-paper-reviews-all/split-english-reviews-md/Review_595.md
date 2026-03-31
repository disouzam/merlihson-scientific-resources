Review 595: Right for the Right Concepts: Teaching Models to Think Like Humans Enhances Robustness
Daily Paper Review by Yehonatan & Mike: 28.03.26, Review 595
Concept-Guided Fine-Tuning: Steering ViTs away from Spurious Correlations to Improve Robustness

Models based on Vision Transformers (ViTs) demonstrate impressive performance on standard benchmarks like ImageNet, yet their robustness remains limited. A primary reason is that these models tend to learn Spurious Correlations: they shift their attention away from features with true semantic meaning and focus instead on statistical cues such as background, lighting, or random noise. The model fails to learn the essence of the object - it learns to identify the context in which it appears.

In recent years, the field of interpretability has increasingly discussed Concept-Based Models (CBMs): models that integrate concepts into their architecture. A concept can be a specific visual feature like "striped pattern", a "yellow beak”, or "furry ears”. The idea is to achieve classification based on specific, explicit features, thereby building networks that are understandable in terms of what they do and why.

Concept-Guided Fine-Tuning (CFT): steering attention to focus on Concepts

To liberate models from the trap of spurious correlations, the paper introduces a method called Concept-Guided Fine-Tuning (CFT). The core idea is to use interpretability as an active component in the model's optimization process: we inject concept-based knowledge directly into the model's explanation maps during training to guide it toward the essential features defining each class.

Explanation maps (also known as saliency/attribution maps) are visual representations designed to reflect which pixels or regions in an image were most significant to the model's decision (a crucial aspect of explainability called faithfulness). Thus, they reveal some reason behind its prediction. These are often provided by attribution methods (e.g., LRP, Grad-CAM, Integrated Gradients) and appear as heatmaps overlaid on the original image (warmer areas were more important). They are typically created using feedback from the model (pixel masking and checking the effect on prediction) or by utilizing model components like gradients or feature maps.

In this work, we utilized Layer-wise Relevance Propagation (LRP), a method that backpropagates relevance scores from the class output neuron to the input pixels, layer by layer, using dedicated relevance propagation rules. Unlike methods like Grad-CAM that rely on a single layer, LRP analyzes the contribution of all network layers, enabling a deeper and more comprehensive analysis of the regions supporting the model's decision. The method (approximately) satisfies the Conservation property, where the sum of relevance scores is preserved across layers. Consequently, the final relevance sum for the pixels matches the model's output for the examined class (e.g., the logit), making the explanation map a faithful additive decomposition of the output into its constituent factors.

One can imagine the internal (latent/hidden) space of a ViT as a vast topographical map of various visual features. Usually, the model is free to navigate it and find any path leading to a correct answer - even if that path goes through the background. CFT serves as a guiding mechanism: for each class, representative and discriminative concepts (like "blue eyes" or "long beak") are predefined, and the model is required to align with and concentrate on them.

The process begins by automatically identifying essential visual characteristics for each class using the semantic knowledge of a LLM (GPT-4o-mini). The LLM generates a list of concepts that are both relevant to the object's definition and possess visual discriminative power, without requiring manual human labeling. To ensure these concepts physically appear in the images, the system performs a validation step checking the concept's frequency and spatial coverage, allowing it to filter out LLM noise and irrelevant concepts.

Then, the refined concept list is fed as a textual prompt to an open-vocabulary segmentation model called GroundedSAM, which locates and precisely masks each concept on the image. This produces a binary semantic mask unifying all relevant concept areas into a single spatial concept map.

In the final stage, the model undergoes fine-tuning where optimization is performed directly on its explanation maps produced via LRP. LRP's Conservation property makes it an exceptionally reliable target for optimization. During training, the loss function encourages the model to assign high relevance to the highlighted concept areas while actively suppressing attention from features unrelated to the concept map. To prevent changes in the explanation maps from harming predictive ability, a specific loss term is integrated to maintain consistency with the original model's predictions, ensuring accuracy is not compromised.

Experimental Results:

The method was tested on five Out-of-Distribution (OOD) datasets. Findings show that using a small number of examples (three images for half of the ImageNet classes), the focus of large models can be shifted properly. CFT achieved consistent improvement - in some cases by hundreds of percent - in OOD performance, all while maintaining accuracy on the original In-distribution training set.

Interesting phenomena observed:

Expected Deviations: In datasets like ImageNet-R (art and graffiti), the improvement was more moderate. This is expected since backgrounds in these datasets tend to be neutral and do not serve as significant spurious cues.

Use of Concepts: Guidance based on specific concepts was found superior to coarse segmentation of the entire object. The level of detail and the ability of concepts to serve as generic discriminative signs are key to the achieved robustness.

Generalization to Unseen Classes: Improved robustness was not limited to classes included in the training. A similar performance boost occurred for the rest of the classes in the data, indicating the model did not just memorize specific examples but likely adopted a more generalized understanding.

In summary, CFT presents a new approach to enhancing robustness: instead of adding more data or changing the architecture, it leverages interpretability to teach the model what to look at. The result is not only better performance but a more interpretable model that visually understands what it is searching for. Ultimately, CFT demonstrates that the field of interpretability, usually intended to explain models, can also be used to improve them.

https://arxiv.org/abs/2603.08309