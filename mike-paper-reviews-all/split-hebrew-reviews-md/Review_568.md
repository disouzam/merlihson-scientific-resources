SFT Memorizes, RL Generalizes 

המאמר היומי של אסף אחי-מרדכי ומייק 23.01.26, סקירה 568, 456 סקירות ל-1024

SFT Memorizes, RL Generalizes: A Comparative Study of Foundation Model Post-training

רקע

המאמר בוחן את השאלה המהותית באימון מודלי יסוד (Foundational Models): כיצד משפיעות טכניקות ה-Post-training הנפוצות: Supervised Fine-Tuning) SFT) ו-Reinforcement Learning) RL) על היכולת של המודל להכליל הוראות ולוגיקה למצבים שלא נראו באימון (Out of Distribution). המסקנה המרכזית היא חד-משמעית: בעוד ש-SFT נוטה לגרום למודל "לשנן" את הדאטה וההוראות עליהם הוא אומן, אימון מבוסס RL מעודד הכללה טובה משמעותית במשימות טקסטואליות ובמשימות ויזואליות.

מתודולוגיה וסביבות הניסוי

החוקרים השתמשו במודל  מולטימודלי (מודל Llama-3.2-Vision-11B) ובחנו אותו בשתי משימות הבוחנות יכולות הנמקה (reasoning) והכלל בשתי המשימות הבאות:

GeneralPoints: משחק קלפים אריתמטי (וריאציה של "24"), הדורש מהמודל להגיע למספר מטרה באמצעות פעולות חשבון על 4 קלפים. הקלט ניתן כטקסט או כתמונה (לבחינת VLM).

V-IRL: סימולטור ניווט בעולם האמיתי (מבוסס מפות של ערים כמו ניו-יורק), הדורש הנמקה מרחבית וזיהוי נקודות ציון ויזואליות (landmarks) כדי לבצע הוראות ניווט מורכבות.

הניסויים תוכננו להפריד בין דוגמאות מתוך ההתפלגות של הדאטה בשלב האימון לדוגמאות מחוץ להתפלגות באמצעות שינוי ההוראות ושינוי ויזואלי. לדוגמה, אימון על הוראות בהם קלפי הנסיך, המלך, והמלכה שווים כולם ל-10, ומבחן על הוראות בהם הם שווים 11-13, או אימון על ניווט בניו יורק ומבחן בערים אחרות בעולם.

ממצאים

המחקר מראה פער דרמטי בביצועים בין שתי הגישות:

SFT: המודל מציג ביצועים גבוהים על הדאטה עליו הוא אומן, אך קורס כאשר הדוגמאות מחוץ להתפלגות. לדוגמה, במשימת הניווט (V-IRL-L), הביצועים צנחו מ-80.8% ל-1.3% בלבד במעבר לסט הוראות חדש. משמעות הדבר היא ש-SFT גורם למודל לשנן במקום להכליל.

RL: המודל שומר על יציבות ואף משתפר במעבר לדוגמאות מחוץ לדוגמאות האימון. באותה משימת ניווט, המודל שאומן ב-RL הציג שיפור מ-80.8% ל-91.8% במעבר לסט ההוראות החדש. ממצא זה מצביע על כך ש-RL, המונחה על ידי פונקציית תגמול מבוססת תוצאה (outcome-based reward), לומד אסטרטגיות פתרון מכלילות.

שיפור יכולות תפיסה ויזואלית (Visual Perception): אחת התובנות המפתיעות במאמר נוגעת למודלים מולטי-מודאליים (VLMs). נמצא כי RL לא רק משפר את יכולת הנמקה, אלא משפר אקטיבית את יכולות ה-Low-level של המודל בזיהוי אובייקטים ויזואליים. בניסויים, הגדלת משאבי האימון (compute) ב-RL הובילה לשיפור דיוק הזיהוי של הקלפים או נקודות הציון. לעומת זאת, הגדלת משאבי האימון ב-SFT הובילה דווקא לירידה ביכולות הויזואליות. ההשערה היא ש-SFT גורם לאוברפיט על הטוקנים הטקסטואליים של הנמקה (reasoning tokens) על חשבון יכולות הראייה.

