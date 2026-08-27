# UX-001 — Fablit Learner Experience Direction

### Core UX principle

> **Fablit should feel like learning at home: curious, relaxed, personal, and rewarding — not like attending a class.**

There is structure underneath the experience, but the learner shouldn't feel that structure.

---

## 1. The emotional journey

Every activity should have a simple emotional rhythm:

```text
        👀
      Curiosity
          ↓
        🔎
      Explore
          ↓
        💭
       Think
          ↓
        ✍️
      Respond
          ↓
        💡
       Discover
          ↓
        ✨
     Accomplish
```

The learner shouldn't feel:

> "I have been evaluated."

They should feel:

> **"I noticed something."**

and eventually:

> **"I completed something meaningful."**

---

# 2. Visual personality

Fablit should feel:

* warm;
* lightweight;
* approachable;
* slightly playful;
* contemporary;
* creative;
* visually calm.

It should **not** feel:

* corporate;
* academic;
* institutional;
* exam-oriented;
* overly gamified;
* childish.

That last distinction is particularly important for fashion aspirants. We want *playful*, not *juvenile*.

---

# 3. The dashboard

We previously decided that the dashboard should remain small.

I would keep it that way.

Instead of presenting a curriculum hierarchy, the learner should see something closer to:

```text
Good evening 👋

What catches your eye today?

┌─────────────────────────┐
│ 👀 Look a little closer │
│                         │
│ Explore visual balance  │
│                         │
│ ~ 5 min                 │
└─────────────────────────┘

┌─────────────────────────┐
│ 💭 Think like a designer│
│                         │
│ Find the story in an    │
│ everyday object         │
│                         │
│ ~ 5 min                 │
└─────────────────────────┘

┌─────────────────────────┐
│ 🔎 Notice the details   │
│                         │
│ Explore colour & form   │
│                         │
│ ~ 5 min                 │
└─────────────────────────┘
```

No:

> Module 2 → Unit 4 → Lesson 3 → Activity 7

The curriculum can exist underneath.

The learner doesn't need to see it.

---

# 4. Activity cards

Each card should answer three questions immediately:

**What is this?**

**Why might I want to try it?**

**How much effort does it require?**

So a card should have:

* small visual/icon;
* short title;
* one-line invitation;
* approximate time.

Avoid long descriptions.

---

# 5. Activity screen

This is where SPEC-015 gave us the foundation.

The screen should feel like an invitation rather than an instruction sheet.

Instead of:

> **Activity: Visual Analysis**

Prefer:

> ### 👀 Look a little closer

Then:

> Take a moment.
> What catches your attention?

Then the image.

The exact ordering can be tested visually, but the hierarchy should be unmistakable:

```text
Invitation
     ↓
Image
     ↓
Observation prompt
     ↓
Response
```

---

# 6. Image treatment

The image should become the **hero element** of observation activities.

Not a tiny image sitting above a form.

Something closer to:

```text
       👀 Look a little closer

       ┌─────────────────────┐
       │                     │
       │                     │
       │       IMAGE         │
       │                     │
       │                     │
       └─────────────────────┘

       What do you notice?
```

The learner should immediately understand:

> **This is what I'm here to look at.**

---

# 7. Response area

The response box should feel like a notebook rather than an exam answer field.

Instead of:

> **Enter answer**

something like:

> **💭 What's your reading of it?**

Placeholder:

> *There isn't a right answer. Tell us what you notice...*

That sentence is important because it removes assessment anxiety.

---

# 8. Submit action

Avoid:

> Submit Answer

It sounds like an examination.

Prefer something like:

> **I'm ready →**

or:

> **Share my thought →**

The action should feel like continuing a conversation.

---

# 9. Feedback

This is where SPEC-015 becomes especially valuable.

Don't show:

> **Evaluation Result**

Instead:

### 💡 Something you noticed

Then the Finding.

For example:

> You noticed how the empty space around the figure draws attention toward it.

Then, optionally:

> **Look again:**
> Can you see another element that helps create that focus?

That turns feedback into another moment of curiosity.

---

# 10. Don't over-explain

