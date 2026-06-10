Review 612: NIV: Neural Axis Variations for Variable Font Generation
הפונטים הסטטיים בדרך להיעלם, והמאמר הזה מסביר למה

סקירת מאמר יומית של מייק: סקירה 612, 412 סקירות ל 1024
מאמר כחול לבן מעניין שתמיד כיף לסקור. מה אם הייתי אומר לכם שאפשר לקחת כמעט כל פונט סטטי בעולם, ללחוץ על כפתור, ולקבל ממנו Variable Font מלא עם צירי Weight, Width, Slant ואפילו צירים מותאמים אישית? זה בדיוק מה שהמאמר החדש NIV - Neural Axis Variations מנסה לעשות.

בוא נתחיל מקצת רקע.

פונט רגיל (סטטי) הוא פונט כפי שאתם מכירים אותו, יש לו נניח גרסת Bold או גרסת Italic, אבל אף פעם לא ראיתם חצי זווית של Italic או נטיה לכיוון ההפוך, נכון? הסיבה היא שהפונט כולל אך ורק את המצבים הדיסקרטים שהמעצב החליט לעצב. אין מעבר רציף בין סגנונות העיצוב ואין שילוב שלהם באופן רציף.

Variable Fonts הם אחת ההמצאות היפות בעולם הפונטים. הסטנדרט הומצא בדיוק לפני עשור. במקום להחזיק עשרות קבצי פונט נפרדים (Regular, Bold, Light, Condensed וכו'), מחזיקים קובץ אחד שמכיל מרחב רציף של וריאציות. הבעיה היא שיצירת Variable Font היא עבודה ידנית, איטית ודורשת מומחיות טיפוגרפית גבוהה, מכיון שהמעצב חייב לעצב עבור כל אות (גליף) בפונט, את כל אחד מהסגנונות, בכל מצבי הקיצון לכל סגנון, וכן את כל הקומבינציות של השילובים שלהם. אם יש ארבעה צירים סגנוניים, זה אומר 80 עיצובים לכל אות. זה המון.

המאמר מציע גישה שמייצרת את הווריאציות האלו אוטומטית. בואו נצלול לטכניקות שהוצעו על ידי המחברים.

האלמנט הראשון: עובדים ישירות על הגיאומטריה הווקטורית.

במקום לרסטר (Rasterize בשפת הקודש כלומר להפוך אלמנט וקטורי (כמו טקסט, צורה הנדסית או תלת-ממד) לתמונת פיקסלים) את האות לתמונה ולהפעיל CNN או Diffusion, המודל מקבל את נקודות הבקרה של קווי המתאר עצמם ומנבא לכל נקודה את ההיסט (displacement) שלה עבור ערכי הצירים המבוקשים. המשמעות היא שהתוצאה נשארת וקטורית לחלוטין וניתנת לייצוא ישירות כקובץ Variable Font תקני.

האלמנט השני: Property Embedding.

לכאורה אפשר היה לתת למודל את ערכי הצירים (Weight=700, Width=120 וכו') וזהו. אבל כאן מופיעה בעיה עדינה: צירי עיצוב משפיעים זה על זה. הדרך שבה אות משתנה כשהיא גם עבה וגם צרה אינה סכום פשוט של שתי טרנספורמציות נפרדות. לכן החוקרים מאוניברסיטת רייכמן (נדב בנדק, אריאל שמיר, אוהד פריד) בנו מנגנון Property Embedding שמאפשר למודל ללמוד אינטראקציות בין צירים שונים וליצור וריאציות מרובות-צירים בצורה עקבית. זה נשמע כמו פרט קטן, אבל בפועל זה כנראה אחד המרכיבים המרכזיים המאפשרים הכללה טובה.

החוקרים בנו מאגר של יותר ממיליון דוגמאות וריאציה שנגזרו ממשפחות Variable Fonts של Google Fonts. כל דוגמה מייצגת קומבינציה אחרת של ערכי צירים וגיאומטריית גליפים. ומה שמעניין במיוחד הוא רמת ההכללה. המודל לא רק מייצר וריאציות עבור אותיות שהוא ראה באימון. הוא מצליח להכליל לגליפים חדשים, לפונטים חדשים, לכתב סיני מורכב (CJK) ואפילו לכתב יד שלא הופיע במהלך האימון.

התוצאה הסופית אולי נשמעת טריוויאלית, אבל היא די מטורפת: אתם מכניסים פונט סטטי, מגדירים אילו צירי עיצוב אתם רוצים, ומקבלים Variable Font תקני שעובד במנועי הרינדור הקיימים בלי שום שינוי בתשתית. כמו כל ארכיטקטורה חדשה, היא לא מושלמת. השיטה חוסכת למעצבי הפונטים את מרבית העבודה, אבל הטאץ הסופי הוא שלהם. כמו כל ארכיטקטורה חדשה, היא אף פעם לא מושלמת. השיטה חוסכת למעצבי הפונטים את מרבית העבודה, אבל הטאץ הסופי הוא שלהם.

בעשור האחרון ראינו AI שיודע ליצור תמונות, וידאו, מוזיקה וקוד. עכשיו מתחילים לראות אותו נכנס גם לעולם הטיפוגרפיה, אחד התחומים היותר ידניים ושמרניים בתעשיית העיצוב. אם הגישה הזו תבשיל, ייתכן שבעתיד רוב הפונטים החדשים לא יעוצבו כמשפחה של קבצים סטטיים, אלא ייוולדו ישר כמרחבי עיצוב רציפים שנוצרים ומנוהלים על ידי מודלים נוירוניים.

https://arxiv.org/abs/2606.05261

=================    ENGLISH    ====================

An interesting paper that's always fun to review.

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

Paper: NIV – Neural Axis Variations (arXiv)