תפקידו הקריטי של SFT כ-Format Teacher: למרות ההצלחה של ה-RL בהכללה, המאמר מדגיש כי לא ניתן לוותר על SFT לחלוטין. ניסויים בהם ניסו לאמן RL ישירות על מודל הבסיס כשלו לעקוב ביעילות אחר ההוראות. ה-SFT נדרש כדי לייצב את פורמט הפלט של המודל ולאפשר לו לעקוב אחרי הוראות בסיסיות, מה שמאפשר ל-RL להתחיל ללמוד בצורה אפקטיבית. כלומר, SFT משמש כ"מורה לפורמט" המכין את הקרקע ללמידה האמיתית המתבצעת ב-RL.

Scaling של אימון: הגדלת משאבי החישוב באימון RL משפרת את דיוק הזיהוי הויזואלי (בניגוד להרחבת SFT שפוגעת בו), בעוד שהגדלת מספר צעדי האימות (Verification steps) תחת אותו תקציב משפרת באופן עקבי ומשמעותי את יכולת ההכללה של המודל.

סיכום והשלכות

המאמר מספק ראיות אמפיריות לכך שאימון SFT קלאסי אולי מספק ביצועים מצוינים על דאטה מתוך ההתפלגות הנלמדת, אך זה נובע משינון ומייצר מודלים שכושלים בקלטים מתוך שינויים קלים בהתפלגות. המאמר מצביע על כך שכדי לבנות מערכות רובוסטיות המסוגלות להסקה אמיתית (reasoning) ומוכללת, יש לשלב RL עם פונקציות תגמול מבוססות תוצאה, תוך שימוש ב-SFT רק כשלב אתחול. 

עם זאת, אימון RL אינו פתרון קסם אוניברסלי. והוא מחייב "פונקציית אימות" (Verifier) אובייקטיבית וחד-משמעית, הקיימת במשימות לוגיות (כמו חישוב שמשוואה הגיעה ל-24 או שהגענו ליעד במשימת ניווט) אך חסרה במשימות "רכות" (כגון כתיבה או סיכום של מסמכים) - שם נדרש אימון יקר המבוסס על העדפות אנושיות (RLHF), שהוא יקר ורועש יותר. ובנוסף, בשל העלות החישובית הגבוהה והצורך באתחול SFT איכותי, השימוש ב-RL אינו מוצדק עבור משימות פשוטות שבהן שינון תבניות מספק פתרון יעיל.

https://arxiv.org/abs/2501.17161

In LLMs, memorization can manifest as the model memorizing the training data, while generalization reflects

LLMs develop reasoning skill sets beyond their training data by pre-computing reasoning graphs before autoregressive generation, which provides compelling evidence of generalization.

Prior studies suggest that LLMs exhibit more overfitting on simpler, knowledge-intensive tasks and greater generalization on more complex, reasoning-intensive ones. But this paper takes a different approach by investigating the role of different post-training paradigms on memorization versus generalization.

To evaluate the generalization of different post-training methods, the paper authors selected two tasks that each offer rule and visual variations. The first task allows assessment of arithmetic reasoning abilities. The second task examines the model’s spatial reasoning capabilities in a visual navigation domain. Both tasks have visual and textual variations (e.g., image of 4 cards with a caption or linguistic navigation instructions and a visual map).

Experiments that investigated the generalization abilities induced by post-training with

RL and SFT. In the experiment setups, the LLM was initialized the model with SFT before running RL. Specifically study the question: 

how does SFT or RL affect the model’s generalization to different rules? 

how does RL/SFT affect its generalization to different visual variants?

how does RL/SFT affect visual recognition capability in a VLM?

what role does SFT play in RL training?

How does the number of verification iterations affect generalization?

RL generalizes, SFT memorizes. L consistently improves OOD performance on all tasks, including both unimodal (LLM) and multimodal (VLM). In contrast, SFT consistently exhibits performance degradation across all OOD evaluations on all tasks.

Is SFT necessary for RL training? SFT is necessary for RL training when the backbone model does not follow instructions. Without SFT, all end-to-end RL runs fail to improve. More specifically, we observe that without SFT, the base model suffers from poor instruction following capability. Yet, Note that due to the difference in backbone model, our results do not

contradict with DeepSeekAI et al. (2025), which suggests that SFT is unnecessary for downstream RL training.