One of the biggest UX dangers now is turning personalized feedback into a mini textbook.

We should resist that.

The learner shouldn't receive a paragraph explaining composition theory every time.

Prefer:

**Observation → small insight → invitation to think again**

rather than:

**Observation → 500-word explanation.**

---

# 11. Completion

This is one of the areas I would deliberately design.

Instead of:

> **Assessment completed successfully**

we want something emotionally lighter.

For example:

### ✨ That's one done.

> You noticed.
> You thought.
> You found something.

**Back to explore →**

This reinforces the feeling of accomplishment without introducing reward mechanics.

---

# 12. Icons and emoji

I agree with your instinct, with one rule:

> **Icons should communicate meaning, not fill empty space.**

Our initial vocabulary could be:

| Meaning        | Visual cue |
| -------------- | ---------- |
| Curiosity      | 👀         |
| Explore        | 🔎         |
| Think          | 💭         |
| Create/respond | ✍️         |
| Insight        | 💡         |
| Reflection     | 🌱         |
| Completion     | ✨          |

We can eventually replace some emoji with a consistent custom icon set if the visual language demands it.

---

# 13. Colour

I wouldn't prescribe a colour palette yet.

Instead, we should establish a principle:

> **Soft, warm, creative, restrained.**

We don't want the interface to look like a children's education app with five competing bright colours.

A restrained palette with one or two expressive accents would fit Fablit's personality much better.

---

# 14. Typography

Typography should create hierarchy without making the interface feel formal.

Think:

```text
Large
friendly title

Small
inviting explanation

Comfortable
reading text

Generous
input space
```

Avoid dense blocks of text.

Whitespace is part of the experience.

---

# 15. Motion

Small transitions can help, but they should be subtle.

For example:

* activity card hover;
* image appearing;
* feedback gently revealing;
* completion state appearing.

No excessive animations.

The learner should feel:

> "This interface is alive."

not:

> "The interface is trying to entertain me."

---

# 16. Mobile-first thinking

Even if the first pilot happens on laptops, the activity should remain comfortable on a phone.

The essential flow should work vertically:

```text
Title
 ↓
Image
 ↓
Prompt
 ↓
Response
 ↓
Feedback
 ↓
Completion
```

No complicated multi-column activity layout is necessary.

---

# 17. Accessibility

The playful personality must not come at the cost of accessibility.

We retain:

* readable text;
* sufficient contrast;
* keyboard navigation;
* meaningful labels;
* accessible form controls;
* image alternative text;
* visible focus states.

Emoji should never be the **only** way information is communicated.

For example:

> 💡 Finding

is fine.

But the semantic text **Finding** must still exist.

---

# 18. What we should explicitly avoid

I think this deserves its own list.

Fablit should avoid:

❌ Progress bars everywhere
❌ Points
❌ Badges
❌ Leaderboards
❌ Streak pressure
❌ Red/green "correct/incorrect" states
❌ "You lost 10 points"
❌ Excessive confetti
❌ Classroom terminology
❌ Dense curriculum menus
❌ Long instructional paragraphs
❌ Generic motivational quotes
❌ Artificially enthusiastic AI language

The learner shouldn't feel manipulated into learning.

---

# 19. The Fablit voice

The interface should speak like a thoughtful companion.

Not:

> **"Congratulations! You have successfully completed Activity 3."**

But:

> **"Nice. You noticed something interesting."**

Not:

> **"Incorrect. Try again."**

But:

> **"Interesting thought. Look once more at the space around the figure."**

Not:

> **"Please provide your answer."**

But:

> **"What do you see?"**

---

# 20. The design test

Whenever we add a UI element, we should ask:

> **Does this make the learner more curious, more comfortable, or more capable?**

If the answer is no, we probably don't need it.

That's a useful design filter for the whole project.

---

# 21. North Star

I'd like to establish this as the UX North Star:

> **Fablit should feel less like opening a course and more like opening a notebook.**

You don't open a notebook because someone is going to grade you.

You open it because:

**something caught your attention.**

You want to explore it.

You want to write something down.

And when you're done, you close the notebook with the small satisfaction that:

> **you noticed something you hadn't noticed before.**
