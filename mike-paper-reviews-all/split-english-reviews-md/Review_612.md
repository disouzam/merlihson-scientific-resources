Review 612: Static fonts are about to disappear, and this article explains why
Daily Paper Review of Mike: 09.06.26, Review 612

NIV: Neural Axis Variations for Variable Font Generation

An interesting paper of Israeli researchers that's always fun to review.

What if I told you that you could take almost any static font in the world, press a button, and turn it into a fully functional Variable Font with Weight, Width, Slant, and even custom design axes? That's exactly what the new paper NIV – Neural Axis Variations sets out to do.

Let's start with a bit of background.

A regular (static) font is what you're already familiar with. It may have a Bold version or an Italic version, but you've probably never seen "half an Italic angle" or a slant in the opposite direction. The reason is that a static font contains only the discrete styles that the designer explicitly created. There is no continuous transition between design styles and no continuous blending of them.

Variable Fonts are one of the most elegant inventions in typography. The standard was introduced about a decade ago. Instead of maintaining dozens of separate font files (Regular, Bold, Light, Condensed, etc.), a single file contains a continuous design space of variations. The problem is that creating a Variable Font is a manual, time-consuming process that requires significant typographic expertise. For every glyph in the font, the designer must create each stylistic variation, all extreme values for every design axis, and all combinations of these extremes. With four stylistic axes, that can mean 80 designs for a single glyph. That's a lot.

This paper proposes a method that generates these variations automatically. Let's dive into the techniques introduced by the authors.

The first ingredient: working directly on vector geometry

Instead of rasterizing a glyph into an image and applying a CNN or diffusion model, the network operates directly on the control points of the glyph outlines. Given a set of desired axis values, it predicts a displacement for each control point. The result remains fully vector-based and can be exported directly as a standard-compliant Variable Font.

The second ingredient: Property Embedding

At first glance, it might seem sufficient to provide the model with axis values such as Weight=700 or Width=120 and let it do the rest. However, there is a subtle challenge: design axes interact with one another.

The way a glyph changes when it becomes both heavier and narrower is not simply the sum of two independent transformations. To address this, the researchers from Reichman University (Nadav Benedek, Ariel Shamir, and Ohad Fried) developed a Property Embedding mechanism that allows the model to learn interactions between different axes and generate consistent multi-axis variations. It may sound like a small detail, but in practice it is likely one of the key components enabling strong generalization.

The researchers constructed a dataset containing more than one million variation examples derived from Variable Font families in Google Fonts. Each example represents a different combination of axis values and glyph geometries.

What is particularly impressive is the level of generalization. The model does not merely generate variations for glyphs seen during training. It successfully generalizes to unseen glyphs, unseen fonts, complex CJK scripts, and even handwriting styles that never appeared in the training set.

The final result may sound simple, but it is actually quite remarkable: you provide a static font, specify which design axes you want, and receive a standards-compliant Variable Font that works with existing rendering engines without requiring any infrastructure changes.

Like any new architecture, the method is not perfect. It removes most of the manual effort from the font designer's workflow, but the final artistic touch still belongs to the designer.

Over the past decade, we've seen AI learn to generate images, videos, music, and code. Now we're beginning to see it enter typography, one of the most manual and conservative disciplines in the design industry. If approaches like this continue to mature, it is possible that future fonts will no longer be designed as families of static files. Instead, they may be born directly as continuous design spaces generated and managed by neural models.

https://arxiv.org/abs/2606.05261